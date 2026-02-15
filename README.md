# 🚀 免费 Shadowsocks 代理搭建指南

基于 [Modal](https://modal.com) 云平台 + GitHub Actions 自动运行的免费 Shadowsocks 代理方案。

出口 IP 为日本东京（Google Cloud），适合日常使用。

---

## 📋 前置条件

| 需要准备的 | 说明 |
|-----------|------|
| [Modal 账号](https://modal.com) | 免费注册，每月有免费额度 |
| [GitHub 账号](https://github.com) | 用于自动运行代理服务 |
| 代理客户端 | Clash / ClashX / Shadowrocket / v2rayN 等 |

---

## 🛠️ 搭建步骤

### 第一步：注册 Modal 并获取 Token

1. 打开 https://modal.com ，注册并登录
2. 在本地电脑安装 Modal CLI：

   ```bash
   pip install modal
   ```

3. 生成 Token：

   ```bash
   modal token new
   ```

   浏览器会弹出授权页面，授权后终端会显示：

   ```
   MODAL_TOKEN_ID=ak-xxxxxxxxxxxxxxx
   MODAL_TOKEN_SECRET=as-xxxxxxxxxxxxxxx
   ```

   **保存好这两个值，后面要用。**

---

### 第二步：创建 GitHub 私有仓库

1. 在 GitHub 新建一个 **私有仓库**（Private），名字随意，例如 `my-proxy`
2. 把以下两个文件放进仓库：

#### 📄 `freeproxy.py`（代理主程序）

把提供的 `freeproxy.py` 文件放到仓库根目录。

> ⚠️ 建议修改文件中的 `password = "123456"` 为一个强密码，防止被别人扫到盗用。

#### 📄 `.github/workflows/ss-proxy.yml`（自动运行配置）

在仓库中创建 `.github/workflows/` 目录，新建 `ss-proxy.yml` 文件，内容如下：

```yaml
name: SS Proxy

on:
  workflow_dispatch:
  schedule:
    - cron: '0 0 * * *'

jobs:
  run-proxy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Modal
        run: pip install modal

      - name: Deploy API
        env:
          MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}
          MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}
        run: modal deploy freeproxy.py

      - name: Start SS Server (detached)
        env:
          MODAL_TOKEN_ID: ${{ secrets.MODAL_TOKEN_ID }}
          MODAL_TOKEN_SECRET: ${{ secrets.MODAL_TOKEN_SECRET }}
        run: modal run --detach freeproxy.py
```

---

### 第三步：配置 GitHub Secrets

1. 进入你的仓库 → **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**，添加两个密钥：

   | Name | Value |
   |------|-------|
   | `MODAL_TOKEN_ID` | 第一步获取的 `ak-xxx` |
   | `MODAL_TOKEN_SECRET` | 第一步获取的 `as-xxx` |

---

### 第四步：启动代理

1. 进入仓库 → **Actions** → 左侧选择 **SS Proxy**
2. 点击右侧 **Run workflow** → **Run workflow**
3. 等待约 1 分钟，工作流运行完成（绿色 ✅）

---

### 第五步：获取代理配置

部署成功后，打开以下地址（替换 `你的workspace` 为你的 Modal 用户名）：

| 地址 | 用途 |
|------|------|
| `https://你的workspace--ss-api.modal.run/` | 查看代理状态 |
| `https://你的workspace--ss-api.modal.run/clash` | Clash 订阅地址 |
| `https://你的workspace--ss-api.modal.run/ss` | 获取 SS 链接 |

> 💡 不确定你的 workspace 名？登录 https://modal.com/apps 查看。

---

## 📱 客户端配置

### Clash / ClashX / Clash Verge

1. 打开 Clash → **配置/Profiles**
2. 输入订阅地址：`https://你的workspace--ss-api.modal.run/clash`
3. 下载配置并选中
4. 打开系统代理，选择 **Global Selection** 分组

### Shadowrocket（iOS）

1. 打开 Shadowrocket
2. 访问 `https://你的workspace--ss-api.modal.run/ss`
3. 复制返回的 `ss://...` 链接
4. 回到 Shadowrocket，会自动识别并添加节点

### v2rayN（Windows）

1. 访问 `https://你的workspace--ss-api.modal.run/ss`
2. 复制 `ss://...` 链接
3. v2rayN → **服务器** → **从剪贴板导入**

---

## 🔄 日常使用

| 场景 | 操作 |
|------|------|
| 正常使用 | 什么都不用管，GitHub Actions 每天自动重启 |
| 代理断了 | 去 GitHub Actions 手动点一次 Run workflow |
| 换密码 | 修改 `freeproxy.py` 中的 `password`，推送后重新运行 |
| 查看状态 | 访问 `/` 端点或 Modal 控制台 |

---

## ⚠️ 注意事项

1. **务必用私有仓库**，否则密码和配置会泄露
2. **Modal 免费额度有限**，留意用量，避免产生费用
3. **每次重启后隧道地址会变**，客户端需要重新拉取订阅（Clash 订阅链接不变，刷新即可）
4. **密码请改成复杂的**，`123456` 容易被扫描盗用
5. **仅供学习和个人使用**，请遵守当地法律法规

---

## 🏗️ 架构说明

```
GitHub Actions (定时触发)
    │
    ├── modal deploy  → 部署 API 端点（提供订阅链接）
    └── modal run --detach  → 启动 SS 服务器（后台运行 24h）
            │
            ├── ss-server (Shadowsocks 服务)
            └── modal.forward() (TCP 隧道，日本东京出口)

用户客户端 ──→ Modal TCP 隧道 ──→ ss-server ──→ 互联网
```

---

## 🐛 常见问题

**Q: 订阅地址返回 "No active proxy"？**
> SS 服务器还没启动或已超时停止。去 GitHub Actions 重新运行一次 workflow。

**Q: 连上了但是网速很慢？**
> Modal 免费实例资源有限，高峰期可能较慢，属于正常现象。

**Q: 如何查看 Modal 用量？**
> 登录 https://modal.com → 左侧 Usage 页面查看。

**Q: GitHub Actions 没有自动运行？**
> 如果仓库 60 天没有活动，GitHub 会自动禁用 scheduled workflows。进仓库 Actions 页面手动启用即可。
