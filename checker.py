import json
import base64
import urllib.parse
import subprocess
import tempfile
import os
import time
import requests
import zipfile
import stat

# Path ke Xray binary
XRAY_PATH = "./bin/xray"
XRAY_URL = "https://github.com/XTLS/Xray-core/releases/download/v25.8.3/Xray-linux-64.zip"

# Port lokal untuk proxy test
LOCAL_PORT = 1080
TEST_URL = "http://httpbin.org/ip"
TIMEOUT = 10
MAX_LATENCY = 5000  # ms

def setup_xray():
    """Download dan setup Xray binary jika belum ada"""
    if os.path.exists(XRAY_PATH):
        print("Xray binary already exists, skipping download...")
        return True
    try:
        print("Downloading Xray binary...")
        os.makedirs("bin", exist_ok=True)
        zip_path = os.path.join("bin", "xray.zip")

        response = requests.get(XRAY_URL, stream=True)
        response.raise_for_status()
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if member.endswith("xray") and not member.endswith("/"):
                    zip_ref.extract(member, "bin")
                    extracted_path = os.path.join("bin", os.path.basename(member))
                    os.rename(extracted_path, XRAY_PATH)
                    break

        os.remove(zip_path)
        os.chmod(XRAY_PATH, 0o755)  # rwxr-xr-x
        print(f"Xray binary extracted to: {XRAY_PATH}")
        return True
    except Exception as e:
        print(f"Gagal setup Xray: {e}")
        return False

def fetch_sub_url(sub_url):
    try:
        response = requests.get(sub_url, timeout=10)
        response.raise_for_status()
        content = response.text
        try:
            content = base64.b64decode(content).decode('utf-8')
        except:
            pass
        return [line.strip() for line in content.splitlines() if line.strip()]
    except Exception as e:
        print(f"Gagal ambil sub URL: {e}")
        return []

def parse_config(config_str):
    if config_str.startswith('vmess://'):
        try:
            payload = base64.b64decode(config_str[8:]).decode('utf-8')
            return json.loads(payload), 'vmess'
        except:
            return None, None
    elif config_str.startswith('vless://'):
        try:
            parsed = urllib.parse.urlparse(config_str)
            query = urllib.parse.parse_qs(parsed.query)
            return {
                'ps': parsed.fragment or 'vless',
                'add': parsed.hostname,
                'port': parsed.port if parsed.port else 443,
                'id': parsed.username,
                'net': parsed.scheme.split('+')[1] if '+' in parsed.scheme else 'tcp',
                'path': query.get('path', ['/'])[0],
                'tls': 'tls' if query.get('security', [''])[0].lower() == 'tls' else 'none',
                'sni': query.get('sni', [parsed.hostname])[0]
            }, 'vless'
        except:
            return None, None
    elif config_str.startswith('trojan://'):
        try:
            parsed = urllib.parse.urlparse(config_str)
            query = urllib.parse.parse_qs(parsed.query)
            port = parsed.port if parsed.port else 443
            return {
                'ps': parsed.fragment or 'trojan',
                'add': parsed.hostname,
                'port': port,
                'password': parsed.username,
                'net': query.get('type', ['tcp'])[0],
                'path': query.get('path', ['/'])[0],
                'sni': query.get('sni', [parsed.hostname])[0],
                'security': 'tls'
            }, 'trojan'
        except:
            return None, None
    elif config_str.startswith('ss://'):
        try:
            # coba format ss://base64
            try:
                decoded = base64.b64decode(config_str[5:].split('#')[0]).decode('utf-8')
            except:
                decoded = config_str[5:].split('#')[0]

            if '@' in decoded and ':' in decoded:
                method_password, host_port = decoded.split('@')
                host, port = host_port.rsplit(':', 1)
                method, password = method_password.split(':', 1)
                return {
                    'ps': urllib.parse.unquote(config_str.split('#')[-1]) if '#' in config_str else 'shadowsocks',
                    'add': host,
                    'port': int(port),
                    'method': method,
                    'password': password
                }, 'shadowsocks'
            return None, None
        except:
            return None, None
    return None, None

