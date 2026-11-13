/*
 * =====================================================================================
 *  CHƯƠNG TRÌNH KIỂM TRA ĐỘC LẬP: MÁY BƠM, QUẠT VÀ CÔNG TẮC TAY (CHỐNG NHÁY RELAY)
 *  Bo mạch: ESP32 NodeMCU-32S
 * =====================================================================================
 *  Sơ đồ đấu nối nút bấm / công tắc:
 *  - Công tắc Máy Bơm : 1 chân vào GPIO 18, 1 chân vào GND (Không cần trở ngoài)
 *  - Công tắc Quạt/Đèn : 1 chân vào GPIO 4,  1 chân vào GND (Không cần trở ngoài)
 *
 *  Sơ đồ đấu nối Rơ-le (Active HIGH):
 *  - IN1 (Bơm) : GPIO 26
 *  - IN2 (Quạt): GPIO 27
 * =====================================================================================
 */

// ----------------------- ĐỊNH NGHĨA CHÂN RƠ-LE ---------------------------
const uint8_t PIN_PUMP_26 = 26; // IN1: Máy bơm nước
const uint8_t PIN_FAN_27  = 27; // IN2: Quạt tản nhiệt / Đèn

const uint8_t PIN_PUMP_23 = 23; // Dự phòng
const uint8_t PIN_FAN_19  = 19; // Dự phòng

// ----------------------- ĐỊNH NGHĨA CHÂN CÔNG TẮC ------------------------
const uint8_t PIN_BTN_PUMP = 18; // Công tắc cơ máy bơm (kéo về GND)
const uint8_t PIN_BTN_FAN  = 4;  // Công tắc cơ quạt (kéo về GND)

// CẤU HÌNH LOẠI CÔNG TẮC:
// - true : Dùng CÔNG TẮC GẠT / BẬP BÊNH (Gạt BẬT là chạy, gạt TẮT là dừng)
// - false: Dùng NÚT NHẤN NHẢ (Bấm 1 cái nhả tay ra là đảo Bật/Tắt)
const bool USE_TOGGLE_SWITCH = true;

// ----------------------- CẤU HÌNH MỨC KÍCH RƠ-LE -------------------------
const uint8_t RELAY_ON  = HIGH; // 3.3V -> Rơ-le Hút -> BẬT
const uint8_t RELAY_OFF = LOW;  // 0V   -> Rơ-le Nhả -> TẮT

// Biến lưu trạng thái thiết bị
bool state26 = false;
bool state27 = false;
bool state23 = false;
bool state19 = false;

// Biến bắt sườn (Edge Detection) chống nháy relay liên tục
int lastBtnPumpState = HIGH;
int stableBtnPumpState = HIGH;
unsigned long lastBtnPumpDebounceMs = 0;

int lastBtnFanState = HIGH;
int stableBtnFanState = HIGH;
unsigned long lastBtnFanDebounceMs = 0;

const unsigned long DEBOUNCE_DELAY_MS = 50;

bool autoMode = false;
unsigned long lastToggleTime = 0;
const unsigned long AUTO_INTERVAL = 2500;

void printHelp() {
  Serial.println("\n===========================================================");
  Serial.println("  MENU TEST RELAY & CÔNG TẮC TAY (ĐÃ FIX CHỐNG NHÁY):");
  Serial.println("  👉 [CÔNG TẮC GẠT]: Gạt BẬT chân GPIO 18 -> BƠM BẬT (Không bị nhấp nháy)");
  Serial.println("  👉 [CÔNG TẮC GẠT]: Gạt TẮT chân GPIO 18 -> BƠM TẮT");
  Serial.println("  👉 [CÔNG TẮC GẠT]: Gạt BẬT chân GPIO 4  -> QUẠT BẬT");
  Serial.println("  👉 [CÔNG TẮC GẠT]: Gạt TẮT chân GPIO 4  -> QUẠT TẮT");
  Serial.println("  ---------------------------------------------------------");
  Serial.println("  [ 1 ] -> Bật/Tắt BƠM  (GPIO 26) qua bàn phím");
  Serial.println("  [ 2 ] -> Bật/Tắt QUẠT (GPIO 27) qua bàn phím");
  Serial.println("  [ A ] -> Chế độ Tự Động bật tắt thử nghiệm");
  Serial.println("  [ S ] -> DỪNG & TẮT TẤT CẢ");
  Serial.println("  [ ? ] -> Xem lại menu này");
  Serial.println("===========================================================\n");
}

void setPinDirect(uint8_t pin, bool targetOn, const char* label) {
  digitalWrite(pin, targetOn ? RELAY_ON : RELAY_OFF);
  Serial.printf(">> [%s - GPIO %d]: ", label, pin);
  if (targetOn) {
    Serial.println("🟢 BẬT (Xuất mức HIGH - Rơ-le HÚT & Thiết bị BẬT)");
  } else {
    Serial.println("🔴 TẮT (Xuất mức LOW  - Rơ-le NHẢ & Thiết bị TẮT)");
  }
}

void togglePin(uint8_t pin, bool &stateVar, const char* label) {
  stateVar = !stateVar;
  setPinDirect(pin, stateVar, label);
}

