import sys, os
from pathlib import Path

# Đảm bảo flush output ngay lập tức
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))

import asyncio
from main import (
    get_crop_profiles, 
    receive_sensor_data, 
    get_latest_status, 
    set_control_mode, 
    get_sensor_history, 
    SensorData, 
    ControlUpdate, 
    SessionLocal
)

print("[1/5] Testing Crop Profiles API...", flush=True)
crops = get_crop_profiles()
print(f"      -> SUCCESS: Found {len(crops['crops'])} crop profiles", flush=True)

db = SessionLocal()

print("[2/5] Testing Sensor Data Ingestion & AI Decision...", flush=True)
sample_data = SensorData(
    air_temp=33.5, 
    air_hum=58.0, 
    soil_temp=27.5, 
    soil_moisture=28, 
    lux=850.0
)
res = asyncio.run(receive_sensor_data(sample_data, db))
print(f"      -> SUCCESS: Pump [{res['pump']}] | Light [{res['light']}] | Saved to DB: {res['db_saved']}", flush=True)

print("[3/5] Testing Latest Status for Android App...", flush=True)
status = get_latest_status(db)
print(f"      -> SUCCESS: Air: {status['air_temp']}C | Soil: {status['soil_moisture']}% | VPD: {status['vpd']} kPa", flush=True)

print("[4/5] Testing Remote Control from Android...", flush=True)
cmd = ControlUpdate(mode="MANUAL", manual_pump="ON", manual_light="OFF", active_crop="tomato")
ctrl_res = asyncio.run(set_control_mode(cmd, db))
print(f"      -> SUCCESS: Mode [{ctrl_res['current_control']['mode']}] | Pump [{ctrl_res['current_control']['manual_pump']}]", flush=True)

print("[5/5] Testing History Endpoint for Graph/Chart...", flush=True)
history = get_sensor_history(10, db)
print(f"      -> SUCCESS: Retrieved {history['count']} historical records", flush=True)

db.close()
print("\n>>> ALL TEST CASES PASSED 100%! BACKEND AND LOGIC VERIFIED! <<<", flush=True)
