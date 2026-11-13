# SƠ ĐỒ ĐẤU NỐI PHẦN CỨNG CHI TIẾT (SMART AGRICULTURE)

Tài liệu này hướng dẫn chi tiết cách đấu nối các cảm biến và rơ-le điều khiển với kit **ESP32 NodeMCU-32S** một cách an toàn, chống cháy chập và chống sụt nguồn khi máy bơm hoạt động.

---

### 1. Bảng phân bổ chân kết nối (Pinout Mapping)

| Thiết bị / Cảm biến | Chân trên Cảm biến | Chân kết nối trên ESP32 | Ghi chú quan trọng |
| :--- | :--- | :--- | :--- |
| **Cảm biến độ ẩm đất** | VCC | **3V3** | Dùng nguồn 3.3V để điện áp AOUT không vượt quá ngưỡng ADC |
| *(Soil Moisture)* | GND | **GND** | Nối chung mass |
| | AOUT | **GPIO 32** | Chân ADC1_CH4 (đọc analog 12-bit từ 0 đến 4095) |
| **Cảm biến nhiệt ẩm khí** | VCC (+) | **3V3** (hoặc 5V) | DHT11 hoặc DHT22 |
| *(DHT11 / DHT22)* | GND (-) | **GND** | |
| | DATA (Out) | **GPIO 18** | Có thể cần trở kéo 10k lên 3.3V nếu dùng module không có sẵn trở |
| **Cảm biến nhiệt độ đất** | Dây Đỏ (VCC) | **3V3** | DS18B20 chống nước bọc kim loại |
| *(DS18B20)* | Dây Đen (GND) | **GND** | |
| | Dây Vàng (DATA) | **GPIO 16** | **BẮT BUỘC:** Mắc 1 điện trở **4.7kΩ** giữa dây Vàng (DATA) và Đỏ (VCC) |
| **Cảm biến ánh sáng** | VCC | **3V3** | Giao tiếp I2C chuẩn |
| *(BH1750)* | GND | **GND** | |
| | SCL | **GPIO 22** | Chân I2C Clock mặc định của ESP32 |
| | SDA | **GPIO 21** | Chân I2C Data mặc định của ESP32 |
| | ADDR | Không nối (hoặc GND)| Địa chỉ I2C mặc định `0x23` |
| **Module Rơ-le 2 kênh** | VCC | **VIN (5V)** | Cấp 5V để cuộn hút rơ-le đóng dứt khoát |
| *(2-Channel Relay)* | GND | **GND** | Nối chung GND với ESP32 |
| | IN1 (Máy bơm) | **GPIO 26** | Kích mức HIGH (Bật khi chân lên 3.3V) |
| | IN2 (Quạt / Đèn) | **GPIO 27** | Kích mức HIGH |
| **Công tắc tay Máy Bơm** | Chân 1 | **GPIO 5** | INPUT_PULLUP (không cần trở ngoài) |
| *(Toggle Switch Bơm)* | Chân 2 | **GND** | Gạt BẬT (nối GND) -> Bật Bơm, Gạt TẮT -> Tắt Bơm |
| **Công tắc tay Quạt/Đèn** | Chân 1 | **GPIO 4** | INPUT_PULLUP (không cần trở ngoài) |
| *(Toggle Switch Quạt)* | Chân 2 | **GND** | Gạt BẬT (nối GND) -> Bật Quạt, Gạt TẮT -> Tắt Quạt |

---

### 2. Sơ đồ mạch đấu nối nguồn cho Máy bơm và Rơ-le

```
 [Nguồn 12V DC / 5V ngoài] ──(+)─────────────── [Cực COM của Rơ-le 1]
                                                      │
                                                [Cực NO của Rơ-le 1]
                                                      │
                                                [(+) Dây đỏ Máy Bơm]
                                                [(-) Dây đen Máy Bơm]
 [Cực (-) Nguồn ngoài] ───────────────────────────────┘
```

> [!CAUTION]
> **Chống nhiễu và sụt áp khi Bơm khởi động:**
> Máy bơm nước là tải cảm ứng (Inductive Load). Khi đóng ngắt, cuộn dây máy bơm sinh ra tia lửa điện và xung điện áp ngược có thể làm **ESP32 bị treo hoặc tự reset**.
> 1. **Dùng nguồn riêng:** Không lấy chân 3.3V của ESP32 để nuôi trực tiếp motor máy bơm. Hãy cấp nguồn 12V/5V riêng cho bơm qua tiếp điểm COM-NO của rơ-le.
> 2. **Diode dập xung (Flyback Diode):** Nên gắn thêm 1 con diode `1N4007` mắc ngược cực song song với 2 đầu dây máy bơm để dập xung điện cảm ứng.
> 3. **Rơ-le cách ly quang (Optocoupler):** Giữ nguyên nắp jumper `JD-VCC` trên rơ-le nếu dùng chung nguồn 5V, hoặc tháo jumper ra để cấp nguồn cuộn hút hoàn toàn độc lập với ESP32.

