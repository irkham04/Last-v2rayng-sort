# V2Ray Config Checker

Tool otomatis untuk menyortir config VLESS, VMess, Trojan dari subscription URL yang masih aktif (latency < 5 detik). Berjalan setiap 5 menit via GitHub Actions.

## Cara Kerja
- Ambil config dari SUB_URL (rahasia).
- Test koneksi menggunakan Xray core (didownload otomatis).
- Simpan config aktif ke `active_configs.txt`, diurutkan berdasarkan latency tercepat.

## Contoh `active_configs.txt`
vmess://eyJ2IjoiMiIsInBzIjoiTest1IiwiYWR... # Latency: 150ms vless://uuid@server.com:443?type=ws&path=/ws... # Latency: 200ms trojan://password@server.com:443?sni=example.com # Latency: 250ms
## Catatan
- Update SUB_URL di Settings > Secrets and variables > Actions jika perlu.
- Jalankan manual di tab Actions > V2Ray Config Checker > Run workflow.
- Untuk config kompleks (misal gRPC, reality), sesuaikan parsing di `checker.py`.
