import random
import requests
import re
import json

URL = '192.168.1.1'
UNAME = 'useradmin'
UPWD  = 'zeqrg'

# 代理配置（若不需要代理，设置为 None）
PROXY = 'http://higzj.vicp.io:53128'


# ------------------------- 基础认证与系统管理 -------------------------

def login(username=UNAME, password=UPWD, proxy=PROXY):
    """登录天翼网关，返回 session 与 token"""
    payload = {'username': username, 'psd': password}
    s = requests.Session()
    if proxy:
        s.proxies = {'http': proxy, 'https': proxy}
    r = s.post('http://' + URL + '/cgi-bin/luci', params=payload, timeout=10)
    tokens = re.compile(r"token: '([a-z0-9]{32})'").findall(r.text)
    if not tokens:
        raise RuntimeError("登录失败，未匹配到 token！请检查账号密码或网络连接。")
    return {'session': s, 'token': tokens[0]}


def logout(session, token):
    """登出网关"""
    payload = {'token': token, '_': random.random()}
    session.post('http://' + URL + '/cgi-bin/luci/admin/logout', params=payload, timeout=5)


def reboot(session, token):
    """重启网关"""
    payload = {'token': token, '_': random.random()}
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/reboot', params=payload, timeout=5)
    return r.text


def change_password(session, token, old_password, new_password):
    """【设置】修改后台管理员密码"""
    data = {
        'token': token,
        'old': old_password,
        'newPasswd': new_password,
    }
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/settings/change_passwd', data=data, timeout=5)
    return r.text


# ------------------------- 状态查询接口 -------------------------

def view(session):
    """【查询】网关基本信息（WAN IP、MAC、硬件版本、固件版本等）"""
    payload = {'get': 'part', '_': random.random()}
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/settings/gwinfo', params=payload, timeout=5)
    return r.json()


def gwstatus(session):
    """【查询】网关运行状态（CPU 使用率、运行时间、在线设备数、iTV/VoIP 状态）"""
    payload = {'get': 'part', '_': random.random()}
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/settings/gwstatus', params=payload, timeout=5)
    return r.json()


def all_info(session):
    """【查询】全局综合信息（在线终端详情、实时上下行总网速 tWUp/tWDown、WAN 在线时长）"""
    payload = {'get': 'part', '_': random.random()}
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/allInfo', params=payload, timeout=5)
    return r.json()


def itv_voip_status(session):
    """【查询】iTV 与 VoIP 电话注册状态"""
    payload = {'get': 'part', '_': random.random()}
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/device/itvVoipReg', params=payload, timeout=5)
    return r.json()


def usb_devices(session):
    """【查询】插入网关的 USB 存储设备状态与数量"""
    payload = {'get': 'part', '_': random.random()}
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/storage/getUsbDevs', params=payload, timeout=5)
    return r.json()


def app_config(session):
    """【查询】安装的应用与商城插件配置"""
    payload = {'get': 'part', '_': random.random()}
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/getAppConfig', params=payload, timeout=5)
    return r.json()


# ------------------------- 终端控制设置 -------------------------

def dev_info(session, dev_type='0'):
    """
    【查询】获取连接的终端设备列表及其实时网速、MAC地址等
    :param dev_type: '0': 有线网口设备, '1': 无线WiFi终端
    """
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/device/devInfo', data={'type': str(dev_type)}, timeout=5)
    return r.json()


def black_hosts(session):
    """【查询】获取黑名单主机列表"""
    payload = {'get': 'part', '_': random.random()}
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/device/blackHosts', params=payload, timeout=5)
    return r.json()


def set_host_black(session, token, mac):
    """【设置】将指定 MAC 地址设备加入黑名单（断网并拉黑）"""
    clean_mac = mac.replace(':', '').replace('-', '').upper()
    data = {
        'token': token,
        'type': 'black',
        'mac': clean_mac
    }
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/device/hostSettings', data=data, timeout=5)
    return r.text


