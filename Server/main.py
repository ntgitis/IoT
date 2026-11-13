import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Literal, Optional, List
from contextlib import asynccontextmanager
import pandas as pd
import joblib

from fastapi import FastAPI, Depends, Query, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, desc, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Import các module nội bộ
from config import DATABASE_URL, API_KEY, DB_LOG_INTERVAL_SECONDS
from telegram_service import check_and_send_alerts
from irrigation_engine import (
    CROP_PROFILES, 
    evaluate_smart_irrigation, 
    calculate_vpd, 
    is_rain_expected_soon
)
from mqtt_service import mqtt_service

# --- 1. CẤU HÌNH DATABASE (POSTGRESQL KÈM SQLITE DỰ PHÒNG) ---
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"connect_timeout": 3})
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("🐘 Kết nối PostgreSQL thành công!")
    is_postgres = True
except Exception as e:
    print(f"⚠️ Chưa kết nối được PostgreSQL: {e}")
    print("🔄 Tự động chuyển sang SQLite dự phòng (smart_farm.db) để hệ thống hoạt động liên tục!")
    engine = create_engine("sqlite:///./smart_farm.db", connect_args={"check_same_thread": False})
    is_postgres = False

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SensorLogDB(Base):
    __tablename__ = "sensor_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    air_temp = Column(Float)
    air_hum = Column(Float)
    soil_temp = Column(Float)
    soil_moisture = Column(Integer)
    lux = Column(Float)
    pump_status = Column(String(10))
    light_status = Column(String(10), default="OFF")
    vpd = Column(Float, nullable=True)

class SystemControlDB(Base):
    __tablename__ = "system_control"
    
    id = Column(Integer, primary_key=True, default=1)
    mode = Column(String(10), default="AUTO")              # "AUTO" hoặc "MANUAL"
    manual_pump = Column(String(10), default="OFF")        # "ON" hoặc "OFF"
    manual_light = Column(String(10), default="OFF")       # "ON" hoặc "OFF"
    lux_threshold = Column(Float, default=300.0)           # Ngưỡng bật đèn
    active_crop = Column(String(50), default="general")    # Hồ sơ cây trồng đang kích hoạt

Base.metadata.create_all(bind=engine)

# Đảm bảo các cột mới có sẵn trong DB nếu đang dùng PostgreSQL
if is_postgres:
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE sensor_logs ADD COLUMN IF NOT EXISTS light_status VARCHAR(10) DEFAULT 'OFF';"))
            conn.execute(text("ALTER TABLE sensor_logs ADD COLUMN IF NOT EXISTS vpd FLOAT DEFAULT 0.0;"))
            conn.execute(text("ALTER TABLE system_control ADD COLUMN IF NOT EXISTS active_crop VARCHAR(50) DEFAULT 'general';"))
            conn.commit()
    except Exception:
        pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_control_state(db: Session) -> SystemControlDB:
    ctrl = db.query(SystemControlDB).filter(SystemControlDB.id == 1).first()
    if not ctrl:
        ctrl = SystemControlDB(
            id=1, 
            mode="AUTO", 
            manual_pump="OFF", 
            manual_light="OFF", 
            lux_threshold=300.0,
            active_crop="general"
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)
    return ctrl

# --- 2. QUẢN LÝ WEBSOCKET KẾT NỐI REALTIME CHO ANDROID APP ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        """Bắn dữ liệu thời gian thực tới tất cả các điện thoại Android đang mở app"""
        message = json.dumps(data)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

ws_manager = ConnectionManager()

# --- 3. LIFESPAN QUẢN LÝ MQTT CLIENT & FASTAPI ---
main_loop = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    print("🚀 [STARTUP] Khởi động MQTT Service kết nối Broker...")
    mqtt_service.start()
    yield
    print("🛑 [SHUTDOWN] Đang dừng MQTT Service...")
    mqtt_service.stop()

