import math
import time
import requests
from config import OPENWEATHER_API_KEY, OPENWEATHER_CITY

# =========================================================================
# 1. HỒ SƠ CÂY TRỒNG (CROP PROFILES)
# Mỗi loại cây có nhu cầu ẩm độ và điều kiện sinh học khác nhau
# =========================================================================
CROP_PROFILES = {
    "general": {
        "name": "Cây trồng thông thường",
        "min_soil_moisture": 40,
        "optimal_soil_moisture": 65,
        "max_soil_moisture": 85,
        "min_lux": 300,
        "description": "Cấu hình cân bằng cho đa số cây cảnh và hoa thông dụng."
    },
    "tomato": {
        "name": "Cà chua (Tomato)",
        "min_soil_moisture": 50,
        "optimal_soil_moisture": 70,
        "max_soil_moisture": 85,
        "min_lux": 600,
        "description": "Nhu cầu nước đều đặn, không chịu được úng, cần nhiều ánh sáng."
    },
    "melon": {
        "name": "Dưa lưới (Cantaloupe)",
        "min_soil_moisture": 45,
        "optimal_soil_moisture": 65,
        "max_soil_moisture": 80,
        "min_lux": 800,
        "description": "Ưa nắng gắt, tưới nhỏ giọt kiểm soát ẩm chặt chẽ."
    },
    "leafy_greens": {
        "name": "Rau ăn lá (Cải, Xà lách)",
        "min_soil_moisture": 55,
        "optimal_soil_moisture": 75,
        "max_soil_moisture": 90,
        "min_lux": 400,
        "description": "Bộ rễ nông, nhu cầu giữ ẩm đất cao và liên tục."
    },
    "orchid": {
        "name": "Hoa Lan (Orchid)",
        "min_soil_moisture": 30,
        "optimal_soil_moisture": 50,
        "max_soil_moisture": 70,
        "min_lux": 250,
        "description": "Rễ thoáng khí, rất sợ ngập úng gốc, tưới phun sương nhẹ."
    }
}

# =========================================================================
# 2. TÍNH TOÁN CHỈ SỐ SINH HỌC & BỐC THOÁT NƯỚC (VPD & ET0)
# =========================================================================
def calculate_vpd(temp_c: float, rh_percent: float) -> float:
    """
    Tính Thâm hụt Áp suất Hơi nước (VPD - Vapor Pressure Deficit, kPa).
    - VPD < 0.4 kPa: Không khí quá ẩm, cây khó thoát hơi nước, dễ nấm bệnh.
    - VPD 0.8 - 1.2 kPa: Vùng tối ưu quang hợp và hút khoáng của cây.
    - VPD > 1.6 kPa: Không khí quá khô nóng, cây đóng khí khổng, bốc thoát hơi nước mạnh.
    """
    # Áp suất hơi bão hòa (Saturation Vapor Pressure - VP_sat theo công thức Tetens)
    vp_sat = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    # Áp suất hơi thực tế (Actual Vapor Pressure)
    vp_act = vp_sat * (rh_percent / 100.0)
    vpd = vp_sat - vp_act
    return round(max(0.0, vpd), 2)

def estimate_solar_radiation_mj(lux: float) -> float:
    """Ước tính bức xạ mặt trời (MJ/m2/day tương đương) từ chỉ số Lux."""
    # 1 Lux ~ 0.0079 W/m2 (ánh sáng trắng / mặt trời)
    w_m2 = lux * 0.0079
    # Quy đổi tương đương MJ/m2 cho chu kỳ giờ
    return round(w_m2 * 0.0036, 3)

# =========================================================================
# 3. TÍCH HỢP DỰ BÁO THỜI TIẾT (OPENWEATHERMAP)
# =========================================================================
_weather_cache = {"rain_expected": False, "last_check": 0}

def is_rain_expected_soon() -> bool:
    """Kiểm tra xem khu vực có dự báo mưa trong 3 giờ tới không (nếu có cấu hình API Key)."""
    if not OPENWEATHER_API_KEY:
        return False
        
    current_time = time.time()
    # Cache kết quả dự báo trong 30 phút để tránh hết quota API
    if current_time - _weather_cache["last_check"] < 1800:
        return _weather_cache["rain_expected"]

    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={OPENWEATHER_CITY}&appid={OPENWEATHER_API_KEY}&cnt=2"
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            data = res.json()
            rain_detected = False
            for forecast in data.get("list", []):
                weather_main = forecast.get("weather", [{}])[0].get("main", "").lower()
                if "rain" in weather_main or "thunderstorm" in weather_main:
                    rain_detected = True
                    break
            _weather_cache["rain_expected"] = rain_detected
            _weather_cache["last_check"] = current_time
            return rain_detected
    except Exception as e:
        print(f"⚠️ [Weather API Warning]: {e}")

    return False