def remove_black_host(session, token, mac):
    """【设置】将指定 MAC 地址移出黑名单（恢复上网）"""
    clean_mac = mac.replace(':', '').replace('-', '').upper()
    data = {
        'token': token,
        'mac': clean_mac
    }
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/device/rmBlackHost', data=data, timeout=5)
    return r.text


def set_host_restrict(session, token, mac, enable=True):
    """【设置】针对某台设备开启/关闭上网访问限制"""
    clean_mac = mac.replace(':', '').replace('-', '').upper()
    data = {
        'token': token,
        'type': 'restrict',
        'onOff': '1' if enable else '0',
        'mac': clean_mac
    }
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/device/hostSettings', data=data, timeout=5)
    return r.text


# ------------------------- Wi-Fi 无线设置 -------------------------

def wifi_base_settings(session):
    """【查询】Wi-Fi 基础配置"""
    r = session.get('http://' + URL + '/cgi-bin/luci/admin/wifi/base_settings', timeout=5)
    return r.json()


def wifi_adv_settings(session):
    """【查询】Wi-Fi 定时开关配置"""
    r = session.get('http://' + URL + '/cgi-bin/luci/admin/wifi/adv_settings', timeout=5)
    return r.json()


def wifi_interconnd_status(session):
    """【查询】Wi-Fi 互联状态"""
    payload = {'get': 'part', '_': random.random()}
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/wifi/interConndStatus', params=payload, timeout=5)
    return r.json()


def set_wifi_basic(session, token, wifi_2g=None, wifi_5g=None, dual_band=True):
    """
    【设置】修改 2.4G / 5G Wi-Fi 配置
    :param wifi_2g: dict: {'switch': '1'/'0', 'ssid': str, 'password': str, 'auth': str, 'strength': '1'/'0'}
    :param wifi_5g: dict: {'switch': '1'/'0', 'ssid': str, 'password': str, 'auth': str, 'strength': '1'/'0'}
    """
    current = wifi_base_settings(session)
    data = {
        'token': token,
        'dualBand': '1' if dual_band else '0',
        # 2.4G
        'wifi_2G_switch': (wifi_2g or {}).get('switch', '1' if current.get('enbl1') else '0'),
        'wifi_2G_SSID': (wifi_2g or {}).get('ssid', current.get('ssid1')),
        'wifi_2G_password': (wifi_2g or {}).get('password', current.get('passwd1')),
        'wifi_2G_auth': (wifi_2g or {}).get('auth', current.get('auth1', 'Mixed WPA2/WPA-PSK')),
        'wifi_2G_strength': (wifi_2g or {}).get('strength', '1' if current.get('wallPower1') else '0'),
        # 5G
        'wifi_5G_switch': (wifi_5g or {}).get('switch', '1' if current.get('enbl2') else '0'),
        'wifi_5G_SSID': (wifi_5g or {}).get('ssid', current.get('ssid2')),
        'wifi_5G_password': (wifi_5g or {}).get('password', current.get('passwd2')),
        'wifi_5G_auth': (wifi_5g or {}).get('auth', current.get('auth2', 'Mixed WPA2/WPA-PSK')),
        'wifi_5G_strength': (wifi_5g or {}).get('strength', '1' if current.get('wallPower2') else '0'),
    }
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/wifi/wifiBasic', data=data, timeout=8)
    return r.text


def set_wifi_timer(session, token, enable=False, start_time="06:00", end_time="23:00"):
    """
    【设置】配置 Wi-Fi 定时关闭/开启时间
    :param enable: 是否启用定时
    :param start_time: 开启时间，如 "06:00"
    :param end_time: 关闭时间，如 "23:00"
    """
    sh, sm = start_time.split(':')
    eh, em = end_time.split(':')
    data = {
        'token': token,
        'wifi_timing_switch': '1' if enable else '0',
        'wifi_start_time': start_time,
        'wifi_end_time': end_time,
        'wifi_start_hour_value': sh,
        'wifi_start_minute_value': sm,
        'wifi_end_hour_value': eh,
        'wifi_end_minute_value': em
    }
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/wifi/wifiAdv', data=data, timeout=5)
    return r.text