app = FastAPI(
    title="Smart Agriculture IoT Backend", 
    version="2.1.0",
    description="Backend điều khiển nông nghiệp thông minh qua MQTT và WebSocket cho Android App",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load AI model
try:
    from pathlib import Path
    model_path = Path(__file__).resolve().parent / "smart_irrigation_model.pkl"
    ai_model = joblib.load(str(model_path))
    print("🤖 Nạp Mô hình AI thành công!")
except Exception as e:
    ai_model = None
    print(f"⚠️ Chưa có file model AI: {e}. Sẽ dùng bộ não quy tắc sinh học.")

# Biến đệm kiểm soát tần suất ghi database (Deadband / Throttling)
last_db_save_time = 0.0
last_logged_pump_state = ""
last_logged_light_state = ""

# --- 4. SCHEMAS CHO ANDROID APP & ESP32 ---
class SensorData(BaseModel):
    air_temp: float = Field(..., ge=-10.0, le=65.0, description="Nhiệt độ không khí (°C)")
    air_hum: float = Field(..., ge=0.0, le=100.0, description="Độ ẩm không khí (%)")
    soil_temp: float = Field(..., ge=-10.0, le=65.0, description="Nhiệt độ đất (°C)")
    soil_moisture: int = Field(..., ge=0, le=100, description="Độ ẩm đất (%)")
    lux: float = Field(..., ge=0.0, le=100000.0, description="Cường độ sáng (Lux)")

class ControlUpdate(BaseModel):
    mode: Literal["AUTO", "MANUAL"]
    manual_pump: Optional[Literal["ON", "OFF"]] = None
    manual_light: Optional[Literal["ON", "OFF"]] = None
    lux_threshold: Optional[float] = Field(None, ge=0.0, le=10000.0)
    active_crop: Optional[str] = None

def safe_float(val, default: float) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default: int) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

# --- 5. HÀM XỬ LÝ DỮ LIỆU CẢM BIẾN DÙNG CHUNG (CHO CẢ HTTP & MQTT) ---
def process_sensor_pipeline(data_dict: dict, db: Session) -> dict:
    global last_db_save_time, last_logged_pump_state, last_logged_light_state, main_loop

    air_temp = safe_float(data_dict.get("air_temp"), 25.0)
    air_hum = safe_float(data_dict.get("air_hum"), 60.0)
    soil_temp = safe_float(data_dict.get("soil_temp"), 25.0)
    soil_moisture = safe_int(data_dict.get("soil_moisture"), 50)
    lux = safe_float(data_dict.get("lux"), 500.0)

    # 1. Dự đoán AI (nếu có model)
    ml_prediction = 0
    if ai_model is not None:
        try:
            input_df = pd.DataFrame([{
                "air_temp": air_temp,
                "air_hum": air_hum,
                "soil_temp": soil_temp,
                "soil_moisture": soil_moisture,
                "lux": lux
            }])
            ml_prediction = int(ai_model.predict(input_df)[0])
        except Exception as e:
            print(f"Lỗi AI prediction: {e}")

    # 2. Lấy cấu hình hệ thống
    ctrl = get_control_state(db)
    vpd_val = calculate_vpd(air_temp, air_hum)

    # Nếu người dùng gạt công tắc tay vật lý trên ESP32 -> Ưu tiên chuyển sang MANUAL & đồng bộ 2 chiều
    if data_dict.get("source") == "physical_switch":
        ctrl.mode = "MANUAL"
        hw_pump_on = data_dict.get("pump_on")
        hw_light_on = data_dict.get("light_on")
        if hw_pump_on is not None:
            ctrl.manual_pump = "ON" if hw_pump_on else "OFF"
        if hw_light_on is not None:
            ctrl.manual_light = "ON" if hw_light_on else "OFF"
        db.commit()
        db.refresh(ctrl)
        if mqtt_service.is_connected:
            mqtt_service.publish_pump_command(ctrl.manual_pump)
            mqtt_service.publish_light_command(ctrl.manual_light)

    # 3. Tính toán quyết định điều khiển
    if ctrl.mode == "MANUAL":
        pump_command = ctrl.manual_pump
        light_command = ctrl.manual_light
        smart_info = {"reason": "Điều khiển thủ công (App Android hoặc Công tắc tại chỗ)"}
    else:
        # Sử dụng Engine nông nghiệp thông minh
        smart_result = evaluate_smart_irrigation(
            sensor_data={
                "air_temp": air_temp,
                "air_hum": air_hum,
                "soil_temp": soil_temp,
                "soil_moisture": soil_moisture,
                "lux": lux
            },
            crop_code=ctrl.active_crop,
            ml_prediction=ml_prediction
        )
        pump_command = smart_result["pump"]
        light_command = smart_result["light"]
        smart_info = smart_result

        # Ở chế độ AUTO: Bắn lệnh ra MQTT nếu có thay đổi hoặc định kỳ đảm bảo ESP32 đồng bộ
        if mqtt_service.is_connected:
            mqtt_service.publish_pump_command(pump_command)
            mqtt_service.publish_light_command(light_command)

    # 4. Kiểm tra cảnh báo Telegram (nếu có cấu hình)
    check_and_send_alerts({
        "air_temp": air_temp,
        "air_hum": air_hum,
        "soil_temp": soil_temp,
        "soil_moisture": soil_moisture,
        "lux": lux
    }, pump_command, light_command)

    # 5. Lưu vào Database có tối ưu tần suất (Chỉ lưu khi đổi trạng thái rơ-le hoặc đủ chu kỳ N giây)
    now_ts = datetime.now(timezone.utc).timestamp()
    state_changed = (pump_command != last_logged_pump_state) or (light_command != last_logged_light_state)
    time_elapsed = (now_ts - last_db_save_time) >= DB_LOG_INTERVAL_SECONDS

    db_saved = False
    if state_changed or time_elapsed:
        try:
            db_log = SensorLogDB(
                timestamp=datetime.now(timezone.utc),
                air_temp=air_temp,
                air_hum=air_hum,
                soil_temp=soil_temp,
                soil_moisture=soil_moisture,
                lux=lux,
                pump_status=pump_command,
                light_status=light_command,
                vpd=vpd_val
            )
            db.add(db_log)
            db.commit()
            last_db_save_time = now_ts
            last_logged_pump_state = pump_command
            last_logged_light_state = light_command
            db_saved = True
        except Exception as e:
            db.rollback()
            print(f"❌ Lỗi ghi Database: {e}")

    # 6. Gửi WebSocket thông báo cập nhật trực tiếp tới Android App ngay lập tức
    crop_info = CROP_PROFILES.get(ctrl.active_crop, CROP_PROFILES["general"])
    payload_to_android = {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": ctrl.mode,
        "active_crop": ctrl.active_crop,
        "crop_name": crop_info["name"],
        "air_temp": air_temp,
        "air_hum": air_hum,
        "soil_temp": soil_temp,
        "soil_moisture": soil_moisture,
        "lux": lux,
        "vpd": vpd_val,
        "pump_status": pump_command,
        "light_status": light_command,
        "manual_pump": ctrl.manual_pump,
        "manual_light": ctrl.manual_light,
        "lux_threshold": ctrl.lux_threshold,
        "smart_info": smart_info
    }
    
    if main_loop and main_loop.is_running():
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(payload_to_android), main_loop)

    return {
        "status": "success",
        "pump": pump_command,
        "light": light_command,
        "mode": ctrl.mode,
        "db_saved": db_saved
    }

