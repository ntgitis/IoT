import json
import logging
import uuid
from typing import Callable, Optional
import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_USER,
    MQTT_PASSWORD,
    MQTT_TOPIC_SENSORS,
    MQTT_TOPIC_CONTROL_PUMP,
    MQTT_TOPIC_CONTROL_LIGHT,
    MQTT_TOPIC_STATUS
)

logger = logging.getLogger("MQTT_SERVICE")

class MQTTService:
    def __init__(self):
        # Sử dụng API Version 2 của Paho MQTT kèm Client ID ngẫu nhiên chống xung đột trên Broker công cộng
        client_id = f"smartfarm_backend_{uuid.uuid4().hex[:6]}"
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id
        )
        if MQTT_USER and MQTT_PASSWORD:
            self.client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self.is_connected = False
        self.on_sensor_callback: Optional[Callable[[dict], None]] = None
        self.on_status_callback: Optional[Callable[[str], None]] = None

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            self.is_connected = True
            print(f"📡 [MQTT] Kết nối thành công tới Broker: {MQTT_BROKER}:{MQTT_PORT}")
            # Đăng ký nhận dữ liệu cảm biến và trạng thái ESP32
            self.client.subscribe(MQTT_TOPIC_SENSORS, qos=1)
            self.client.subscribe(MQTT_TOPIC_STATUS, qos=1)
            print(f"📡 [MQTT] Đã Subscribe: {MQTT_TOPIC_SENSORS} & {MQTT_TOPIC_STATUS}")
        else:
            print(f"⚠️ [MQTT] Lỗi kết nối Broker (Reason Code: {reason_code})")

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.is_connected = False
        print(f"🔌 [MQTT] Mất kết nối tới Broker (Code: {reason_code}). Sẽ tự động kết nối lại...")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload_str = msg.payload.decode("utf-8")
        except Exception:
            payload_str = str(msg.payload)

        # 1. Dữ liệu cảm biến từ ESP32
        if topic == MQTT_TOPIC_SENSORS:
            try:
                data = json.loads(payload_str)
                if self.on_sensor_callback:
                    self.on_sensor_callback(data)
            except json.JSONDecodeError:
                print(f"⚠️ [MQTT] Lỗi parse JSON từ {topic}: {payload_str}")
            except Exception as e:
                print(f"❌ [MQTT] Lỗi xử lý cảm biến: {e}")

        # 2. Trạng thái sống/chết (LWT) của ESP32
        elif topic == MQTT_TOPIC_STATUS:
            print(f"📢 [MQTT LWT] Trạng thái ESP32: {payload_str}")
            if self.on_status_callback:
                try:
                    self.on_status_callback(payload_str)
                except Exception as e:
                    print(f"❌ [MQTT] Lỗi xử lý status: {e}")

    def publish_pump_command(self, command: str, retain: bool = True):
        """Bắn lệnh ON/OFF tới máy bơm (retain=True để đảm bảo ESP32 luôn nhận trạng thái mới nhất)"""
        self.publish(MQTT_TOPIC_CONTROL_PUMP, command, retain=retain)

    def publish_light_command(self, command: str, retain: bool = True):
        """Bắn lệnh ON/OFF tới đèn (retain=True để đảm bảo ESP32 luôn nhận trạng thái mới nhất)"""
        self.publish(MQTT_TOPIC_CONTROL_LIGHT, command, retain=retain)

    def publish(self, topic: str, payload: str, qos: int = 1, retain: bool = False):
        if not self.is_connected:
            print(f"⚠️ [MQTT] Chưa kết nối Broker, đang cố gắng gửi tới {topic}: {payload}")
        try:
            self.client.publish(topic, payload, qos=qos, retain=retain)
            print(f"⚡ [MQTT LỆNH ĐIỀU KHIỂN] -> {topic}: {payload} (retain={retain})")
        except Exception as e:
            print(f"❌ [MQTT] Lỗi publish {topic}: {e}")

    def start(self):
        try:
            print(f"🔄 [MQTT] Đang kết nối tới Broker {MQTT_BROKER}:{MQTT_PORT}...")
            self.client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            print(f"⚠️ [MQTT] Không thể khởi động MQTT Client: {e}")

    def stop(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
            print("🛑 [MQTT] Đã dừng MQTT Client.")
        except Exception:
            pass

mqtt_service = MQTTService()

