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
XRAY_PATH = "./bin/xray"  # Untuk Linux (GitHub Actions)
XRAY_URL = "https://github.com/XTLS/Xray-core/releases/download/v25.8.3/Xray-linux-64.zip"  # Versi terbaru untuk Linux

# Port lokal untuk proxy test
LOCAL_PORT = 1080

# URL untuk test koneksi
TEST_URL = "http://httpbin.org/ip"
TIMEOUT = 10  # Detik
MAX_LATENCY = 5000  # ms (config aktif kalau latency < 5 detik)

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
                if chunk:
                    f.write(chunk)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extract("xray", "bin")  # Ekstrak xray untuk Linux
        os.remove(zip_path)
        # Set izin untuk Linux
        os.chmod(XRAY_PATH, stat.S_IEXEC | stat.S_IREAD | stat.S_IWRITE)
        print(f"Xray binary extracted to: {XRAY_PATH}")
        return True
    except Exception as e:
        print(f"Gagal setup Xray: {e}")
        return False

def fetch_sub_url(sub_url):
    """Ambil config dari subscription URL"""
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

def parse_config(config_str
