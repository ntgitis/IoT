#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <BH1750.h>
#include <math.h>

// =========================================================================
// HỆ THỐNG NÔNG NGHIỆP THÔNG MINH - FIRMWARE ESP32 CHUẨN CÔNG NGHIỆP (SAFE)
// Vi điều khiển: ESP32 WROOM DevKit V1
// Giao thức truyền thông: MQTT (PubSubClient) + LWT (Last Will and Testament)
// Tính năng an toàn: Non-blocking Loop, Khóa cứng Watchdog 60s, Cooldown, Offline Fail-Safe
// =========================================================================

// ----------------------- 1. CẤU HÌNH WIFI & MQTT -----------------------
const char* WIFI_SSID ="iPhoen";
const char* WIFI_PASSWORD = "12345679";
const char* MQTT_HOST = "broker.emqx.io"; // Đổi sang IP Laptop (vd: 192.168.1.202) nếu dùng Mosquitto nội bộ
const uint16_t MQTT_PORT = 1883;
const char* MQTT_USER = "";
const char* MQTT_PASSWORD = "";

// Các MQTT Topics đồng bộ với FastAPI Backend & App Android
const char* TOPIC_SENSORS = "smartfarm/esp32/sensors";
const char* TOPIC_PUMP = "smartfarm/esp32/control/pump";
const char* TOPIC_LIGHT = "smartfarm/esp32/control/light";
const char* TOPIC_STATUS = "smartfarm/esp32/status"; // Trạng thái online/offline (LWT)

// ----------------------- 2. ĐỊNH NGHĨA CHÂN PHẦN CỨNG -------------------
constexpr uint8_t PIN_SOIL = 32;       // Cảm biến độ ẩm đất (ADC1)
constexpr uint8_t PIN_DHT = 18;        // Cảm biến nhiệt ẩm không khí DHT11
constexpr uint8_t PIN_ONEWIRE = 16;    // Cảm biến nhiệt độ đất DS18B20
constexpr uint8_t PIN_PUMP = 26;       // Rơ-le 1: Máy bơm nước (GPIO 26 - Active HIGH)
constexpr uint8_t PIN_LIGHT = 27;      // Rơ-le 2: Quạt / Đèn quang hợp (GPIO 27 - Active HIGH)
constexpr uint8_t PIN_SDA = 21;        // I2C SDA cho BH1750
constexpr uint8_t PIN_SCL = 22;        // I2C SCL cho BH1750

// CÁC CHÂN NÚT BẤM CƠ ĐIỀU KHIỂN TAY TẠI CHỖ (INPUT_PULLUP)
constexpr uint8_t PIN_BTN_PUMP = 5;   // Nút bấm Máy Bơm (nối chân GPIO 5 về GND)
constexpr uint8_t PIN_BTN_LIGHT = 4;   // Nút bấm Quạt / Đèn (nối chân GPIO 4 về GND)

// CẤU HÌNH MỨC KÍCH RƠ-LE:
// Thực tế phần cứng của bạn kích mức HIGH (Active HIGH):
// - Khi xuất HIGH (3.3V): Rơ-le HÚT (BẬT thiết bị)
// - Khi xuất LOW (0V): Rơ-le NHẢ (TẮT thiết bị)
constexpr uint8_t RELAY_ON = HIGH;
constexpr uint8_t RELAY_OFF = LOW;

// ----------------------- 3. THÔNG SỐ HIỆU CHUẨN & AN TOÀN ---------------
constexpr int SOIL_ADC_DRY = 4095;     // Giá trị ADC khi cảm biến khô ngoài không khí
constexpr int SOIL_ADC_WET = 1500;     // Giá trị ADC khi nhúng vào nước

// Kích hoạt hiệu chuẩn và tính năng an toàn tự hành cục bộ
constexpr bool SOIL_CALIBRATED = true;           // Đã hiệu chuẩn cảm biến đất
constexpr bool ENABLE_OFFLINE_AUTO_PUMP = true;  // Tự động bật bơm cứu cây khi mất kết nối mạng
constexpr bool ENABLE_OFFLINE_AUTO_LIGHT = true; // Tự động bật đèn khi mất kết nối mạng và trời tối

