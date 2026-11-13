"""
KỊCH BẢN GIẢ LẬP ESP32 GỬI DỮ LIỆU CẢM BIẾN (MOCK SIMULATOR)
Dùng để kiểm tra giao diện Android App hoạt động trực tiếp ngay cả khi chưa cắm ESP32 thật!
"""

import time
import random
import requests

SERVER_URL = "http://127.0.0.1:8000/api/sensor-data"
API_KEY = "smart_farm_secret_key_2026"

# Trạng thái ban đầu
current_moisture = 38
current_temp = 29.5
current_hum = 65.0
current_lux = 420.0
pump_is_running = False

print("=" * 60)
print("🌾 BẮT ĐẦU CHƯƠNG TRÌNH GIẢ LẬP ESP32 (SMART AGRICULTURE)")
print(f"📡 Gửi tới máy chủ: {SERVER_URL}")
print("💡 Mẹo: Mở App Android trên điện thoại để xem thông số nhảy số trực tiếp!")
print("Nhấn Ctrl + C để dừng giả lập.")
print("=" * 60)

cycle = 0
try:
    while True:
        cycle += 1

        # Mô phỏng biến động tự nhiên của môi trường
        temp_delta = random.uniform(-0.3, 0.3)
        current_temp = round(max(20.0, min(38.0, current_temp + temp_delta)), 1)
        
        hum_delta = random.uniform(-0.5, 0.5)
        current_hum = round(max(40.0, min(90.0, current_hum + hum_delta)), 1)
        
        lux_delta = random.uniform(-25.0, 25.0)
        current_lux = round(max(50.0, min(1500.0, current_lux + lux_delta)), 1)

        # Mô phỏng tác động của máy bơm: nếu bơm BẬT thì độ ẩm tăng dần, tắt thì đất khô dần
        if pump_is_running:
            current_moisture = min(85, current_moisture + random.randint(2, 4))
        else:
            current_moisture = max(20, current_moisture - random.choice([0, 0, 1]))

        soil_temp = round(current_temp - random.uniform(1.0, 2.5), 1)

        payload = {
            "air_temp": current_temp,
            "air_hum": current_hum,
            "soil_temp": soil_temp,
            "soil_moisture": current_moisture,
            "lux": current_lux
        }

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": API_KEY
        }

        try:
            res = requests.post(SERVER_URL, json=payload, headers=headers, timeout=4)
            if res.status_code == 200:
                data = res.json()
                pump_cmd = data.get("pump", "OFF")
                light_cmd = data.get("light", "OFF")
                mode = data.get("mode", "AUTO")
                pump_is_running = (pump_cmd == "ON")

                print(
                    f"[{time.strftime('%H:%M:%S')}] Chu kỳ #{cycle:03d} | "
                    f"Đất: {current_moisture}% | Khí: {current_temp}°C - {current_hum}% | "
                    f"Sáng: {current_lux} Lux -> "
                    f"Lệnh: Bơm [{pump_cmd}] | Đèn [{light_cmd}] (Chế độ: {mode})"
                )
            else:
                print(f"⚠️ Server trả lời lỗi: Mã {res.status_code}")
        except Exception as e:
            print(f"❌ Không kết nối được Server ({e}). Đảm bảo uvicorn đang chạy!")

        time.sleep(4)

except KeyboardInterrupt:
    print("\n🛑 Đã dừng chương trình giả lập ESP32.")

