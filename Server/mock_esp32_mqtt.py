"""
KỊCH BẢN GIẢ LẬP ESP32 GIAO TIẾP QUA MQTT (MOCK ESP32 MQTT SIMULATOR)
Dùng để kiểm thử toàn bộ luồng MQTT:
- Bắn dữ liệu cảm biến lên Topic: smartfarm/esp32/sensors
- Lắng nghe lệnh điều khiển tức thì từ App/Server tại Topic: smartfarm/esp32/control/pump và light
"""

import time
import random
import json
import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_TOPIC_SENSORS,
    MQTT_TOPIC_CONTROL_PUMP,
    MQTT_TOPIC_CONTROL_LIGHT,
    MQTT_TOPIC_STATUS
)

# Trạng thái giả lập phần cứng
current_moisture = 38
current_temp = 29.5
current_hum = 65.0
current_lux = 420.0
pump_is_running = False
light_is_running = False

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"✅ [MOCK ESP32] Đã kết nối MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
        # Báo danh online
        client.publish(MQTT_TOPIC_STATUS, "online", qos=1, retain=True)
        # Lắng nghe lệnh điều khiển
        client.subscribe(MQTT_TOPIC_CONTROL_PUMP, qos=1)
        client.subscribe(MQTT_TOPIC_CONTROL_LIGHT, qos=1)
        print(f"👂 [MOCK ESP32] Đang lắng nghe lệnh: {MQTT_TOPIC_CONTROL_PUMP} & {MQTT_TOPIC_CONTROL_LIGHT}")
    else:
        print(f"❌ [MOCK ESP32] Lỗi kết nối (Code: {reason_code})")

def on_message(client, userdata, msg):
    global pump_is_running, light_is_running
    topic = msg.topic
    cmd = msg.payload.decode().strip()
    
    if topic == MQTT_TOPIC_CONTROL_PUMP:
        pump_is_running = (cmd == "ON")
        status_text = "🟢 BẬT MÁY BƠM" if pump_is_running else "🔴 TẮT MÁY BƠM"
        print(f"\n⚡ [MOCK ESP32 NHẬN LỆNH TỨC THÌ] -> {status_text} (Topic: {topic})")
    elif topic == MQTT_TOPIC_CONTROL_LIGHT:
        light_is_running = (cmd == "ON")
        status_text = "💡 BẬT ĐÈN QUANG HỢP" if light_is_running else "🌑 TẮT ĐÈN QUANG HỢP"
        print(f"\n⚡ [MOCK ESP32 NHẬN LỆNH TỨC THÌ] -> {status_text} (Topic: {topic})")

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="mock_esp32_device_" + str(random.randint(1000, 9999))
)

# Cấu hình Last Will & Testament (LWT)
client.will_set(MQTT_TOPIC_STATUS, "offline", qos=1, retain=True)
client.on_connect = on_connect
client.on_message = on_message

print("=" * 60)
print("🌾 KHỞI ĐỘNG GIẢ LẬP ESP32 MQTT (SMART AGRICULTURE)")
print(f"📡 Broker: {MQTT_BROKER}:{MQTT_PORT}")
print("Nhấn Ctrl + C để dừng.")
print("=" * 60)

client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)
client.loop_start()

try:
    cycle = 0
    while True:
        cycle += 1
        time.sleep(5)

        # Mô phỏng biến động môi trường
        current_temp = round(max(20.0, min(38.0, current_temp + random.uniform(-0.3, 0.3))), 1)
        current_hum = round(max(40.0, min(90.0, current_hum + random.uniform(-0.5, 0.5))), 1)
        current_lux = round(max(50.0, min(1500.0, current_lux + random.uniform(-20.0, 20.0))), 1)

        # Mô phỏng tác động của máy bơm
        if pump_is_running:
            current_moisture = min(85, current_moisture + random.randint(2, 4))
        else:
            current_moisture = max(20, current_moisture - random.choice([0, 0, 1]))

        soil_temp = round(current_temp - random.uniform(1.0, 2.0), 1)

        payload = {
            "air_temp": current_temp,
            "air_hum": current_hum,
            "soil_temp": soil_temp,
            "soil_moisture": current_moisture,
            "lux": current_lux
        }

        json_data = json.dumps(payload)
        client.publish(MQTT_TOPIC_SENSORS, json_data, qos=1)
        print(f"📤 [Chu kỳ {cycle:03d}] Bắn cảm biến: Ẩm đất={current_moisture}% | Khí={current_temp}°C | Bơm={'ON' if pump_is_running else 'OFF'}")

except KeyboardInterrupt:
    print("\n🛑 Dừng giả lập ESP32.")
    client.publish(MQTT_TOPIC_STATUS, "offline", qos=1, retain=True)
    client.loop_stop()
    client.disconnect()