# --- 6. GẮN CALLBACK MQTT VÀO PIPELINE ---
def handle_mqtt_sensor(data_dict: dict):
    try:
        db = SessionLocal()
        try:
            process_sensor_pipeline(data_dict, db)
        finally:
            db.close()
    except Exception as e:
        print(f"❌ [MQTT Handler Error]: {e}")

def handle_mqtt_status(status_str: str):
    global main_loop
    if main_loop and main_loop.is_running():
        asyncio.run_coroutine_threadsafe(
            ws_manager.broadcast({
                "event": "ESP32_STATUS",
                "status": status_str,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }),
            main_loop
        )

mqtt_service.on_sensor_callback = handle_mqtt_sensor
mqtt_service.on_status_callback = handle_mqtt_status

# --- 7. ENDPOINTS DÀNH CHO ESP32 VÀ ANDROID ---

# [WEBSOCKET] Android App kết nối để nhận Live Stream thông số không cần Polling HTTP
@app.websocket("/ws/live-data")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Giữ kết nối mở để nhận sự kiện từ app nếu cần
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

# [POST] Vẫn giữ endpoint HTTP cho ESP32 hoặc thiết bị cũ gửi lên
@app.post("/api/sensor-data")
async def receive_sensor_data(
    data: SensorData, 
    db: Session = Depends(get_db),
    x_api_key: Optional[str] = Header(None)
):
    return process_sensor_pipeline(data.model_dump(), db)


# [GET] Android App lấy dữ liệu mới nhất (Khi vừa mở app)
@app.get("/api/latest-status")
def get_latest_status(db: Session = Depends(get_db)):
    latest_log = db.query(SensorLogDB).order_by(desc(SensorLogDB.id)).first()
    ctrl = get_control_state(db)
    
    if not latest_log:
        return {"status": "error", "message": "Chưa có dữ liệu cảm biến"}
        
    crop_info = CROP_PROFILES.get(ctrl.active_crop, CROP_PROFILES["general"])

    # Ở chế độ MANUAL: trạng thái thiết bị phản ánh cấu hình người dùng cài đặt
    current_pump = ctrl.manual_pump if ctrl.mode == "MANUAL" else latest_log.pump_status
    current_light = ctrl.manual_light if ctrl.mode == "MANUAL" else latest_log.light_status

    return {
        "status": "success",
        "timestamp": latest_log.timestamp.isoformat() if latest_log.timestamp else None,
        "mode": ctrl.mode,
        "active_crop": ctrl.active_crop,
        "crop_name": crop_info["name"],
        "air_temp": latest_log.air_temp,
        "air_hum": latest_log.air_hum,
        "soil_temp": latest_log.soil_temp,
        "soil_moisture": latest_log.soil_moisture,
        "lux": latest_log.lux,
        "vpd": latest_log.vpd,
        "pump_status": current_pump,
        "light_status": current_light,
        "manual_pump": ctrl.manual_pump,
        "manual_light": ctrl.manual_light,
        "lux_threshold": ctrl.lux_threshold
    }