# =========================================================================
# 4. BỘ PHÁT HIỆN BẤT THƯỜNG HỆ THỐNG (ANOMALY DETECTION)
# =========================================================================
class AnomalyDetector:
    def __init__(self):
        self.consecutive_pump_on_count = 0
        self.last_moisture = None

    def analyze(self, pump_status: str, current_moisture: int) -> dict:
        """
        Phát hiện sự cố:
        - Bơm bật liên tục nhiều chu kỳ mà độ ẩm đất không hề tăng => Cảnh báo:
          1. Bồn chứa hết nước.
          2. Đường ống tưới bị tuột / nghẽn đầu phun.
          3. Cảm biến độ ẩm bị tuột khỏi chậu đất.
        """
        issue = None
        if pump_status == "ON":
            self.consecutive_pump_on_count += 1
            if self.last_moisture is not None and self.consecutive_pump_on_count >= 8:
                if current_moisture <= self.last_moisture:
                    issue = "NGUY_CO_HET_NUOC_HOAC_NGHEN_ONG"
        else:
            self.consecutive_pump_on_count = 0

        self.last_moisture = current_moisture
        return {
            "has_issue": issue is not None,
            "issue_type": issue,
            "pump_cycles": self.consecutive_pump_on_count
        }

anomaly_detector = AnomalyDetector()

# =========================================================================
# 5. BỘ ĐIỀU PHỐI TƯỚI NÔNG NGHIỆP THÔNG MINH (DECISION ENGINE)
# =========================================================================
def evaluate_smart_irrigation(
    sensor_data: dict, 
    crop_code: str = "general", 
    ml_prediction: int = 0
) -> dict:
    """
    Tổng hợp:
    1. Chỉ số cảm biến (Nhiệt, Ẩm đất, Không khí, Lux)
    2. Hồ sơ cây trồng (Crop Profile)
    3. Thâm hụt hơi nước (VPD)
    4. Dự báo thời tiết mưa
    5. Dự đoán từ mô hình Machine Learning
    """
    crop = CROP_PROFILES.get(crop_code, CROP_PROFILES["general"])
    soil_moist = sensor_data["soil_moisture"]
    air_temp = sensor_data["air_temp"]
    air_hum = sensor_data["air_hum"]
    lux = sensor_data["lux"]

    vpd = calculate_vpd(air_temp, air_hum)
    rain_soon = is_rain_expected_soon()

    # Logic chuyên gia Nông nghiệp:
    pump_decision = "OFF"
    reason = []

    if soil_moist < crop["min_soil_moisture"]:
        # Đất khô dưới ngưỡng tối thiểu của cây
        if rain_soon and soil_moist > (crop["min_soil_moisture"] - 5):
            pump_decision = "OFF"
            reason.append("Đất hơi khô nhưng dự báo sắp có mưa, tạm hoãn tưới tiết kiệm nước.")
        else:
            pump_decision = "ON"
            reason.append(f"Độ ẩm đất ({soil_moist}%) dưới ngưỡng tối thiểu của cây {crop['name']} ({crop['min_soil_moisture']}%).")
    elif soil_moist < crop["optimal_soil_moisture"]:
        # Vùng trung gian: Cần tưới nếu bốc thoát hơi nước lớn (VPD cao hoặc trời nóng gắt)
        if vpd > 1.4 or air_temp > 33.0 or ml_prediction == 1:
            pump_decision = "ON"
            reason.append(f"VPD cao ({vpd} kPa) hoặc nhiệt độ cao ({air_temp}°C) làm thoát hơi nước nhanh -> Tưới bổ sung.")
        else:
            pump_decision = "OFF"
            reason.append(f"Độ ẩm đất ổn định ({soil_moist}%), thời tiết mát mẻ -> Không cần tưới.")
    else:
        pump_decision = "OFF"
        reason.append(f"Độ ẩm đất dồi dào ({soil_moist}%), chống úng rễ.")

    # Đèn quang hợp bổ sung
    light_decision = "ON" if lux < crop["min_lux"] else "OFF"

    # Kiểm tra bất thường
    anomaly = anomaly_detector.analyze(pump_decision, soil_moist)

    return {
        "pump": pump_decision,
        "light": light_decision,
        "vpd_kpa": vpd,
        "rain_soon": rain_soon,
        "reason": " | ".join(reason),
        "crop_profile": crop["name"],
        "anomaly": anomaly
    }

