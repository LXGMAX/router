import tkinter as tk
from tkinter import ttk, messagebox
import threading
import sys
import os
import math
import time
import json

# 将上级/当前目录加入引用路径以直接使用 tianyi.py 中的接口
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tianyi


class CircularGauge(tk.Canvas):
    """自定义 Canvas 绘制的精美仪表环形图（用于展示 CPU、网速或百分比）"""
    def __init__(self, parent, size=150, title="CPU 负载", unit="%", max_val=100, **kwargs):
        super().__init__(parent, width=size, height=size, bg="white", highlightthickness=0, **kwargs)
        self.size = size
        self.title = title
        self.unit = unit
        self.max_val = max_val
        self.value = 0
        self.padding = 16
        self.draw()

    def set_value(self, val):
        self.value = max(0, min(self.max_val, val))
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.size
        r_box = [self.padding, self.padding, w - self.padding, w - self.padding]
        
        # 1. 底环（淡灰色）
        self.create_arc(r_box, start=-30, extent=240, style=tk.ARC, outline="#E2E8F0", width=12)

        # 2. 进度环（渐变色彩根据百分比切换）
        extent = -(self.value / self.max_val) * 240
        if self.value < 50:
            arc_color = "#3B82F6"  # 蓝
        elif self.value < 80:
            arc_color = "#F59E0B"  # 橙
        else:
            arc_color = "#EF4444"  # 红

        if extent != 0:
            self.create_arc(r_box, start=210, extent=extent, style=tk.ARC, outline=arc_color, width=12)

        # 3. 中心数值展示
        cx, cy = w / 2, w / 2
        self.create_text(cx, cy - 8, text=f"{int(self.value)}{self.unit}", font=("Helvetica", 18, "bold"), fill="#1E293B")
        self.create_text(cx, cy + 18, text=self.title, font=("Microsoft YaHei UI", 9), fill="#64748B")


class TianyiManagerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("天翼网关智能管理器 (TEWA-1000E)")
        self.geometry("960x700")
        self.minsize(880, 600)

        self.session = None
        self.token = None
        self.proxy_visible = True
        self.privacy_mode = False  # 敏感信息脱敏模式（用于截图分享）

        # 缓存最新拉取到的原始数据，便于脱敏切换时无需重新发网络请求
        self.raw_gwinfo = None
        self.raw_status = None
        self.raw_allinfo = None
        self.raw_lan = None
        self.raw_wifi = None
        self.raw_adv = None
        self.raw_devices = None

        # 配置文件路径
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_config.json")
        self.config_data = self.load_config()

        # 定时器相关
        self.timer_running = False
        self.timer_thread = None
        self.is_fetching = False  # 锁，防止重复并发重叠

        self.setup_styles()
        self.setup_ui()

    def load_config(self):
        """读取 app_config.json 配置，若不存在则使用默认值"""
        default_config = {
            "url": "192.168.1.1",
            "username": "useradmin",
            "password": "",
            "proxy": "",
            "auto_refresh": False
        }
        # 兼容 tianyi.load_config()
        if hasattr(tianyi, 'load_config'):
            try:
                default_config.update(tianyi.load_config())
            except Exception:
                pass

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_config.update(data)
            except Exception as e:
                print(f"读取配置失败: {e}")
        return default_config

    def save_config(self):
        """将当前输入项及自动刷新设置写入 app_config.json"""
        config = {
            "url": self.ent_url.get().strip(),
            "username": self.ent_user.get().strip(),
            "password": self.ent_pwd.get().strip(),
            "proxy": self.ent_proxy.get().strip(),
            "auto_refresh": self.var_timer.get()
        }
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel", font=("Microsoft YaHei UI", 9))
        style.configure("TButton", font=("Microsoft YaHei UI", 9))
        style.configure("TLabelframe.Label", font=("Microsoft YaHei UI", 10, "bold"), foreground="#1E293B")
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("Treeview", font=("Microsoft YaHei UI", 9), rowheight=24)

    def setup_ui(self):
        # 1. 顶部连接/认证栏
        top_frame = ttk.LabelFrame(self, text=" 网关认证连接 ", padding=10)
        top_frame.pack(fill=tk.X, padx=12, pady=6)

        ttk.Label(top_frame, text="地址:").grid(row=0, column=0, padx=3, sticky=tk.W)
        self.ent_url = ttk.Entry(top_frame, width=12)
        self.ent_url.insert(0, self.config_data.get("url", getattr(tianyi, 'URL', '192.168.1.1')))
        self.ent_url.grid(row=0, column=1, padx=3)

        ttk.Label(top_frame, text="账号:").grid(row=0, column=2, padx=3, sticky=tk.W)
        self.ent_user = ttk.Entry(top_frame, width=11)
        self.ent_user.insert(0, self.config_data.get("username", "useradmin"))
        self.ent_user.grid(row=0, column=3, padx=3)

        ttk.Label(top_frame, text="密码:").grid(row=0, column=4, padx=3, sticky=tk.W)
        self.ent_pwd = ttk.Entry(top_frame, width=9, show="*")
        self.ent_pwd.insert(0, self.config_data.get("password", ""))
        self.ent_pwd.grid(row=0, column=5, padx=3)

        ttk.Label(top_frame, text="代理:").grid(row=0, column=6, padx=3, sticky=tk.W)
        self.ent_proxy = ttk.Entry(top_frame, width=22)
        self.ent_proxy.insert(0, self.config_data.get("proxy", ""))
        self.ent_proxy.grid(row=0, column=7, padx=2)

        # 小眼睛按钮 (切换代理可见性)
        self.btn_eye = tk.Button(top_frame, text="👁", font=("Segoe UI Emoji", 10), relief=tk.FLAT,
                                 cursor="hand2", command=self.toggle_proxy_visibility, bg="#F1F5F9", activebackground="#E2E8F0")
        self.btn_eye.grid(row=0, column=8, padx=2)

        # 连接 / 断开 按钮
        self.btn_conn = ttk.Button(top_frame, text="连接网关", command=self.toggle_connection)
        self.btn_conn.grid(row=0, column=9, padx=8)

        self.lbl_status = ttk.Label(top_frame, text="● 未连接", foreground="#94A3B8")
        self.lbl_status.grid(row=0, column=10, padx=6)

        # 顶部操作栏右侧：隐私脱敏按钮与定时刷新开关
        timer_box = ttk.Frame(top_frame)
        timer_box.grid(row=0, column=11, padx=(10, 4), sticky=tk.E)

        # 敏感信息打码切换按钮 (截图模式)
        self.btn_privacy = ttk.Button(timer_box, text="🙈 隐私打码", command=self.toggle_privacy_mode)
        self.btn_privacy.pack(side=tk.LEFT, padx=4)

        self.var_timer = tk.BooleanVar(value=self.config_data.get("auto_refresh", False))
        self.chk_timer = ttk.Checkbutton(timer_box, text="⚡ 1秒自动刷新",
                                         variable=self.var_timer, command=self.on_timer_toggle)
        self.chk_timer.pack(side=tk.LEFT, padx=4)

        # 底部状态栏（先 pack 底部，确保始终可见）
        bottom_bar = ttk.Frame(self, padding=(12, 6))
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.statusbar = ttk.Label(bottom_bar, text="就绪", foreground="#64748B")
        self.statusbar.pack(side=tk.LEFT)

        # 中间 Tab 选项卡
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        # Tab 1: 状态总览 (卡片 + 环形图)
        self.tab_status = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_status, text=" 📊 状态总览 ")
        self.build_status_tab()

        # Tab 2: 终端设备
        self.tab_devices = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_devices, text=" 💻 终端设备 ")
        self.build_devices_tab()

        # Tab 3: 端口映射
        self.tab_portmap = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_portmap, text=" 🔀 端口映射 ")
        self.build_portmap_tab()

        # Tab 4: Wi-Fi 配置
        self.tab_wifi = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_wifi, text=" 📶 Wi-Fi 配置 ")
        self.build_wifi_tab()

        # Tab 5: 控制与设置接口
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_settings, text=" ⚙️ 设置与控制 (SET) ")
        self.build_settings_tab()

    # ------------------ 状态总览美化构建 ------------------

    def build_status_tab(self):
        f = ttk.Frame(self.tab_status, padding=12)
        f.pack(fill=tk.BOTH, expand=True)

        # 顶部工具栏
        tool_bar = ttk.Frame(f)
        tool_bar.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(tool_bar, text="🔄 手动刷新", command=lambda: self.run_async(self.refresh_overview)).pack(side=tk.LEFT)
        
        # 状态总览页面内的定时刷新快捷开关
        self.chk_timer_page = ttk.Checkbutton(tool_bar, text="⚡ 开启 1 秒定时自动刷新监控",
                                              variable=self.var_timer, command=self.on_timer_toggle)
        self.chk_timer_page.pack(side=tk.LEFT, padx=16)

        self.lbl_last_update = ttk.Label(tool_bar, text="", foreground="#64748B")
        self.lbl_last_update.pack(side=tk.LEFT, padx=12)

        # 上部：图形化仪表盘行 (Charts Row)
        charts_frame = ttk.LabelFrame(f, text=" 📈 实时资源与性能监控 ", padding=10)
        charts_frame.pack(fill=tk.X, pady=(0, 10))

        # 1. CPU 环形图
        card_cpu = tk.Frame(charts_frame, bg="white", bd=1, relief=tk.SOLID)
        card_cpu.pack(side=tk.LEFT, padx=10, fill=tk.Y)
        self.gauge_cpu = CircularGauge(card_cpu, size=150, title="CPU 负载", unit="%")
        self.gauge_cpu.pack(padx=10, pady=6)

        # 2. 实时速率卡片
        card_speed = tk.Frame(charts_frame, bg="white", bd=1, relief=tk.SOLID, padx=20, pady=12)
        card_speed.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)

        tk.Label(card_speed, text="实时网络吞吐", font=("Microsoft YaHei UI", 11, "bold"), bg="white", fg="#1E293B").pack(anchor=tk.W, pady=(0, 8))
        
        row_up = tk.Frame(card_speed, bg="white")
        row_up.pack(fill=tk.X, pady=4)
        tk.Label(row_up, text="▲ 实时上行: ", font=("Microsoft YaHei UI", 10), bg="white", fg="#64748B").pack(side=tk.LEFT)
        self.lbl_up_speed = tk.Label(row_up, text="0.00 KB/s", font=("Consolas", 14, "bold"), bg="white", fg="#059669")
        self.lbl_up_speed.pack(side=tk.LEFT, padx=6)

        row_down = tk.Frame(card_speed, bg="white")
        row_down.pack(fill=tk.X, pady=4)
        tk.Label(row_down, text="▼ 实时下行: ", font=("Microsoft YaHei UI", 10), bg="white", fg="#64748B").pack(side=tk.LEFT)
        self.lbl_down_speed = tk.Label(row_down, text="0.00 KB/s", font=("Consolas", 14, "bold"), bg="white", fg="#2563EB")
        self.lbl_down_speed.pack(side=tk.LEFT, padx=6)

        self.lbl_wan_state = tk.Label(card_speed, text="WAN 连接: 未知", font=("Microsoft YaHei UI", 9), bg="white", fg="#64748B")
        self.lbl_wan_state.pack(anchor=tk.W, pady=(8, 0))

        # 3. 专网与终端状态卡片
        card_clients = tk.Frame(charts_frame, bg="white", bd=1, relief=tk.SOLID, padx=20, pady=12)
        card_clients.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)

        tk.Label(card_clients, text="业务与设备概览", font=("Microsoft YaHei UI", 11, "bold"), bg="white", fg="#1E293B").pack(anchor=tk.W, pady=(0, 8))
        self.lbl_wired_count = tk.Label(card_clients, text="🔌 有线设备: - 台", font=("Microsoft YaHei UI", 10), bg="white", fg="#334155")
        self.lbl_wired_count.pack(anchor=tk.W, pady=2)
        self.lbl_wireless_count = tk.Label(card_clients, text="📶 无线设备: - 台", font=("Microsoft YaHei UI", 10), bg="white", fg="#334155")
        self.lbl_wireless_count.pack(anchor=tk.W, pady=2)
        self.lbl_itv_voip = tk.Label(card_clients, text="📺 iTV: - | 📞 VoIP: -", font=("Microsoft YaHei UI", 10), bg="white", fg="#334155")
        self.lbl_itv_voip.pack(anchor=tk.W, pady=2)

        # 下部：网关软硬件及网络参数卡片 (Info Cards)
        info_frame = ttk.LabelFrame(f, text=" ℹ️ 网关硬件与网络配置详情 ", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_overview = tk.Text(info_frame, font=("Consolas", 10), wrap=tk.NONE, bd=0, bg="#F8FAFC")
        self.txt_overview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.txt_overview.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_overview.config(yscrollcommand=scroll_y.set)

    def build_devices_tab(self):
        f = ttk.Frame(self.tab_devices, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        btn_box = ttk.Frame(f)
        btn_box.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(btn_box, text="🔄 刷新设备列表", command=lambda: self.run_async(self.refresh_devices)).pack(side=tk.LEFT)

        columns = ("ip", "mac", "type", "up_speed", "down_speed", "black", "system")
        self.tree_dev = ttk.Treeview(f, columns=columns, show="headings", height=15)
        self.tree_dev.heading("ip", text="IP 地址")
        self.tree_dev.heading("mac", text="MAC 地址")
        self.tree_dev.heading("type", text="设备类型")
        self.tree_dev.heading("up_speed", text="上行速率")
        self.tree_dev.heading("down_speed", text="下行速率")
        self.tree_dev.heading("black", text="黑名单状态")
        self.tree_dev.heading("system", text="系统 / 设备信息")

        self.tree_dev.column("ip", width=120)
        self.tree_dev.column("mac", width=150)
        self.tree_dev.column("type", width=90)
        self.tree_dev.column("up_speed", width=110)
        self.tree_dev.column("down_speed", width=110)
        self.tree_dev.column("black", width=90)
        self.tree_dev.column("system", width=150)

        self.tree_dev.pack(fill=tk.BOTH, expand=True)

    def build_portmap_tab(self):
        f = ttk.Frame(self.tab_portmap, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        btn_box = ttk.Frame(f)
        btn_box.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(btn_box, text="🔄 刷新映射列表", command=lambda: self.run_async(self.refresh_portmap)).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_box, text="一键全部启用", command=lambda: self.run_async(lambda: self.batch_pm('enable'))).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_box, text="一键全部禁用", command=lambda: self.run_async(lambda: self.batch_pm('disable'))).pack(side=tk.LEFT, padx=4)

        columns = ("name", "enable", "client", "protocol", "inPort", "exPort")
        self.tree_pm = ttk.Treeview(f, columns=columns, show="headings", height=15)
        self.tree_pm.heading("name", text="服务备注")
        self.tree_pm.heading("enable", text="状态")
        self.tree_pm.heading("client", text="内部主机 IP")
        self.tree_pm.heading("protocol", text="协议")
        self.tree_pm.heading("inPort", text="内部端口")
        self.tree_pm.heading("exPort", text="外部端口")

        self.tree_pm.column("name", width=120)
        self.tree_pm.column("enable", width=70)
        self.tree_pm.column("client", width=130)
        self.tree_pm.column("protocol", width=80)
        self.tree_pm.column("inPort", width=90)
        self.tree_pm.column("exPort", width=90)

        self.tree_pm.pack(fill=tk.BOTH, expand=True)

    def build_wifi_tab(self):
        f = ttk.Frame(self.tab_wifi, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        btn_box = ttk.Frame(f)
        btn_box.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(btn_box, text="🔄 刷新 Wi-Fi 信息", command=lambda: self.run_async(self.refresh_wifi)).pack(side=tk.LEFT)

        self.txt_wifi = tk.Text(f, font=("Consolas", 10), wrap=tk.NONE, bg="#F8FAFC", bd=0)
        self.txt_wifi.pack(fill=tk.BOTH, expand=True)

    def build_settings_tab(self):
        f = ttk.Frame(self.tab_settings, padding=15)
        f.pack(fill=tk.BOTH, expand=True)

        # 1. 端口映射添加
        grp_pm = ttk.LabelFrame(f, text=" ➕ 添加端口映射规则 ", padding=10)
        grp_pm.pack(fill=tk.X, pady=5)

        ttk.Label(grp_pm, text="名称:").grid(row=0, column=0, padx=4, sticky=tk.W)
        self.pm_name = ttk.Entry(grp_pm, width=12)
        self.pm_name.grid(row=0, column=1, padx=4)

        ttk.Label(grp_pm, text="内部IP:").grid(row=0, column=2, padx=4, sticky=tk.W)
        self.pm_ip = ttk.Entry(grp_pm, width=14)
        self.pm_ip.grid(row=0, column=3, padx=4)

        ttk.Label(grp_pm, text="内部端口:").grid(row=0, column=4, padx=4, sticky=tk.W)
        self.pm_inport = ttk.Entry(grp_pm, width=8)
        self.pm_inport.grid(row=0, column=5, padx=4)

        ttk.Label(grp_pm, text="外部端口:").grid(row=0, column=6, padx=4, sticky=tk.W)
        self.pm_export = ttk.Entry(grp_pm, width=8)
        self.pm_export.grid(row=0, column=7, padx=4)

        ttk.Label(grp_pm, text="协议:").grid(row=0, column=8, padx=4, sticky=tk.W)
        self.pm_proto = ttk.Combobox(grp_pm, values=["TCP", "UDP", "BOTH"], width=6, state="readonly")
        self.pm_proto.set("TCP")
        self.pm_proto.grid(row=0, column=9, padx=4)

        ttk.Button(grp_pm, text="确认添加", command=lambda: self.run_async(self.action_add_portmap)).grid(row=0, column=10, padx=8)

        # 2. 设备黑名单 / 断网控制
        grp_dev = ttk.LabelFrame(f, text=" 🚫 设备黑名单与访问限制 ", padding=10)
        grp_dev.pack(fill=tk.X, pady=5)

        ttk.Label(grp_dev, text="目标 MAC 地址:").grid(row=0, column=0, padx=4, sticky=tk.W)
        self.dev_mac = ttk.Entry(grp_dev, width=20)
        self.dev_mac.grid(row=0, column=1, padx=4)

        ttk.Button(grp_dev, text="加入黑名单(拉黑)", command=lambda: self.run_async(self.action_add_black)).grid(row=0, column=2, padx=6)
        ttk.Button(grp_dev, text="移除黑名单(解封)", command=lambda: self.run_async(self.action_remove_black)).grid(row=0, column=3, padx=6)

        # 3. Wi-Fi SSID 与密码快速修改
        grp_wifi = ttk.LabelFrame(f, text=" 📶 Wi-Fi 快速配置 ", padding=10)
        grp_wifi.pack(fill=tk.X, pady=5)

        ttk.Label(grp_wifi, text="2.4G SSID:").grid(row=0, column=0, padx=4, sticky=tk.W)
        self.wifi_2g_ssid = ttk.Entry(grp_wifi, width=15)
        self.wifi_2g_ssid.grid(row=0, column=1, padx=4)

        ttk.Label(grp_wifi, text="2.4G 密码:").grid(row=0, column=2, padx=4, sticky=tk.W)
        self.wifi_2g_pwd = ttk.Entry(grp_wifi, width=15)
        self.wifi_2g_pwd.grid(row=0, column=3, padx=4)

        ttk.Label(grp_wifi, text="5G SSID:").grid(row=1, column=0, padx=4, pady=5, sticky=tk.W)
        self.wifi_5g_ssid = ttk.Entry(grp_wifi, width=15)
        self.wifi_5g_ssid.grid(row=1, column=1, padx=4, pady=5)

        ttk.Label(grp_wifi, text="5G 密码:").grid(row=1, column=2, padx=4, pady=5, sticky=tk.W)
        self.wifi_5g_pwd = ttk.Entry(grp_wifi, width=15)
        self.wifi_5g_pwd.grid(row=1, column=3, padx=4, pady=5)

        ttk.Button(grp_wifi, text="保存修改 Wi-Fi", command=lambda: self.run_async(self.action_save_wifi)).grid(row=0, column=4, rowspan=2, padx=12)

        # 4. 系统高危操作
        grp_sys = ttk.LabelFrame(f, text=" ⚠️ 系统操作 ", padding=10)
        grp_sys.pack(fill=tk.X, pady=5)

        ttk.Button(grp_sys, text="重启天翼网关", command=self.action_reboot).pack(side=tk.LEFT, padx=10)

    # ------------------ 辅助与工具函数 ------------------

    def mask_text(self, val, typ="general"):
        """敏感信息脱敏处理器"""
        if not val or not self.privacy_mode:
            return str(val or "")
        val = str(val).strip()
        if typ == "ip":
            # 公网 IP 或敏感 IP：保留首位，其余打码 如 171.***.***.***
            parts = val.split(".")
            if len(parts) == 4:
                return f"{parts[0]}.*.*.*"
            return "***.***.***.***"
        elif typ == "mac":
            # MAC 地址打码：例如 10:12:B4:*:*:* 或 1012B4******
            if len(val) >= 6:
                return val[:6] + "*" * (len(val) - 6)
            return "******"
        elif typ == "sn":
            # 序列号打码：保留前后两位
            if len(val) > 4:
                return val[:3] + "****" + val[-2:]
            return "******"
        elif typ == "pwd":
            # 密码全打码
            return "******"
        return "******"

    def toggle_privacy_mode(self):
        """一键切换敏感信息脱敏模式（用于截图展示）"""
        self.privacy_mode = not self.privacy_mode
        if self.privacy_mode:
            self.btn_privacy.config(text="🐵 恢复明文")
            self.set_status("已开启隐私模式：MAC、公网IP、SN、WiFi密码已脱敏")
        else:
            self.btn_privacy.config(text="🙈 隐私打码 (截图)")
            self.set_status("已关闭隐私模式：恢复正常明文显示")

        # 立即重新渲染已有数据，不需要重新发请求
        self.render_all_views()

    def render_all_views(self):
        """使用当前脱敏模式重新刷新界面各面板"""
        if self.raw_gwinfo and self.raw_status and self.raw_allinfo and self.raw_lan:
            self.render_overview_ui(self.raw_gwinfo, self.raw_status, self.raw_allinfo, self.raw_lan)
        if self.raw_devices is not None:
            self.render_devices_ui(self.raw_devices, self.raw_allinfo or {})
        if self.raw_wifi:
            self.render_wifi_ui(self.raw_wifi, self.raw_adv or {})

    def toggle_proxy_visibility(self):
        """切换代理输入框的可见性（明文/密文）"""
        if self.proxy_visible:
            self.ent_proxy.config(show="*")
            self.btn_eye.config(text="🔒")
            self.proxy_visible = False
        else:
            self.ent_proxy.config(show="")
            self.btn_eye.config(text="👁")
            self.proxy_visible = True

    def toggle_connection(self):
        """连接 / 断开 切换"""
        if self.session is not None:
            # 当前已登录，执行断开
            self.run_async(self.do_disconnect)
        else:
            # 当前未登录，执行连接
            self.run_async(self.do_login)

    def format_speed(self, bytes_per_sec):
        """网速格式化"""
        b = float(bytes_per_sec or 0)
        if b < 1024:
            return f"{b:.1f} B/s"
        elif b < 1024 * 1024:
            return f"{b / 1024:.2f} KB/s"
        else:
            return f"{b / (1024 * 1024):.2f} MB/s"

    def run_async(self, fn):
        """异步执行，避免网络请求导致 Tkinter 界面卡死"""
        threading.Thread(target=fn, daemon=True).start()

    def set_status(self, text):
        self.statusbar.config(text=f" {text}")

    # ------------------ 网络登录与断开 ------------------

    def do_login(self):
        tianyi.URL = self.ent_url.get().strip()
        uname = self.ent_user.get().strip()
        pwd = self.ent_pwd.get().strip()
        proxy = self.ent_proxy.get().strip() or None

        self.set_status("正在连接登录天翼网关...")
        try:
            res = tianyi.login(uname, pwd, proxy=proxy)
            self.session = res['session']
            self.token = res['token']

            # 登录成功后保存当前配置（记忆功能）
            self.save_config()

            # 更新登录按钮状态为【断开网关】
            self.btn_conn.config(text="断开网关")
            self.lbl_status.config(text="● 已连接", foreground="#10B981")
            self.set_status(f"登录成功！Token: {self.token}")

            # 登录成功后自动拉取数据
            self.refresh_overview()
            self.refresh_devices()
            self.refresh_portmap()
            self.refresh_wifi()

            # 若配置中开启了自动刷新，登录后自动启动定时器
            if self.var_timer.get() and not self.timer_running:
                self.timer_running = True
                self.timer_thread = threading.Thread(target=self.timer_worker, daemon=True)
                self.timer_thread.start()
                self.set_status("登录成功，已自动开启 1 秒定时监控")
        except Exception as e:
            self.lbl_status.config(text="● 连接失败", foreground="#EF4444")
            self.set_status(f"连接失败: {e}")
            messagebox.showerror("连接错误", str(e))

    def do_disconnect(self):
        # 关闭定时器
        self.var_timer.set(False)
        self.timer_running = False

        self.set_status("正在断开并登出网关...")
        try:
            if self.session and self.token:
                tianyi.logout(self.session, self.token)
        except Exception:
            pass
        finally:
            self.session = None
            self.token = None
            self.btn_conn.config(text="连接网关")
            self.lbl_status.config(text="● 未连接", foreground="#94A3B8")
            self.set_status("已成功断开网关连接。")

    def check_logged_in(self):
        if not self.session or not self.token:
            messagebox.showwarning("提示", "网关尚未连接，请先点击【连接网关】登录！")
            return False
        return True

    # ------------------ 定时器控制 (1秒获取数据) ------------------

    def on_timer_toggle(self):
        # 记忆自动刷新状态
        self.save_config()
        if self.var_timer.get():
            if not self.session:
                messagebox.showwarning("提示", "请先登录连接网关后再开启定时器！")
                self.var_timer.set(False)
                return
            self.timer_running = True
            self.timer_thread = threading.Thread(target=self.timer_worker, daemon=True)
            self.timer_thread.start()
            self.set_status("已启动 1 秒定时数据刷新监控")
        else:
            self.timer_running = False
            self.set_status("已关闭定时器")

    def timer_worker(self):
        while self.timer_running and self.session:
            if not self.is_fetching:
                self.run_async(self.refresh_overview_fast)
            time.sleep(1)

    def refresh_overview_fast(self):
        """定时器轻量刷新：更新 CPU、网速及设备统计"""
        if not self.session or self.is_fetching:
            return
        self.is_fetching = True
        try:
            status = tianyi.gwstatus(self.session)
            allinfo = tianyi.all_info(self.session)

            cpu = status.get('cpuUsed', 0)
            tw_up = allinfo.get('tWUp', 0)
            tw_down = allinfo.get('tWDown', 0)
            wan_conn = allinfo.get('wanConnect', 'UNKNOWN')

            wcount = status.get('wcount', 0)
            wlcount = status.get('wlcount', 0)
            itv = status.get('itv', False)
            voip = status.get('voip', False)

            # 在主线程更新 GUI 控件
            self.after(0, lambda: self.update_dashboard_ui(
                cpu, tw_up, tw_down, wan_conn, wcount, wlcount, itv, voip
            ))
        except Exception:
            pass
        finally:
            self.is_fetching = False

    def update_dashboard_ui(self, cpu, tw_up, tw_down, wan_conn, wcount, wlcount, itv, voip):
        # 1. 环形图更新
        self.gauge_cpu.set_value(cpu)

        # 2. 速率更新
        self.lbl_up_speed.config(text=self.format_speed(tw_up))
        self.lbl_down_speed.config(text=self.format_speed(tw_down))
        self.lbl_wan_state.config(text=f"WAN 状态: {wan_conn} (实时)")

        # 3. 专网与设备统计更新
        self.lbl_wired_count.config(text=f"🔌 有线设备: {wcount} 台")
        self.lbl_wireless_count.config(text=f"📶 无线设备: {wlcount} 台")
        self.lbl_itv_voip.config(text=f"📺 iTV: {'正常' if itv else '未注册'}  |  📞 VoIP: {'正常' if voip else '未注册'}")

        self.lbl_last_update.config(text=f"最后刷新: {time.strftime('%H:%M:%S')}")

    # ------------------ 完整数据刷新 ------------------

    def refresh_overview(self):
        if not self.check_logged_in():
            return
        self.set_status("正在获取网关概览信息...")
        try:
            self.raw_gwinfo = tianyi.view(self.session)
            self.raw_status = tianyi.gwstatus(self.session)
            self.raw_allinfo = tianyi.all_info(self.session)
            self.raw_lan = tianyi.lan_info(self.session)

            self.render_overview_ui(self.raw_gwinfo, self.raw_status, self.raw_allinfo, self.raw_lan)
            self.set_status("概览信息更新完成")
        except Exception as e:
            self.set_status(f"获取概览失败: {e}")

    def render_overview_ui(self, gwinfo, status, allinfo, lan):
        cpu = status.get('cpuUsed', 0)
        tw_up = allinfo.get('tWUp', 0)
        tw_down = allinfo.get('tWDown', 0)
        wan_conn = allinfo.get('wanConnect', 'UNKNOWN')
        wcount = status.get('wcount', 0)
        wlcount = status.get('wlcount', 0)
        itv = status.get('itv', False)
        voip = status.get('voip', False)

        # 敏感信息脱敏
        disp_sn = self.mask_text(gwinfo.get('ProductSN'), "sn")
        disp_mac = self.mask_text(gwinfo.get('MAC'), "mac")
        disp_wan_ip = self.mask_text(gwinfo.get('WANIP'), "ip")

        # 更新图形组件
        self.after(0, lambda: self.update_dashboard_ui(
            cpu, tw_up, tw_down, wan_conn, wcount, wlcount, itv, voip
        ))

        # 更新文本详情
        text = f"""【硬件与网络基本信息】
  产品型号: {gwinfo.get('ProductCls')} (序列号: {disp_sn})
  软件固件版本: {gwinfo.get('SWVer')}
  网关 MAC 地址: {disp_mac}
  公网 WAN IP: {disp_wan_ip}
  局域网 LAN IP: {gwinfo.get('LANIP')} (子网掩码: {lan.get('subnetMask')})
  DHCP 地址池: {lan.get('poolStart')} ~ {lan.get('poolEnd')} (开关状态: {lan.get('dhcpEnbl')})

【运行与拨号指标】
  系统开机时长: {status.get('upTime')} 秒
  宽带拨号在线: {allinfo.get('wanUpTime')} 秒
  WAN 链路状态: {wan_conn}
  CPU 瞬时占用: {cpu}%
"""
        self.after(0, lambda: self._set_text(self.txt_overview, text))

    def _set_text(self, widget, text):
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)

    def refresh_devices(self):
        if not self.check_logged_in():
            return
        self.set_status("正在查询在线设备...")
        try:
            self.raw_devices = tianyi.dev_info(self.session, dev_type='0')
            self.raw_allinfo = tianyi.all_info(self.session)

            self.render_devices_ui(self.raw_devices, self.raw_allinfo)
            self.set_status("在线设备列表已更新")
        except Exception as e:
            self.set_status(f"获取设备失败: {e}")

    def render_devices_ui(self, devs_wired, all_info_data):
        # 建立 IP -> 品牌/型号 映射字典
        brand_map = {}
        for k, v in (all_info_data or {}).items():
            if k.startswith("pc") and isinstance(v, dict):
                ip = v.get("ip")
                model_str = f"{v.get('brand', '')} {v.get('model', '')}".strip()
                if ip:
                    brand_map[ip] = model_str

        rows = []
        for k, dev in devs_wired.items():
            if k.startswith("dev"):
                ip = dev.get("ip", "")
                mac = self.mask_text(dev.get("mac"), "mac")
                sys_model = brand_map.get(ip) or dev.get("system", "") or dev.get("type", "")
                rows.append((
                    ip,
                    mac,
                    dev.get("type"),
                    self.format_speed(dev.get("upSpeed")),
                    self.format_speed(dev.get("downSpeed")),
                    "已拉黑" if dev.get("black") else "正常",
                    sys_model
                ))

        def _update():
            self.tree_dev.delete(*self.tree_dev.get_children())
            for r in rows:
                self.tree_dev.insert("", tk.END, values=r)

        self.after(0, _update)

    def refresh_portmap(self):
        if not self.check_logged_in():
            return
        self.set_status("正在获取端口映射...")
        try:
            pms = tianyi.portmap_list(self.session)
            rows = []
            for k, rule in pms.items():
                if k.startswith("pmRule") and rule.get("client"):
                    status_text = "启用" if rule.get("enable") == 1 else "停用"
                    rows.append((
                        rule.get("desp"),
                        status_text,
                        rule.get("client"),
                        rule.get("protocol"),
                        rule.get("inPort"),
                        rule.get("exPort")
                    ))

            def _update():
                self.tree_pm.delete(*self.tree_pm.get_children())
                for r in rows:
                    self.tree_pm.insert("", tk.END, values=r)

            self.after(0, _update)
            self.set_status("端口映射列表已更新")
        except Exception as e:
            self.set_status(f"获取端口映射失败: {e}")

    def refresh_wifi(self):
        if not self.check_logged_in():
            return
        self.set_status("正在获取 Wi-Fi 配置...")
        try:
            self.raw_wifi = tianyi.wifi_base_settings(self.session)
            self.raw_adv = tianyi.wifi_adv_settings(self.session)

            self.render_wifi_ui(self.raw_wifi, self.raw_adv)
            self.set_status("Wi-Fi 配置已更新")
        except Exception as e:
            self.set_status(f"获取 Wi-Fi 失败: {e}")

    def render_wifi_ui(self, wifi, adv):
        pwd1 = self.mask_text(wifi.get("passwd1", ""), "pwd")
        pwd2 = self.mask_text(wifi.get("passwd2", ""), "pwd")

        def _update():
            self.wifi_2g_ssid.delete(0, tk.END)
            self.wifi_2g_ssid.insert(0, wifi.get("ssid1", ""))
            self.wifi_2g_pwd.delete(0, tk.END)
            self.wifi_2g_pwd.insert(0, pwd1)

            self.wifi_5g_ssid.delete(0, tk.END)
            self.wifi_5g_ssid.insert(0, wifi.get("ssid2", ""))
            self.wifi_5g_pwd.delete(0, tk.END)
            self.wifi_5g_pwd.insert(0, pwd2)

            text = f"""【2.4G 无线网络】
  开关状态: {'开启' if wifi.get('enbl1') else '关闭'}
  SSID 名称: {wifi.get('ssid1')}
  Wi-Fi 密码: {pwd1}
  认证加密: {wifi.get('auth1')}
  发射功率级别: {wifi.get('powerLevel1')} (穿墙模式: {'已开启' if wifi.get('wallPower1') else '未开启'})

【5G 无线网络】
  开关状态: {'开启' if wifi.get('enbl2') else '关闭'}
  SSID 名称: {wifi.get('ssid2')}
  Wi-Fi 密码: {pwd2}
  认证加密: {wifi.get('auth2')}
  无线协议: 802.11{wifi.get('standard2')}
  发射功率级别: {wifi.get('powerLevel2')} (穿墙模式: {'已开启' if wifi.get('wallPower2') else '未开启'})

【Wi-Fi 定时关闭】
  定时开关: {'已启用' if adv.get('timerEnbl') == 1 else '未启用'}
  生效时间段: {adv.get('startTime')} ~ {adv.get('endTime')}
"""
            self._set_text(self.txt_wifi, text)

        self.after(0, _update)

    # ------------------ 设置调用事件 ------------------

    def action_add_portmap(self):
        if not self.check_logged_in():
            return
        name = self.pm_name.get().strip()
        ip = self.pm_ip.get().strip()
        inp = self.pm_inport.get().strip()
        exp = self.pm_export.get().strip()
        proto = self.pm_proto.get()

        if not all([name, ip, inp, exp]):
            messagebox.showwarning("警告", "请完整填写端口映射的所有字段！")
            return

        self.set_status(f"正在添加端口映射: {name} -> {ip}:{inp} ...")
        try:
            tianyi.add_portmap(self.session, self.token, name, ip, inp, exp, proto)
            messagebox.showinfo("成功", f"端口映射 [{name}] 添加成功！")
            self.refresh_portmap()
        except Exception as e:
            messagebox.showerror("错误", f"添加失败: {e}")

    def batch_pm(self, op):
        if not self.check_logged_in():
            return
        try:
            tianyi.batch_portmap_op(self.session, self.token, op=op)
            messagebox.showinfo("成功", f"批量操作 [{op}] 完成！")
            self.refresh_portmap()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def action_add_black(self):
        if not self.check_logged_in():
            return
        mac = self.dev_mac.get().strip()
        if not mac:
            messagebox.showwarning("警告", "请输入要拉黑的 MAC 地址！")
            return
        if messagebox.askyesno("确认", f"确定要拉黑设备 [{mac}] 并切断其网络吗？"):
            try:
                tianyi.set_host_black(self.session, self.token, mac)
                messagebox.showinfo("成功", f"设备 [{mac}] 已成功加入黑名单！")
                self.refresh_devices()
            except Exception as e:
                messagebox.showerror("错误", str(e))

    def action_remove_black(self):
        if not self.check_logged_in():
            return
        mac = self.dev_mac.get().strip()
        if not mac:
            messagebox.showwarning("警告", "请输入要解封的 MAC 地址！")
            return
        try:
            tianyi.remove_black_host(self.session, self.token, mac)
            messagebox.showinfo("成功", f"设备 [{mac}] 已移出黑名单！")
            self.refresh_devices()
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def action_save_wifi(self):
        if not self.check_logged_in():
            return
        w2_s = self.wifi_2g_ssid.get().strip()
        w2_p = self.wifi_2g_pwd.get().strip()
        w5_s = self.wifi_5g_ssid.get().strip()
        w5_p = self.wifi_5g_pwd.get().strip()

        if messagebox.askyesno("确认", "修改 Wi-Fi 名称或密码会导致连接该 Wi-Fi 的设备掉线重连，确认保存吗？"):
            try:
                tianyi.set_wifi_basic(
                    self.session, self.token,
                    wifi_2g={'ssid': w2_s, 'password': w2_p},
                    wifi_5g={'ssid': w5_s, 'password': w5_p}
                )
                messagebox.showinfo("成功", "Wi-Fi 配置已成功保存！")
                self.refresh_wifi()
            except Exception as e:
                messagebox.showerror("错误", str(e))

    def action_reboot(self):
        if not self.check_logged_in():
            return
        if messagebox.askyesno("警告", "真的要重启光猫吗？网关将断开连接约 2 分钟！"):
            try:
                tianyi.reboot(self.session, self.token)
                messagebox.showinfo("提示", "重启指令已发送，网关正在重启...")
            except Exception as e:
                messagebox.showerror("错误", str(e))


if __name__ == '__main__':
    app = TianyiManagerGUI()
    app.mainloop()
