import json
import base64
import urllib.parse
import subprocess
import tempfile
import os
import time
import requests
import zipfile

# Path ke Xray binary
XRAY_PATH = "./bin/xray"
XRAY_URL = "https://github.com/XTLS/Xray-core/releases/download/v25.8.3/Xray-linux-64.zip"

LOCAL_PORT = 1080
TEST_URL = "http://httpbin.org/ip"
TIMEOUT = 10
MAX_LATENCY = 5000  # ms

RETRY = 3
RETRY_DELAY = 5

def retry_request(func, *args, **kwargs):
    for attempt in range(1, RETRY + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Attempt {attempt} gagal: {e}")
            if attempt < RETRY:
                print(f"Tunggu {RETRY_DELAY}s sebelum retry...")
                time.sleep(RETRY_DELAY)
            else:
                raise
    return None

def setup_xray():
    if os.path.exists(XRAY_PATH):
        print("Xray binary already exists, skipping download...")
        return True
    try:
        print("Downloading Xray binary...")
        os.makedirs("bin", exist_ok=True)
        zip_path = os.path.join("bin", "xray.zip")

        def download():
            response = requests.get(XRAY_URL, stream=True, timeout=30)
            response.raise_for_status()
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        retry_request(download)

        # extract xray
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if member.endswith("xray") and not member.endswith("/"):
                    extracted = zip_ref.extract(member, "bin")
                    os.rename(extracted, XRAY_PATH)
                    break

        os.remove(zip_path)
        os.chmod(XRAY_PATH, 0o755)
        print(f"Xray binary saved to: {XRAY_PATH}")
        return True
    except Exception as e:
        print(f"Gagal setup Xray setelah {RETRY} percobaan: {e}")
        return False

def fetch_sub_url(sub_url):
    try:
        def get_url():
            response = requests.get(sub_url, timeout=10)
            response.raise_for_status()
            return response.text
        content = retry_request(get_url)
        try:
            content = base64.b64decode(content).decode('utf-8')
        except:
            pass
        return [line.strip() for line in content.splitlines() if line.strip()]
    except Exception as e:
        print(f"Gagal ambil sub URL setelah {RETRY} percobaan: {e}")
        return []

# -----------------------
# parsing, generate_xray_config, test_config, main
# Gunakan versi sebelumnya, sama persis, tidak berubah
# -----------------------

if __name__ == "__main__":
    if not setup_xray():
        print("Gagal setup Xray, keluar...")
    else:
        main()  # jalankan fungsi main versi sebelumnya":
    main()