# ------------------------- 端口映射（虚拟服务器）设置 -------------------------

def portmap_list(session):
    """【查询】查看端口映射规则列表"""
    payload = {'get': 'part', '_': random.random()}
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/settings/pmDisplay', params=payload, timeout=5)
    return r.json()


def add_portmap(session, token, name, client_ip, internal_port, external_port, protocol='TCP'):
    """
    【设置】添加一条端口映射规则
    :param protocol: 'TCP', 'UDP', 或 'BOTH'
    """
    data = {
        'token': token,
        'op': 'add',
        'srvname': name,
        'client': client_ip,
        'protocol': protocol,
        'inPort': str(internal_port),
        'exPort': str(external_port)
    }
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/settings/pmSetSingle', data=data, timeout=5)
    return r.text


def set_portmap_status(session, token, name, op='enable'):
    """
    【设置】修改单条端口映射状态
    :param op: 'enable' (启用), 'disable' (停用), 'del' (删除)
    """
    data = {
        'token': token,
        'op': op,
        'srvname': name
    }
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/settings/pmSetSingle', data=data, timeout=5)
    return r.text


def batch_portmap_op(session, token, op='enable'):
    """
    【设置】批量操作所有端口映射规则
    :param op: 'enable' (全部启用), 'disable' (全部禁用), 'del' (全部删除)
    """
    data = {
        'token': token,
        'op': op
    }
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/settings/pmSetAll', data=data, timeout=5)
    return r.text


# ------------------------- 局域网 LAN / DHCP 设置 -------------------------

def lan_info(session):
    """【查询】局域网 LAN 及 DHCP 配置"""
    r = session.get('http://' + URL + '/cgi-bin/luci/admin/settings/lanInfo', timeout=5)
    return r.json()


def set_lan_dhcp(session, token, lan_ip, subnet_mask, pool_start, pool_end, dhcp_enable=True):
    """
    【设置】修改 LAN 口 IP 及 DHCP 地址池（慎用，修改 IP 会导致断网重连）
    """
    curr = lan_info(session)
    data = {
        'token': token,
        'oldLanIp': curr.get('lanIp'),
        'lanIp': lan_ip,
        'subnetMask': subnet_mask,
        'dhcpEnbl': '1' if dhcp_enable else '0',
        'poolStart': pool_start,
        'poolEnd': pool_end
    }
    r = session.post('http://' + URL + '/cgi-bin/luci/admin/settings/lanSettings', data=data, timeout=5)
    return r.text


def pretty_print(title, obj):
    print(f"\n==================== {title} ====================")
    print(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True))


# ------------------------- 演示 -------------------------

if __name__ == '__main__':
    conn = login(UNAME, UPWD)
    session = conn['session']
    token = conn['token']

    try:
        # 演示查询
        pretty_print("网关信息", view(session))
        pretty_print("Wi-Fi 配置", wifi_base_settings(session))
        pretty_print("黑名单主机", black_hosts(session))
        pretty_print("现有端口映射", portmap_list(session))

        # 示例：如果要添加端口映射（取消注释即可）：
        # add_portmap(session, token, name='webtest', client_ip='192.168.1.211', internal_port=8080, external_port=8080, protocol='TCP')

        # 示例：如果要拉黑某设备 / 移出黑名单：
        # set_host_black(session, token, mac='A4:39:B3:01:D8:6B')
        # remove_black_host(session, token, mac='A4:39:B3:01:D8:6B')

    finally:
        logout(session, token)
        print("\n[+] 已安全退出登录。")