constexpr uint8_t SOIL_PUMP_START_PERCENT = 35; // Ngưỡng độ ẩm đất kích hoạt bơm (< 35%)
constexpr uint8_t SOIL_PUMP_STOP_PERCENT = 50;  // Ngưỡng độ ẩm đất ngắt bơm (>= 50%)
constexpr float LIGHT_ON_LUX = 300.0f;          // Ngưỡng bật đèn (< 300 Lux)
constexpr float LIGHT_OFF_LUX = 400.0f;         // Ngưỡng tắt đèn (>= 400 Lux)

constexpr uint32_t SENSOR_INTERVAL_MS = 5000;   // Chu kỳ đo cảm biến: 5 giây
constexpr uint32_t WIFI_RETRY_MS = 10000;       // Thời gian thử lại kết nối WiFi: 10 giây
constexpr uint32_t MQTT_RETRY_MS = 5000;        // Thời gian thử lại MQTT: 5 giây

// Bảo vệ máy bơm đa tầng (Multi-tier Pump Safety)
constexpr uint32_t MAX_PUMP_ON_MS = 60000;      // Tối đa 60 giây chạy liên tục
constexpr uint32_t PUMP_COOLDOWN_MS = 3000;     // Thời gian nghỉ giữa 2 lần bơm: 3 giây (chống rung relay, phản hồi nhanh khi test)
constexpr uint32_t MAX_TOTAL_PUMP_MS = 600000;  // Hạn mức tối đa 10 phút bơm trong 1 giờ (phù hợp demo/báo cáo)
constexpr uint32_t PUMP_WINDOW_MS = 3600000;    // Cửa sổ tính toán giới hạn: 1 giờ

// ----------------------- 4. KHỞI TẠO ĐỐI TƯỢNG PHẦN CỨNG ----------------
DHT dht(PIN_DHT, DHT11);
OneWire oneWire(PIN_ONEWIRE);
DallasTemperature ds18b20(&oneWire);
BH1750 bh1750;
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

bool lightReady = false;
bool pumpOn = false;
bool lightOn = false;
bool pumpTimeoutLock = false; // Cờ khóa cứng nếu bơm chạy quá 60s
bool hadMqttConnection = false;

uint32_t pumpStartMs = 0;
uint32_t pumpLastStopMs = 0;
bool pumpHasStopped = false;
uint32_t pumpWindowStartMs = 0;
uint32_t pumpUsedMs = 0;

uint32_t lastSampleMs = 0;
uint32_t lastWifiAttemptMs = 0;
uint32_t lastMqttAttemptMs = 0;

struct Readings {
  float airTemp = NAN;
  float airHum = NAN;
  float soilTemp = NAN;
  float lux = NAN;
  int soilAdc = -1;
  int soilPercent = -1;
  bool dhtOk = false;
  bool dsOk = false;
  bool bhOk = false;
  bool soilOk = false;
};

// Khai báo trước hàm gửi báo cáo telemetry
void sampleAndReport(const char* source = "periodic");

// ----------------------- 5. HÀM ĐIỀU KHIỂN & BẢO VỆ PHẦN CỨNG ------------
void setLight(bool on, const char* reason) {
  if (lightOn == on) return;
  lightOn = on;
  digitalWrite(PIN_LIGHT, on ? RELAY_ON : RELAY_OFF);
  Serial.printf("💡 [ĐÈN] %s (Lý do: %s)\n", on ? "BẬT" : "TẮT", reason);
}

void updatePumpWindow(uint32_t now) {
  if ((uint32_t)(now - pumpWindowStartMs) >= PUMP_WINDOW_MS) {
    if (!pumpOn) {
      pumpWindowStartMs = now;
      pumpUsedMs = 0;
    }
  }
}

void stopPump(const char* reason) {
  if (!pumpOn) return;
  uint32_t now = millis();
  pumpUsedMs += (uint32_t)(now - pumpStartMs);
  pumpOn = false;
  pumpHasStopped = true;
  pumpLastStopMs = now;
  digitalWrite(PIN_PUMP, RELAY_OFF);
  Serial.printf("💤 [MÁY BƠM] TẮT (Lý do: %s) | Đã chạy tích lũy: %lu ms\n", reason, (unsigned long)pumpUsedMs);
}