def generate_xray_config(parsed_config, protocol):
    base = {
        "log": {"loglevel": "none"},
        "inbounds": [{
            "port": LOCAL_PORT,
            "protocol": "socks",
            "listen": "127.0.0.1",
            "settings": {"udp": True}
        }]
    }
    if protocol == 'vmess':
        base["outbounds"] = [{
            "protocol": "vmess",
            "settings": {
                "vnext": [{
                    "address": parsed_config['add'],
                    "port": int(parsed_config['port']),
                    "users": [{
                        "id": parsed_config['id'],
                        "alterId": int(parsed_config.get('aid', 0)),
                        "security": parsed_config.get('scy', 'auto')
                    }]
                }]
            },
            "streamSettings": {
                "network": parsed_config.get('net', 'tcp'),
                "security": parsed_config.get('tls', 'none'),
                "wsSettings": {"path": parsed_config.get('path', '/')} if parsed_config.get('net') == 'ws' else None
            }
        }]
    elif protocol == 'vless':
        base["outbounds"] = [{
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": parsed_config['add'],
                    "port": int(parsed_config['port']),
                    "users": [{"id": parsed_config['id'], "encryption": "none"}]
                }]
            },
            "streamSettings": {
                "network": parsed_config['net'],
                "security": parsed_config['tls'],
                "wsSettings": {"path": parsed_config['path']} if parsed_config['net'] == 'ws' else None
            }
        }]
    elif protocol == 'trojan':
        base["outbounds"] = [{
            "protocol": "trojan",
            "settings": {
                "servers": [{
                    "address": parsed_config['add'],
                    "port": int(parsed_config['port']),
                    "password": parsed_config['password']
                }]
            },
            "streamSettings": {
                "network": parsed_config['net'],
                "security": "tls",
                "tlsSettings": {"serverName": parsed_config['sni']}
            }
        }]
    elif protocol == 'shadowsocks':
        base["outbounds"] = [{
            "protocol": "shadowsocks",
            "settings": {
                "servers": [{
                    "address": parsed_config['add'],
                    "port": int(parsed_config['port']),
                    "method": parsed_config['method'],
                    "password": parsed_config['password']
                }]
            }
        }]
    return base

def test_config(config_str):
    parsed, protocol = parse_config(config_str)
    if not parsed or not protocol:
        return False, "Parse gagal", None

    config_json = generate_xray_config(parsed, protocol)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_json, f, indent=2)
        temp_config = f.name

    try:
        xray_full_path = os.path.abspath(XRAY_PATH)
        proc = subprocess.Popen([xray_full_path, 'run', '-c', temp_config],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(2)
        start_time = time.time()
        proxies = {
            'http': f'socks5://127.0.0.1:{LOCAL_PORT}',
            'https': f'socks5://127.0.0.1:{LOCAL_PORT}'
        }
        response = requests.get(TEST_URL, proxies=proxies, timeout=TIMEOUT)
        latency = int((time.time() - start_time) * 1000)

        proc.terminate()
        proc.wait()
        os.unlink(temp_config)

        if response.status_code == 200 and latency < MAX_LATENCY:
            return True, f"Aktif, latency: {latency}ms", latency
        else:
            return False, f"Gagal connect atau latency tinggi: {latency}ms", latency
    except Exception as e:
        if 'proc' in locals():
            proc.kill()
        if os.path.exists(temp_config):
            os.unlink(temp_config)
        return False, f"Error: {e}", None

def main():
    if not setup_xray():
        print("Gagal setup Xray, keluar...")
        return

    sub_url = os.environ.get('SUB_URL', '')
    if not sub_url:
        print("SUB_URL tidak diset di environment variable!")
        return

    print(f"Fetching configs from: {sub_url}")
    configs = fetch_sub_url(sub_url)
    if not configs:
        print("Tidak ada config dari sub URL!")
        return

    active_configs = []
    print(f"Testing {len(configs)} configs...")

    for i, config in enumerate(configs, 1):
        print(f"[{i}/{len(configs)}] Testing: {config[:50]}...")
        is_active, msg, latency = test_config(config)
        if is_active:
            active_configs.append((config, latency))
            print(f"  ✓ {msg}")
        else:
            print(f"  ✗ {msg}")

    active_configs.sort(key=lambda x: x[1] if x[1] is not None else float('inf'))

    output_file = "active_configs.txt"
    with open(output_file, 'w') as f:
        for config, latency in active_configs:
            f.write(f"{config} # Latency: {latency}ms\n")

    print(f"\nSelesai! {len(active_configs)} config aktif disimpan di {output_file}")

if __name__ == "__main__":
    main()
