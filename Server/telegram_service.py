import time
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ALERT_ENABLED

# Bộ nhớ đệm lưu thời gian gửi cảnh báo gần nhất để chống spam (cooldown 10 phút)
_last_alert_times = {}
ALERT_COOLDOWN_SECONDS = 600

def send_telegram_message(text: str) -> bool:
    """Gửi tin nhắn trực tiếp qua Telegram Bot API."""
    if not TELEGRAM_ALERT_ENABLED or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        return res.status_code == 200
    except Exception as e:
        print(f"⚠️ [Telegram Alert Error]: {e}")
        return False

def check_and_send_alerts(sensor_data: dict, pump_status: str, light_status: str):
    """
    Kiểm tra các chỉ số bất thường và gửi cảnh báo tự động có chống spam:
    - Nhiệt độ không khí quá cao (> 38°C) hoặc quá thấp (< 12°C)
    - Độ ẩm đất kiệt quệ (< 20%)
    - Cảnh báo rơ-le hoạt động bất thường
    """
    current_time = time.time()
    alerts = []

    # 1. Kiểm tra nhiệt độ
    temp = sensor_data.get("air_temp", 25.0)
    if temp > 38.0:
        key = "high_temp"
        if current_time - _last_alert_times.get(key, 0) > ALERT_COOLDOWN_SECONDS:
            alerts.append(f"🔥 <b>CẢNH BÁO NHIỆT ĐỘ QUÁ CAO!</b>\nNhiệt độ hiện tại: <b>{temp}°C</b> (Nguy cơ cháy lá/héo rũ).")
            _last_alert_times[key] = current_time
    elif temp < 12.0:
        key = "low_temp"
        if current_time - _last_alert_times.get(key, 0) > ALERT_COOLDOWN_SECONDS:
            alerts.append(f"❄️ <b>CẢNH BÁO NHIỆT ĐỘ QUÁ THẤP!</b>\nNhiệt độ hiện tại: <b>{temp}°C</b> (Nguy cơ rét hại cây).")
            _last_alert_times[key] = current_time

    # 2. Kiểm tra độ ẩm đất
    soil_moist = sensor_data.get("soil_moisture", 50)
    if soil_moist < 20:
        key = "dry_soil"
        if current_time - _last_alert_times.get(key, 0) > ALERT_COOLDOWN_SECONDS:
            alerts.append(f"🏜️ <b>CẢNH BÁO ĐẤT KHÔ CẠN!</b>\nĐộ ẩm đất chỉ còn: <b>{soil_moist}%</b>.\nTrạng thái bơm hiện tại: <b>{pump_status}</b>.")
            _last_alert_times[key] = current_time

    # Gửi tin nhắn nếu có cảnh báo mới
    for msg in alerts:
        formatted = f"🚨 <b>[SMART AGRICULTURE NOTIFICATION]</b>\n\n{msg}\n\n⏱️ Thời gian: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_message(formatted)