bool startPump(const char* reason) {
  if (pumpOn) return true;
  uint32_t now = millis();
  updatePumpWindow(now);

  if (pumpTimeoutLock) {
    Serial.println("⛔ [MÁY BƠM TỪ CHỐI] Bơm đang bị Khóa An Toàn! Cần gửi lệnh OFF để xác nhận mở khóa.");
    return false;
  }
  if (pumpHasStopped && (uint32_t)(now - pumpLastStopMs) < PUMP_COOLDOWN_MS) {
    Serial.println("⏳ [MÁY BƠM TỪ CHỐI] Đang trong thời gian Cooldown nghỉ (bảo vệ động cơ).");
    return false;
  }
  if (pumpUsedMs >= MAX_TOTAL_PUMP_MS) {
    Serial.println("⚠️ [MÁY BƠM TỪ CHỐI] Vượt quá giới hạn tổng thời gian bơm trong 1 giờ (Chống ngập).");
    return false;
  }

  pumpOn = true;
  pumpStartMs = now;
  digitalWrite(PIN_PUMP, RELAY_ON);
  Serial.printf("⚡ [MÁY BƠM] BẬT (Lý do: %s)\n", reason);
  return true;
}

void enforcePumpSafety() {
  uint32_t now = millis();
  updatePumpWindow(now);
  if (!pumpOn) return;
  uint32_t elapsed = (uint32_t)(now - pumpStartMs);

  if (elapsed >= MAX_PUMP_ON_MS || pumpUsedMs + elapsed >= MAX_TOTAL_PUMP_MS) {
    pumpTimeoutLock = true;
    stopPump("VƯỢT NGƯỠNG AN TOÀN 60 GIÂY");
    Serial.println("🚨 [CẢNH BÁO KHẨN CẤP] Máy bơm bị khóa cứng chống cháy và tràn nước! Cần lệnh OFF để mở khóa.");
  }
}

// ----------------------- 6. XỬ LÝ LỆNH MQTT ĐẾN TỨC THÌ -----------------
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  if (length == 0 || length > 3) {
    Serial.println("⚠️ [MQTT] Lệnh điều khiển không đúng định dạng (Quá độ dài)");
    return;
  }
  char cmd[4] = {0};
  memcpy(cmd, payload, length);
  bool on = strcmp(cmd, "ON") == 0;
  bool off = strcmp(cmd, "OFF") == 0;
  if (!on && !off) {
    Serial.printf("⚠️ [MQTT] Lệnh không hợp lệ: %s\n", cmd);
    return;
  }

  if (strcmp(topic, TOPIC_PUMP) == 0) {
    if (off) {
      stopPump("LỆNH MQTT OFF");
      pumpTimeoutLock = false; // Người dùng chủ động gửi OFF -> Mở khóa an toàn
      pumpHasStopped = false;  // Reset cờ cooldown để có thể bật lại ngay
      Serial.println("🔓 [MÁY BƠM] Đã mở khóa an toàn thành công.");
    } else {
      startPump("LỆNH MQTT ON");
    }
  } else if (strcmp(topic, TOPIC_LIGHT) == 0) {
    setLight(on, "LỆNH MQTT");
  }
}

// ----------------------- 7. DUY TRÌ KẾT NỐI MẠNG (NON-BLOCKING) ---------
void maintainNetwork() {
  uint32_t now = millis();
  if (WiFi.status() != WL_CONNECTED) {
    if (hadMqttConnection) {
      hadMqttConnection = false;
      stopPump("Mất kết nối WiFi");
      setLight(false, "Mất kết nối WiFi");
    }
    if ((uint32_t)(now - lastWifiAttemptMs) >= WIFI_RETRY_MS) {
      lastWifiAttemptMs = now;
      Serial.println("📡 [WiFi] Đang thử kết nối lại...");
      WiFi.reconnect();
    }
    return;
  }

  if (mqtt.connected()) {
    mqtt.loop();
    return;
  }

  if (hadMqttConnection) {
    hadMqttConnection = false;
    stopPump("Mất kết nối MQTT");
    setLight(false, "Mất kết nối MQTT");
  }

  if ((uint32_t)(now - lastMqttAttemptMs) < MQTT_RETRY_MS) return;
  lastMqttAttemptMs = now;

  String id = "ESP32_Farm_" + String((uint32_t)ESP.getEfuseMac(), HEX);
  Serial.printf("🔄 [MQTT] Đang kết nối tới %s:%u...\n", MQTT_HOST, MQTT_PORT);
  
  // Đăng ký Last Will and Testament: Gửi "offline" nếu mất nguồn đột ngột
  bool ok = (strlen(MQTT_USER) == 0)
    ? mqtt.connect(id.c_str(), TOPIC_STATUS, 1, true, "offline")
    : mqtt.connect(id.c_str(), MQTT_USER, MQTT_PASSWORD, TOPIC_STATUS, 1, true, "offline");

  if (!ok) {
    Serial.printf("❌ [MQTT] Kết nối thất bại (state=%d)\n", mqtt.state());
    return;
  }

  hadMqttConnection = true;
  mqtt.publish(TOPIC_STATUS, "online", true);
  mqtt.subscribe(TOPIC_PUMP);
  mqtt.subscribe(TOPIC_LIGHT);
  Serial.println("✅ [MQTT] Đã kết nối Broker và đăng ký lắng nghe lệnh!");
}

