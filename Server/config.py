import os
from pathlib import Path
from dotenv import load_dotenv

# Tải cấu hình từ file .env nếu có
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:Nam123456@localhost:5432/greenhouse_db"
)

API_KEY = os.getenv("API_KEY", "smart_farm_secret_key_2026")

DB_LOG_INTERVAL_SECONDS = int(os.getenv("DB_LOG_INTERVAL_SECONDS", "60"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ALERT_ENABLED = os.getenv("TELEGRAM_ALERT_ENABLED", "false").lower() in ("true", "1", "yes")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
OPENWEATHER_CITY = os.getenv("OPENWEATHER_CITY", "Hanoi,VN")

# Cấu hình MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.emqx.io")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPIC_SENSORS = os.getenv("MQTT_TOPIC_SENSORS", "smartfarm/esp32/sensors")
MQTT_TOPIC_CONTROL_PUMP = os.getenv("MQTT_TOPIC_CONTROL_PUMP", "smartfarm/esp32/control/pump")
MQTT_TOPIC_CONTROL_LIGHT = os.getenv("MQTT_TOPIC_CONTROL_LIGHT", "smartfarm/esp32/control/light")
MQTT_TOPIC_STATUS = os.getenv("MQTT_TOPIC_STATUS", "smartfarm/esp32/status")

