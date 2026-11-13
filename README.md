# 🌾 HỆ THỐNG NÔNG NGHIỆP THÔNG MINH (SMART AGRICULTURE IOT)

Hệ thống giám sát và tưới tiêu nông nghiệp thông minh tự động ứng dụng Trí tuệ Nhân tạo (Machine Learning), giao thức truyền thông công nghiệp **MQTT**, máy chủ điều khiển trung tâm **FastAPI** và ứng dụng di động **Android (Jetpack Compose)**.

---

## 📁 CẤU TRÚC DỰ ÁN SAU KHI TỔ CHỨC LẠI

```text
Smart_Agriculture/
│
├── 📂 ESP32/                                # Tầng Phần cứng & Cảm biến
│   ├── 📂 SmartFarm_ESP32/                  # Mã nguồn Firmware chuẩn Arduino IDE
│   │   └── 📄 SmartFarm_ESP32.ino           # Firmware an toàn (Safe Industrial-Grade)
│   └── 📂 Test_Relay_Pump_Fan/              # Code test độc lập Rơ-le & Công tắc tay
│       └── 📄 Test_Relay_Pump_Fan.ino
│
├── 📂 Server/                               # Tầng Backend & Trí tuệ Nhân tạo
│   ├── 📄 main.py                           # Máy chủ FastAPI + WebSocket + MQTT Gateway
│   ├── 📄 mqtt_service.py                   # Bộ điều phối kết nối MQTT Broker
│   ├── 📄 irrigation_engine.py              # Động cơ phân tích sinh học & tính toán VPD
│   ├── 📄 config.py                         # Quản lý cấu hình hệ thống
│   ├── 📄 smart_irrigation_model.pkl        # Mô hình học máy dự đoán tưới tiêu (AI)
│   ├── 📄 smart_farm.db                     # Cơ sở dữ liệu SQLite cục bộ
│   ├── 📄 mock_esp32_mqtt.py                # Script giả lập ESP32 qua MQTT (thử nghiệm)
│   ├── 📄 run_server.bat                    # Script 1-click khởi chạy Backend
│   ├── 📄 install_requirements.bat          # Script 1-click cài đặt thư viện Python
│   └── 📄 requirements.txt                  # Danh mục dependencies Python
│
├── 📂 SmartAgriculture/                     # Tầng Ứng dụng Di động
│   ├── 📂 app/src/main/                     # Mã nguồn Android (MVVM + Compose)
│   ├── 📄 build.gradle.kts                  # Cấu hình Gradle build app
│   └── 📄 gradlew.bat                       # Gradle wrapper script
│
├── 📄 HARDWARE_WIRING.md                    # Sơ đồ đấu nối dây phần cứng & chống xung
└── 📄 README.md                             # Tài liệu tổng quan dự án
```

---

## ⚡ TÍNH NĂNG NỔI BẬT

### 1. Firmware ESP32 Chuẩn Công Nghiệp (`SmartFarm_ESP32.ino`)
* **Chống giật rơ-le:** Gán trạng thái ngắt trước khi chuyển chân sang `OUTPUT`.
* **Bảo vệ máy bơm 4 tầng:** 
  1. Tự ngắt sau 60s chạy liên tục.
  2. Nghỉ chống rung Cooldown 3s giữa các lần bơm.
  3. Khóa cứng an toàn (`pumpTimeoutLock`) yêu cầu lệnh "OFF" để xác nhận mở khóa.
  4. Giới hạn tối đa 10 phút bơm trong mỗi 1 giờ để chống ngập úng.
* **Điều khiển Hybrid 2 chiều:** Hỗ trợ công tắc tay vật lý tại chỗ (GPIO 5 & GPIO 4) có chống dội phím (Edge Detection) và đồng bộ trạng thái ngay lập tức với App Android.
* **Lọc nhiễu cảm biến:** Thuật toán Oversampling lấy mẫu 10 lần liên tục cho cảm biến độ ẩm đất.
* **Tự hành ngoại tuyến (Offline Fail-Safe):** Khi rớt mạng hoặc tắt server, ESP32 tự động kích hoạt tưới cứu cây nếu đất khô `< 35%`.
* **Last Will and Testament (LWT):** Báo cáo trạng thái `online` / `offline` tới Broker ngay lập tức khi kit bị mất nguồn.

### 2. Backend FastAPI & MQTT Gateway
* **Cầu nối Hybrid:** Nhận dữ liệu phần cứng qua **MQTT**, phục vụ di động qua **WebSocket** (Realtime Stream) và **REST API** (Biểu đồ, Lịch sử).
* **Trí tuệ nhân tạo:** Tích hợp mô hình `RandomForest` kết hợp tính toán áp suất bốc hơi nước (`VPD`) theo từng hồ sơ cây trồng (Cà chua, Dưa lưới, Hoa lan, Rau ăn lá,...).
* **Chống nghẽn Database (Deadband Throttling):** Tối ưu hóa chu kỳ ghi dữ liệu định kỳ 60s hoặc khi trạng thái thiết bị thay đổi.

### 3. Ứng dụng Android Hiện Đại
* **Giao diện:** 100% Jetpack Compose + Material 3.
* **Kiến trúc:** MVVM Clean Architecture, StateFlow, Coroutines.
* **Độ trễ điều khiển:** Bấm nút điều khiển trên App -> Server đẩy lệnh qua MQTT tới ESP32 với độ trễ `< 50ms`.

---

## 🚀 HƯỚNG DẪN VẬN HÀNH NHANH

### Bước 1: Khởi động Backend Server
Nhấp đúp chuột vào file:
```text
Server/run_server.bat
```
Server sẽ chạy tại `http://localhost:8000` (hoặc IP Wi-Fi laptop). Trang tài liệu API tương tác có tại `http://localhost:8000/docs`.

### Bước 2: Nạp code ESP32
1. Mở Arduino IDE.
2. Mở file `ESP32/SmartFarm_ESP32/SmartFarm_ESP32.ino`.
3. Cắm kit ESP32 vào cổng USB -> Chọn đúng cổng COM và Board `ESP32 Dev Module`.
4. Nhấn **Upload**.

### Bước 3: Mở App Android
1. Mở Android Studio -> Chọn **Open** thư mục `SmartAgriculture`.
2. Để Gradle tự động đồng bộ và bấm **Run** lên máy ảo hoặc điện thoại Android thật.