# [POST] Android App điều khiển trực tiếp (Bật/Tắt bơm, đèn, đổi mode, đổi cây trồng)
@app.post("/api/control")
async def set_control_mode(config: ControlUpdate, db: Session = Depends(get_db)):
    ctrl = get_control_state(db)
    was_auto = (ctrl.mode == "AUTO")
    ctrl.mode = config.mode
    
    # Khi chuyển từ chế độ AI (AUTO) sang chế độ tay (MANUAL):
    # Đưa các thiết bị chưa chỉ định về OFF và gửi lệnh ngắt ngay xuống ESP32
    if was_auto and ctrl.mode == "MANUAL":
        ctrl.manual_pump = config.manual_pump if config.manual_pump is not None else "OFF"
        ctrl.manual_light = config.manual_light if config.manual_light is not None else "OFF"
    else:
        if config.manual_pump is not None:
            ctrl.manual_pump = config.manual_pump
        if config.manual_light is not None:
            ctrl.manual_light = config.manual_light

    if config.lux_threshold is not None:
        ctrl.lux_threshold = config.lux_threshold
    if config.active_crop is not None and config.active_crop in CROP_PROFILES:
        ctrl.active_crop = config.active_crop
        
    db.commit()
    db.refresh(ctrl)

    # Bắn lệnh trực tiếp qua MQTT tới ESP32 ngay lập tức (Độ trễ < 50ms)
    if ctrl.mode == "MANUAL":
        if was_auto or config.manual_pump is not None:
            mqtt_service.publish_pump_command(ctrl.manual_pump)
        if was_auto or config.manual_light is not None:
            mqtt_service.publish_light_command(ctrl.manual_light)

    # Bắn thông báo cập nhật trạng thái mới sang Android qua WebSocket ngay tức thì
    latest_log = db.query(SensorLogDB).order_by(desc(SensorLogDB.id)).first()
    crop_info = CROP_PROFILES.get(ctrl.active_crop, CROP_PROFILES["general"])
    full_status_payload = {
        "status": "success",
        "timestamp": latest_log.timestamp.isoformat() if (latest_log and latest_log.timestamp) else datetime.now(timezone.utc).isoformat(),
        "mode": ctrl.mode,
        "active_crop": ctrl.active_crop,
        "crop_name": crop_info["name"],
        "air_temp": latest_log.air_temp if latest_log else 25.0,
        "air_hum": latest_log.air_hum if latest_log else 60.0,
        "soil_temp": latest_log.soil_temp if latest_log else 25.0,
        "soil_moisture": latest_log.soil_moisture if latest_log else 50,
        "lux": latest_log.lux if latest_log else 500.0,
        "vpd": latest_log.vpd if latest_log else 1.0,
        "pump_status": ctrl.manual_pump if ctrl.mode == "MANUAL" else (latest_log.pump_status if latest_log else "OFF"),
        "light_status": ctrl.manual_light if ctrl.mode == "MANUAL" else (latest_log.light_status if latest_log else "OFF"),
        "manual_pump": ctrl.manual_pump,
        "manual_light": ctrl.manual_light,
        "lux_threshold": ctrl.lux_threshold
    }
    await ws_manager.broadcast(full_status_payload)

    return {
        "status": "success",
        "message": f"Hệ thống đã chuyển sang chế độ {ctrl.mode}",
        "current_control": {
            "mode": ctrl.mode,
            "manual_pump": ctrl.manual_pump,
            "manual_light": ctrl.manual_light,
            "lux_threshold": ctrl.lux_threshold,
            "active_crop": ctrl.active_crop
        }
    }

# [GET] Danh sách các hồ sơ cây trồng (Để Android hiển thị menu chọn cây)
@app.get("/api/crops")
def get_crop_profiles():
    return {
        "status": "success",
        "crops": [
            {"id": key, **info}
            for key, info in CROP_PROFILES.items()
        ]
    }

# [GET] Lấy lịch sử đo để Android vẽ biểu đồ (Chart)
@app.get("/api/history")
def get_sensor_history(
    limit: int = Query(50, ge=5, le=300), 
    db: Session = Depends(get_db)
):
    logs = db.query(SensorLogDB).order_by(desc(SensorLogDB.id)).limit(limit).all()
    result = []
    for row in reversed(logs):
        result.append({
            "id": row.id,
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
            "air_temp": row.air_temp,
            "air_hum": row.air_hum,
            "soil_temp": row.soil_temp,
            "soil_moisture": row.soil_moisture,
            "lux": row.lux,
            "vpd": row.vpd,
            "pump_status": row.pump_status,
            "light_status": row.light_status
        })
    return {"status": "success", "count": len(result), "data": result}