// ----------------------- 8. ĐỌC CẢM BIẾN & XỬ LÝ LỌC NHIỄU -------------
Readings readSensors() {
  Readings r;
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  r.dhtOk = isfinite(humidity) && isfinite(temperature) &&
            humidity >= 0 && humidity <= 100 && temperature >= -10 && temperature <= 65;
  if (r.dhtOk) { r.airHum = humidity; r.airTemp = temperature; }

  if (ds18b20.getDeviceCount() > 0) {
    ds18b20.requestTemperatures();
    float t = ds18b20.getTempCByIndex(0);
    r.dsOk = isfinite(t) && t != DEVICE_DISCONNECTED_C && t >= -10 && t <= 65;
    if (r.dsOk) r.soilTemp = t;
  }

  if (lightReady) {
    float value = bh1750.readLightLevel();
    r.bhOk = isfinite(value) && value >= 0 && value <= 100000;
    if (r.bhOk) r.lux = value;
  }

  // Lọc lấy mẫu 10 lần liên tục cho độ ẩm đất
  long total = 0;
  int adcMin = 4095, adcMax = 0;
  for (int i = 0; i < 10; ++i) {
    int value = analogRead(PIN_SOIL);
    total += value;
    if (value < adcMin) adcMin = value;
    if (value > adcMax) adcMax = value;
    delay(3);
  }
  r.soilAdc = total / 10;
  r.soilOk = SOIL_CALIBRATED && SOIL_ADC_DRY > SOIL_ADC_WET &&
             r.soilAdc > 15 && r.soilAdc < 4080 && (adcMax - adcMin) < 700;

  if (r.soilOk) {
    r.soilPercent = constrain(map(r.soilAdc, SOIL_ADC_DRY, SOIL_ADC_WET, 0, 100), 0, 100);
  }
  return r;
}

// Chế độ tự hành cục bộ (Offline Fail-Safe khi mất kết nối mạng)
void runOfflineControl(const Readings& r) {
  if (ENABLE_OFFLINE_AUTO_PUMP && r.soilOk) {
    if (r.soilPercent < SOIL_PUMP_START_PERCENT) startPump("Tự hành cục bộ: Đất khô");
    else if (r.soilPercent >= SOIL_PUMP_STOP_PERCENT) stopPump("Tự hành cục bộ: Đất đủ ẩm");
  } else {
    stopPump("Chế độ an toàn mất mạng");
  }

  if (ENABLE_OFFLINE_AUTO_LIGHT && r.bhOk) {
    if (r.lux < LIGHT_ON_LUX) setLight(true, "Tự hành cục bộ: Thiếu sáng");
    else if (r.lux >= LIGHT_OFF_LUX) setLight(false, "Tự hành cục bộ: Đủ sáng");
  } else {
    setLight(false, "Chế độ an toàn mất mạng");
  }
}

