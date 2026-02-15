import modal
import yaml
import base64
import subprocess
from datetime import datetime
from fastapi import FastAPI, Response

app = modal.App("ss-proxy-manager")

image = (
    modal.Image.debian_slim()
    .apt_install("shadowsocks-libev")
    .pip_install("fastapi[standard]", "pyyaml")
)

# 用 Modal Dict 在函数间共享代理信息
proxy_dict = modal.Dict.from_name("ss-proxy-info", create_if_missing=True)

web_app = FastAPI()

@web_app.get("/clash")
async def clash_subscription():
    try:
        info = proxy_dict["proxy_info"]
    except KeyError:
        return {"error": "No active proxy"}
    
    clash_config = {
        "port": 7890,
        "socks-port": 7891,
        "allow-lan": False,
        "mode": "Global",
        "proxies": [info],
        "proxy-groups": [{
            "name": "Proxy",
            "type": "select",
            "proxies": [info["name"], "DIRECT"]
        }],
        "rules": ["MATCH,Proxy"]
    }
    return Response(
        content=yaml.dump(clash_config, allow_unicode=True, sort_keys=False),
        media_type="application/x-yaml",
    )

@web_app.get("/ss")
async def ss_url():
    try:
        info = proxy_dict["proxy_info"]
    except KeyError:
        return {"error": "No active proxy"}
    auth = f"{info['cipher']}:{info['password']}"
    auth_b64 = base64.b64encode(auth.encode()).decode()
    return {"ss_url": f"ss://{auth_b64}@{info['server']}:{info['port']}#{info['name']}"}

@web_app.get("/")
async def status():
    try:
        info = proxy_dict["proxy_info"]
        return {"status": "running", "server": f"{info['server']}:{info['port']}"}
    except KeyError:
        return {"status": "no proxy running"}

# API 端点 — 纯 ASGI，不跑后台线程
@app.function(image=image)
@modal.asgi_app(label="ss-api")
def api():
    return web_app

# SS 服务器 — 独立长时运行函数
@app.function(image=image, timeout=3600 * 24, region="asia-northeast1")
def run_ss_server():
    password = "123456"
    method = "chacha20-ietf-poly1305"  # 用 AEAD 加密
    port = 8388

    ss_cmd = [
        "ss-server",
        "-s", "0.0.0.0",
        "-p", str(port),
        "-k", password,
        "-m", method,
        "-t", "300",
        # 去掉 --fast-open
    ]
    process = subprocess.Popen(ss_cmd)

    with modal.forward(port, unencrypted=True) as tunnel:
        hostname, tunnel_port = tunnel.tcp_socket
        
        # 写入共享字典，API 函数可以读取
        proxy_dict["proxy_info"] = {
            "name": "Modal SS Proxy",
            "type": "ss",
            "server": hostname,
            "port": tunnel_port,
            "cipher": method,
            "password": password,
            "udp": True,
            "updated_at": datetime.now().isoformat()
        }
        
        print(f"✅ SS running at {hostname}:{tunnel_port}")
        process.wait()  # 阻塞直到进程退出

@app.local_entrypoint()
def main():
    # 启动 SS 服务器（会阻塞运行）
    run_ss_server.remote()