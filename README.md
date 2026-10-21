# router

操作中国电信智能网关（天翼网关）的自动化脚本与可视化管理工具。

> 已在 `TEWA-1000E`（固件版本 `Tianyi_V1.0.2` / `Tianyi_V1.0.7`）上实测通过。

---

## 功能特性

- **完整接口覆盖**：
  - **状态查询**：网关硬件基本信息、CPU 负载、实时上下行总网速吞吐、拨号 WAN IP、局域网 DHCP 分配、已连终端（区分有线/无线及品牌型号）、Wi-Fi 状态、专网（iTV、VoIP）状态、USB 存储状态。
  - **功能控制**：端口映射（虚拟服务器）规则添加/启停/删除/批量清空、Wi-Fi SSID 与密码修改/定时关闭、设备黑名单（断网）与访问限制、后台密码修改、网关重启。
- **代理支持**：支持配置 HTTP / SOCKS5 代理穿透内网访问远程光猫后台。
- **配置持久化记忆**：账号密码、网关地址、代理地址自动保存在本地 `app_config.json`，且已加入 `.gitignore` 防止敏感凭据泄漏。
- **现代化可视化 GUI 界面**：
  - 选项卡多页面布局（总览、终端设备、端口映射、Wi-Fi、设置与控制）；
  - 自定义 Canvas 仪表盘环形图实时监控 CPU 负载；
  - 1 秒轻量级后台定时刷新实时流量吞吐看板；
  - **🙈 隐私打码模式**：一键对公网 IP、MAC 地址、序列号 (SN) 及 Wi-Fi 密码脱敏打码，便于安全截图交流。

---

## 快速上手

### 1. 安装依赖

脚本使用 Python 3 标准库（Tkinter、json、re 等）配合 `requests` 库：

```bash
pip install requests
```

> 若使用 SOCKS5 代理，可额外安装：`pip install requests[socks]`

---

### 2. 方式一：使用图形界面 (GUI)

直接启动可视化管理控制台：

```bash
python tianyi/gui.py
```

#### GUI 核心功能操作：
1. **连接与登录**：
   - 首次启动输入网关地址（默认 `192.168.1.1`）、管理员账号、密码及代理地址；
   - 点击 **【连接网关】**，登录成功后按钮变为 **【断开网关】**，输入内容自动持久化保存；
   - 代理输入框右侧带 **`👁` 小眼睛**，点击可自由切换明文与密文显示。
2. **监控与图表**：
   - 勾选右上角或状态总览页中的 **`⚡ 1秒自动刷新`**，系统将启动后台异步监控，每秒更新 CPU 环形图与实时上下行吞吐。
3. **隐私截图模式**：
   - 点击顶部 **`🙈 隐私打码 (截图)`** 按钮，界面中的公网 IP、MAC、设备 SN、Wi-Fi 密码即刻脱敏显示，再次点击即可恢复。
4. **设置操作 (SET 页面)**：
   - **端口映射**：输入服务备注、内网 IP、端口一键添加映射；
   - **拉黑控制**：输入 MAC 一键将其加入黑名单断开网络；
   - **Wi-Fi 修改**：快速修改 2.4G / 5G 的 SSID 和密码。

---

### 3. 方式二：命令行脚本与代码调用

可在终端直接运行核心模块输出所有数据：

```bash
python tianyi/tianyi.py
```

也可以作为模块在自己的自动化项目中引入使用：

```python
from tianyi.tianyi import login, all_info, dev_info, add_portmap, logout

# 1. 登录（不传参则自动读取 app_config.json；亦可手动传参）
conn = login(username="useradmin", password="xxx", proxy="http://127.0.0.1:7890")
session = conn['session']
token = conn['token']

try:
    # 2. 查询全局网速与设备品牌型号
    info = all_info(session)
    print("实时上行速率:", info.get('tWUp'), "Bytes/s")
    print("实时下行速率:", info.get('tWDown'), "Bytes/s")

    # 3. 查看当前有线连接的所有设备
    wired_devices = dev_info(session, dev_type='0')
    print(wired_devices)

    # 4. 动态添加一条端口映射规则（如 NAS 转发）
    add_portmap(session, token, 
                name="nas_ssh", 
                client_ip="192.168.1.211", 
                internal_port=22, 
                external_port=50022, 
                protocol="TCP")

finally:
    # 5. 安全登出
    logout(session, token)
```

---

## 配置文件说明 (`app_config.json`)

程序首次连接成功后会在 `tianyi/` 目录下生成 `app_config.json`：

```json
{
  "url": "192.168.1.1",
  "username": "useradmin",
  "password": "your_password",
  "proxy": "http://your-proxy-address:port",
  "auto_refresh": false
}
```

> **注意**：该文件已在 `.gitignore` 中配置，请勿将包含实际密码的文件提交到公开仓库中。