// Đóng gói JSON và gửi báo cáo
void sampleAndReport(const char* source) {
  Readings r = readSensors();
  if (!mqtt.connected()) runOfflineControl(r);

  StaticJsonDocument<512> doc;
  doc["source"] = source;
  if (r.dhtOk) {
    doc["air_temp"] = roundf(r.airTemp * 10) / 10;
    doc["air_hum"] = roundf(r.airHum * 10) / 10;
  } else {
    doc["air_temp"] = nullptr;
    doc["air_hum"] = nullptr;
  }

  if (r.dsOk) doc["soil_temp"] = roundf(r.soilTemp * 10) / 10;
  else doc["soil_temp"] = nullptr;

  if (r.soilOk) doc["soil_moisture"] = r.soilPercent;
  else doc["soil_moisture"] = nullptr;

  if (r.bhOk) doc["lux"] = roundf(r.lux * 10) / 10;
  else doc["lux"] = nullptr;

  doc["soil_adc_raw"] = r.soilAdc;

  // Gói tin chẩn đoán sức khỏe phần cứng
  JsonObject status = doc.createNestedObject("sensor_status");
  status["dht11"] = r.dhtOk;
  status["ds18b20"] = r.dsOk;
  status["bh1750"] = r.bhOk;
  status["soil"] = r.soilOk;
  doc["pump_on"] = pumpOn;
  doc["light_on"] = lightOn;
  doc["pump_locked"] = pumpTimeoutLock;
  doc["wifi_connected"] = WiFi.status() == WL_CONNECTED;
  doc["mqtt_connected"] = mqtt.connected();
  doc["uptime_ms"] = millis();

  char buffer[512];
  size_t written = serializeJson(doc, buffer, sizeof(buffer));
  Serial.printf("📊 [TELEMETRY] %s\n", buffer);

  if (written == 0 || written >= sizeof(buffer) - 1) {
    Serial.println("❌ [LỖI] Kích thước bộ đệm JSON quá nhỏ");
    return;
  }

  if (mqtt.connected()) {
    bool sent = mqtt.publish(TOPIC_SENSORS, buffer);
    Serial.printf("📤 [MQTT GỬI] %s\n", sent ? "THÀNH CÔNG" : "THẤT BẠI");
  } else {
    Serial.println("⚠️ [MQTT] Đang Offline - Chạy chế độ ghi nhận cục bộ");
  }
}

// ----------------------- 9. XỬ LÝ NÚT BẤM CƠ / CÔNG TẮC TAY -------------
// CẤU HÌNH LOẠI CÔNG TẮC TAY:
// - true : Dùng CÔNG TẮC GẠT / BẬP BÊNH (Gạt BẬT là chạy, gạt TẮT là ngắt)
// - false: Dùng NÚT NHẤN NHẢ (Bấm 1 cái đảo trạng thái Bật/Tắt)
constexpr bool USE_TOGGLE_SWITCH = true;

int lastBtnPumpState = HIGH;
int stableBtnPumpState = HIGH;
uint32_t lastBtnPumpDebounceMs = 0;

int lastBtnLightState = HIGH;
int stableBtnLightState = HIGH;
uint32_t lastBtnLightDebounceMs = 0;

constexpr uint32_t DEBOUNCE_DELAY_MS = 50; // 50ms chống rung tiếp điểm

void checkManualButtons() {
  uint32_t now = millis();

  // --- 1. XỬ LÝ CÔNG TẮC / NÚT MÁY BƠM (GPIO 5) ---
  int readPump = digitalRead(PIN_BTN_PUMP);
  if (readPump != lastBtnPumpState) {
    lastBtnPumpDebounceMs = now;
    lastBtnPumpState = readPump;
  }

  if ((uint32_t)(now - lastBtnPumpDebounceMs) >= DEBOUNCE_DELAY_MS) {
    if (readPump != stableBtnPumpState) {
      stableBtnPumpState = readPump;

      if (USE_TOGGLE_SWITCH) {
        // Chế độ CÔNG TẮC GẠT (Latching Toggle Switch)
        if (stableBtnPumpState == LOW) {
          // Gạt sang vị trí BẬT (kéo xuống GND)
          Serial.println("👆 [CÔNG TẮC TAY] Gạt BẬT Máy Bơm");
          startPump("Công tắc tay gạt BẬT");
          pumpTimeoutLock = false;
          pumpHasStopped = false;
        } else {
          // Gạt về vị trí TẮT (nhả lên 3.3V)
          Serial.println("👆 [CÔNG TẮC TAY] Gạt TẮT Máy Bơm");
          stopPump("Công tắc tay gạt TẮT");
          pumpTimeoutLock = false;
          pumpHasStopped = false;
        }
      } else {
        // Chế độ NÚT NHẤN NHẢ (Momentary Push Button)
        if (stableBtnPumpState == LOW) { // Chỉ bắt sườn xuống (vừa nhấn)
          Serial.println("👆 [NÚT NHẤN TAY] Nhấn nút Máy Bơm");
          if (pumpOn) {
            stopPump("Nút nhấn tay");
            pumpTimeoutLock = false;
            pumpHasStopped = false;
          } else {
            startPump("Nút nhấn tay");
          }
        }
      }
      sampleAndReport("physical_switch"); // Gửi telemetry để Tablet cập nhật trạng thái ngay lập tức
    }
  }

  // --- 2. XỬ LÝ CÔNG TẮC / NÚT QUẠT & ĐÈN (GPIO 4) ---
  int readLight = digitalRead(PIN_BTN_LIGHT);
  if (readLight != lastBtnLightState) {
    lastBtnLightDebounceMs = now;
    lastBtnLightState = readLight;
  }

  if ((uint32_t)(now - lastBtnLightDebounceMs) >= DEBOUNCE_DELAY_MS) {
    if (readLight != stableBtnLightState) {
      stableBtnLightState = readLight;

      if (USE_TOGGLE_SWITCH) {
        // Chế độ CÔNG TẮC GẠT
        if (stableBtnLightState == LOW) {
          Serial.println("👆 [CÔNG TẮC TAY] Gạt BẬT Quạt / Đèn");
          setLight(true, "Công tắc tay gạt BẬT");
        } else {
          Serial.println("👆 [CÔNG TẮC TAY] Gạt TẮT Quạt / Đèn");
          setLight(false, "Công tắc tay gạt TẮT");
        }
      } else {
        // Chế độ NÚT NHẤN NHẢ
        if (stableBtnLightState == LOW) { // Chỉ bắt sườn xuống (vừa nhấn)
          Serial.println("👆 [NÚT NHẤN TAY] Nhấn nút Quạt / Đèn");
          setLight(!lightOn, "Nút nhấn tay");
        }
      }
      sampleAndReport("physical_switch"); // Gửi telemetry để Tablet cập nhật trạng thái ngay lập tức
    }
  }
}

