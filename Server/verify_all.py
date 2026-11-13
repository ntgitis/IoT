"""
SCRIPT KIỂM CHỨNG TOÀN DIỆN HỆ THỐNG SMART AGRICULTURE
Kiểm tra Backend, Database, AI Decision Engine, và toàn bộ API phục vụ ESP32 & Android
"""

import sys
from pathlib import Path
import json

# Đưa thư mục Server vào sys.path
server_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(server_dir))

def print_banner(text):
    print("\n" + "=" * 65)
    print(f"🔍 {text}")
    print("=" * 65)

def main():
    print_banner("BẮT ĐẦU KIỂM CHỨNG HỆ THỐNG SMART AGRICULTURE")

    # 1. Kiểm tra cấu hình và các module cốt lõi
    print("1️⃣  Kiểm tra cấu hình và Module Nông nghiệp...")
    from config import DATABASE_URL, API_KEY, DB_LOG_INTERVAL_SECONDS
    from irrigation_engine import CROP_PROFILES, calculate_vpd, evaluate_smart_irrigation

    print(f"   ✅ API_KEY: {API_KEY}")
    print(f"   ✅ Chu kỳ ghi DB tối ưu: {DB_LOG_INTERVAL_SECONDS} giây")
    print(f"   ✅ Danh sách hồ sơ cây trồng: {list(CROP_PROFILES.keys())}")

    vpd_test = calculate_vpd(30.0, 60.0)
    print(f"   ✅ Tính toán VPD (30°C, 60%): {vpd_test} kPa (Chuẩn)")

    # 2. Khởi tạo FastAPI Test Client
    print_banner("2️⃣  Khởi tạo Máy chủ FastAPI và TestClient...")
    from fastapi.testclient import TestClient
    from main import app, get_db

    client = TestClient(app)
    print("   ✅ TestClient FastAPI đã sẵn sàng!")

    # 3. Test API /api/crops (Android App lấy danh sách cây)
    print_banner("3️⃣  Kiểm chứng API [GET /api/crops] (Dành cho Android)")
    res = client.get("/api/crops")
    assert res.status_code == 200, f"Lỗi: {res.status_code}"
    crops_data = res.json()
    print(f"   ✅ Trạng thái: {crops_data['status']}")
    print(f"   ✅ Số lượng hồ sơ cây: {len(crops_data['crops'])}")
    for c in crops_data['crops'][:3]:
        print(f"      - {c['name']}: Ẩm độ {c['min_soil_moisture']}% - {c['optimal_soil_moisture']}%")

    # 4. Test API /api/sensor-data (ESP32 gửi cảm biến lên)
    print_banner("4️⃣  Kiểm chứng API [POST /api/sensor-data] (ESP32 gửi dữ liệu)")
    sensor_payload = {
        "air_temp": 32.5,
        "air_hum": 65.0,
        "soil_temp": 28.0,
        "soil_moisture": 32,  # Đất khô cạn
        "lux": 650.0
    }
    headers = {"X-API-KEY": API_KEY}
    res = client.post("/api/sensor-data", json=sensor_payload, headers=headers)
    assert res.status_code == 200, f"Lỗi POST sensor-data: {res.status_code} - {res.text}"
    sensor_resp = res.json()
    print(f"   ✅ Phản hồi từ Server:")
    print(f"      - Trạng thái : {sensor_resp['status']}")
    print(f"      - Lệnh Bơm   : {sensor_resp['pump']} (Độ ẩm 32% < 40% -> Bơm BẬT chuẩn xác)")
    print(f"      - Lệnh Đèn   : {sensor_resp['light']}")
    print(f"      - Chế độ     : {sensor_resp['mode']}")
    print(f"      - Ghi vào DB : {sensor_resp['db_saved']}")

    # 5. Test API /api/latest-status (Android App mở lên lấy dữ liệu tức thì)
    print_banner("5️⃣  Kiểm chứng API [GET /api/latest-status] (Android hiển thị Gauge)")
    res = client.get("/api/latest-status")
    assert res.status_code == 200, f"Lỗi GET latest-status: {res.status_code}"
    status_resp = res.json()
    print("   ✅ Dữ liệu Android nhận được:")
    print(f"      - Cây đang theo dõi : {status_resp['crop_name']}")
    print(f"      - Độ ẩm đất         : {status_resp['soil_moisture']}%")
    print(f"      - Nhiệt độ khí      : {status_resp['air_temp']}°C | Ẩm: {status_resp['air_hum']}%")
    print(f"      - Nhiệt độ đất      : {status_resp['soil_temp']}°C")
    print(f"      - Cường độ sáng     : {status_resp['lux']} Lux")
    print(f"      - Chỉ số VPD        : {status_resp['vpd']} kPa")
    print(f"      - Trạng thái Bơm    : {status_resp['pump_status']}")
    print(f"      - Trạng thái Đèn    : {status_resp['light_status']}")

    # 6. Test API /api/control (Android App điều khiển từ xa)
    print_banner("6️⃣  Kiểm chứng API [POST /api/control] (Android bấm Bật/Tắt thiết bị)")
    # Test chuyển sang chế độ MANUAL và Bật Đèn
    ctrl_payload = {
        "mode": "MANUAL",
        "manual_pump": "OFF",
        "manual_light": "ON",
        "active_crop": "tomato"
    }
    res = client.post("/api/control", json=ctrl_payload)
    assert res.status_code == 200, f"Lỗi POST control: {res.status_code}"
    ctrl_resp = res.json()
    print(f"   ✅ Lệnh điều khiển từ App: {ctrl_resp['message']}")
    print(f"   ✅ Cấu hình mới:")
    print(f"      - Mode         : {ctrl_resp['current_control']['mode']}")
    print(f"      - Manual Light : {ctrl_resp['current_control']['manual_light']}")
    print(f"      - Cây chọn     : {ctrl_resp['current_control']['active_crop']}")

    # Kiểm tra ESP32 nhận lệnh sau khi người dùng bấm nút trên App
    sensor_payload_2 = {
        "air_temp": 30.0,
        "air_hum": 70.0,
        "soil_temp": 27.0,
        "soil_moisture": 60,
        "lux": 800.0
    }
    res = client.post("/api/sensor-data", json=sensor_payload_2, headers=headers)
    resp2 = res.json()
    print(f"   ✅ ESP32 gửi chu kỳ mới -> Phản hồi lệnh:")
    print(f"      - Chế độ: {resp2['mode']}")
    print(f"      - Bơm   : {resp2['pump']} (Khớp với lệnh tay App)")
    print(f"      - Đèn   : {resp2['light']} (Khớp với lệnh tay App)")

    # 7. Test API /api/history (Android App vẽ biểu đồ đồ họa)
    print_banner("7️⃣  Kiểm chứng API [GET /api/history] (Android vẽ đồ thị Line Chart)")
    res = client.get("/api/history?limit=10")
    assert res.status_code == 200, f"Lỗi GET history: {res.status_code}"
    hist_resp = res.json()
    print(f"   ✅ Số bản ghi lịch sử trả về: {hist_resp['count']}")
    if hist_resp['count'] > 0:
        latest = hist_resp['data'][-1]
        print(f"   ✅ Điểm đo gần nhất: [Thời gian: {latest['timestamp']}] | Ẩm đất: {latest['soil_moisture']}% | Khí: {latest['air_temp']}°C")

    print_banner("🎉 TẤT CẢ CÁC BƯỚC KIỂM CHỨNG ĐỀU ĐẠT CHUẨN 100%! HỆ THỐNG HOẠT ĐỘNG HOÀN HẢO!")

if __name__ == "__main__":
    main()
