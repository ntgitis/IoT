import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib

# Tạo hạt giống ngẫu nhiên để tái lặp kết quả
np.random.seed(42)
n_samples = 2500

# Sinh dữ liệu mô phỏng môi trường nhiệt đới / nhà kính thực tế
air_temp = np.random.uniform(18.0, 42.0, n_samples)
air_hum = np.random.uniform(35.0, 95.0, n_samples)
soil_temp = np.random.uniform(16.0, 38.0, n_samples)
soil_moisture = np.random.uniform(10.0, 95.0, n_samples)
lux = np.random.uniform(50.0, 25000.0, n_samples)

# Tính toán VPD (Vapor Pressure Deficit) - chỉ số thoát hơi nước sinh học của lá cây
labels = []
for at, ah, st, sm, lx in zip(air_temp, air_hum, soil_temp, soil_moisture, lux):
    # Tính áp suất hơi bão hòa và thực tế
    vp_sat = 0.61078 * np.exp((17.27 * at) / (at + 237.3))
    vp_act = vp_sat * (ah / 100.0)
    vpd = max(0.0, vp_sat - vp_act)

    # Quy tắc Nông nghiệp Sinh thái:
    # 1. Đất khô cạn (< 35%): Luôn cần tưới để bảo vệ rễ
    if sm < 35:
        labels.append(1)
    # 2. Đất quá ẩm (> 65%): Ngừng tưới chống úng và thối rễ
    elif sm > 65:
        labels.append(0)
    else:
        # 3. Vùng ẩm trung bình (35% - 65%):
        # Quyết định dựa trên tốc độ thoát hơi nước (VPD cao > 1.3 hoặc nhiệt độ > 32°C hoặc nắng gắt)
        need_water = (vpd > 1.3) or (at > 32.0 and sm < 50) or (lx > 10000 and sm < 48)
        labels.append(1 if need_water else 0)

df = pd.DataFrame({
    "air_temp": air_temp,
    "air_hum": air_hum,
    "soil_temp": soil_temp,
    "soil_moisture": soil_moisture,
    "lux": lux,
    "label": labels
})

X = df[["air_temp", "air_hum", "soil_temp", "soil_moisture", "lux"]]
y = df["label"]

# Huấn luyện Random Forest
model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
model.fit(X, y)

# Lưu model đã huấn luyện
joblib.dump(model, "smart_irrigation_model.pkl")
print("✅ Đã huấn luyện và cập nhật mô hình Machine Learning mới dựa trên chỉ số VPD Nông học!")
print(f"   Số lượng mẫu: {n_samples}")
print(f"   Tỷ lệ nhãn 1 (Cần tưới): {np.mean(y):.2%}")