// ----------------------- 10. SETUP & LOOP CHÍNH -------------------------
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n========================================================");
  Serial.println("   KHỞI ĐỘNG HỆ THỐNG SMART AGRICULTURE (ESP32 SAFE)");
  Serial.println("========================================================");

  // ÉP MỨC NGẮT TRƯỚC KHI THIẾT LẬP OUTPUT ĐỂ CHỐNG GIẬT RƠ-LE
  digitalWrite(PIN_PUMP, RELAY_OFF);
  digitalWrite(PIN_LIGHT, RELAY_OFF);
  pinMode(PIN_PUMP, OUTPUT);
  pinMode(PIN_LIGHT, OUTPUT);
  pinMode(PIN_SOIL, INPUT);
  analogReadResolution(12);

  // KÍCH HOẠT ĐIỆN TRỞ KÉO LÊN NỘI CHO NÚT NHẤN TAY
  pinMode(PIN_BTN_PUMP, INPUT_PULLUP);
  pinMode(PIN_BTN_LIGHT, INPUT_PULLUP);

  // Đọc trạng thái ban đầu để tránh nhảy sai lúc khởi động
  stableBtnPumpState = digitalRead(PIN_BTN_PUMP);
  lastBtnPumpState = stableBtnPumpState;
  stableBtnLightState = digitalRead(PIN_BTN_LIGHT);
  lastBtnLightState = stableBtnLightState;

  dht.begin();
  ds18b20.begin();
  Serial.printf("🌡️ [DS18B20] Số lượng cảm biến nhận diện: %d\n", ds18b20.getDeviceCount());
  
  Wire.begin(PIN_SDA, PIN_SCL);
  lightReady = bh1750.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
  Serial.printf("☀️ [BH1750] Cảm biến ánh sáng: %s\n", lightReady ? "SẴN SÀNG" : "CHƯA KẾT NỐI");

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWifiAttemptMs = millis();
  Serial.printf("📡 [WiFi] Đang kết nối tới: %s (Non-blocking)\n", WIFI_SSID);

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  mqtt.setBufferSize(768); // Mở rộng buffer để chứa trọn vẹn JSON telemetry
  mqtt.setSocketTimeout(2);

  lastMqttAttemptMs = millis() - MQTT_RETRY_MS;
  lastSampleMs = millis() - SENSOR_INTERVAL_MS;
  pumpWindowStartMs = millis();
  Serial.println("✅ [HỆ THỐNG] Khởi tạo hoàn tất. Baud rate: 115200");
}

void loop() {
  checkManualButtons(); // Quét nút bấm tay liên tục (phản hồi tức thì < 1ms)
  enforcePumpSafety();  // Canh chừng an toàn máy bơm
  maintainNetwork();    // Duy trì kết nối mạng non-blocking
  enforcePumpSafety();

  uint32_t now = millis();
  if ((uint32_t)(now - lastSampleMs) >= SENSOR_INTERVAL_MS) {
    lastSampleMs = now;
    sampleAndReport(); // Đo cảm biến và bắn MQTT định kỳ
  }
}