void allOff() {
  state26 = false;
  state27 = false;
  state23 = false;
  state19 = false;

  digitalWrite(PIN_PUMP_26, RELAY_OFF);
  digitalWrite(PIN_FAN_27,  RELAY_OFF);
  digitalWrite(PIN_PUMP_23, RELAY_OFF);
  digitalWrite(PIN_FAN_19,  RELAY_OFF);

  Serial.println("🛑 [TẮT HẾT]: Tất cả thiết bị đã được ngắt.");
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n***********************************************************");
  Serial.println("   CHUONG TRINH TEST: CONG TAC TAY CHONG NHAY RELAY");
  Serial.println("***********************************************************");

  // Đặt mức OFF trước khi bật OUTPUT để chống giật rơ-le
  digitalWrite(PIN_PUMP_26, RELAY_OFF);
  digitalWrite(PIN_FAN_27,  RELAY_OFF);
  digitalWrite(PIN_PUMP_23, RELAY_OFF);
  digitalWrite(PIN_FAN_19,  RELAY_OFF);

  pinMode(PIN_PUMP_26, OUTPUT);
  pinMode(PIN_FAN_27,  OUTPUT);
  pinMode(PIN_PUMP_23, OUTPUT);
  pinMode(PIN_FAN_19,  OUTPUT);

  // Kích hoạt điện trở kéo lên nội cho các công tắc tay
  pinMode(PIN_BTN_PUMP, INPUT_PULLUP);
  pinMode(PIN_BTN_FAN,  INPUT_PULLUP);

  // Đọc trạng thái ban đầu của công tắc
  stableBtnPumpState = digitalRead(PIN_BTN_PUMP);
  lastBtnPumpState = stableBtnPumpState;
  stableBtnFanState = digitalRead(PIN_BTN_FAN);
  lastBtnFanState = stableBtnFanState;

  Serial.println("✅ Đã thiết lập OUTPUT cho Rơ-le (GPIO 26, 27).");
  Serial.println("✅ Đã bật Edge-Detection chống nhảy liên tục khi giữ công tắc.");
  printHelp();
}

void loop() {
  unsigned long now = millis();

  // 1. Quét Công tắc Máy Bơm (GPIO 18) - Chỉ kích hoạt khi có thay đổi trạng thái
  int readPump = digitalRead(PIN_BTN_PUMP);
  if (readPump != lastBtnPumpState) {
    lastBtnPumpDebounceMs = now;
    lastBtnPumpState = readPump;
  }

  if (now - lastBtnPumpDebounceMs >= DEBOUNCE_DELAY_MS) {
    if (readPump != stableBtnPumpState) {
      stableBtnPumpState = readPump;
      autoMode = false;

      if (USE_TOGGLE_SWITCH) {
        if (stableBtnPumpState == LOW) {
          state26 = true;
          Serial.print("👆 [CÔNG TẮC GPIO 18 GẠT BẬT] -> ");
          setPinDirect(PIN_PUMP_26, true, "MÁY BƠM");
        } else {
          state26 = false;
          Serial.print("👆 [CÔNG TẮC GPIO 18 GẠT TẮT] -> ");
          setPinDirect(PIN_PUMP_26, false, "MÁY BƠM");
        }
      } else {
        if (stableBtnPumpState == LOW) {
          Serial.print("👆 [NÚT BẤM GPIO 18 ĐÃ NHẤN] -> ");
          togglePin(PIN_PUMP_26, state26, "MÁY BƠM");
        }
      }
    }
  }

  // 2. Quét Công tắc Quạt / Đèn (GPIO 4)
  int readFan = digitalRead(PIN_BTN_FAN);
  if (readFan != lastBtnFanState) {
    lastBtnFanDebounceMs = now;
    lastBtnFanState = readFan;
  }

  if (now - lastBtnFanDebounceMs >= DEBOUNCE_DELAY_MS) {
    if (readFan != stableBtnFanState) {
      stableBtnFanState = readFan;
      autoMode = false;

      if (USE_TOGGLE_SWITCH) {
        if (stableBtnFanState == LOW) {
          state27 = true;
          Serial.print("👆 [CÔNG TẮC GPIO 4 GẠT BẬT] -> ");
          setPinDirect(PIN_FAN_27, true, "QUẠT / ĐÈN");
        } else {
          state27 = false;
          Serial.print("👆 [CÔNG TẮC GPIO 4 GẠT TẮT] -> ");
          setPinDirect(PIN_FAN_27, false, "QUẠT / ĐÈN");
        }
      } else {
        if (stableBtnFanState == LOW) {
          Serial.print("👆 [NÚT BẤM GPIO 4 ĐÃ NHẤN] -> ");
          togglePin(PIN_FAN_27, state27, "QUẠT / ĐÈN");
        }
      }
    }
  }

  // 3. Nhận lệnh từ Serial Monitor
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\r' || c == '\n' || c == ' ') return;

    if (c == '1') {
      autoMode = false;
      togglePin(PIN_PUMP_26, state26, "MÁY BƠM");
    } 
    else if (c == '2') {
      autoMode = false;
      togglePin(PIN_FAN_27, state27, "QUẠT / ĐÈN");
    } 
    else if (c == 'a' || c == 'A') {
      autoMode = true;
      lastToggleTime = millis();
      Serial.println("\n⚡ [TỰ ĐỘNG]: BẮT ĐẦU test tự động đảo bật/tắt chân 26 & 27...");
    } 
    else if (c == 's' || c == 'S') {
      autoMode = false;
      allOff();
    } 
    else if (c == '?') {
      printHelp();
    }
  }

  // 4. Tự động bật tắt luân phiên nếu bật autoMode
  if (autoMode) {
    if (now - lastToggleTime >= AUTO_INTERVAL) {
      lastToggleTime = now;
      if (!state26 && !state27) {
        state26 = true;
        setPinDirect(PIN_PUMP_26, true, "MÁY BƠM");
      } else if (state26 && !state27) {
        state27 = true;
        setPinDirect(PIN_FAN_27, true, "QUẠT / ĐÈN");
      } else {
        allOff();
      }
    }
  }
}
