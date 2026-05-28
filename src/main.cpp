#include "daq_setting.h"

ADS1115 ADS(ADS1115_ADDR);
HX711 scale;

static unsigned long prev_micros_press = 0;

void setup() {
  Serial.begin(SERIAL_BAUDRATE);

  scale.begin(HX711_DATA_PIN, HX711_CLK_PIN);
  scale.set_scale(LOAD_CELL_CAL_FACTOR);
  
  // Wait for stabilization
  delay(3000); 
  scale.tare(); 

  Wire.begin();
  ADS.begin();
  ADS.setGain(1);
  ADS.setDataRate(7); 
}

void loop() {
  unsigned long current_micros = micros();
  unsigned long current_ms = millis();
  
  // Pressure loop
  if (current_micros - prev_micros_press >= PRESS_INTERVAL_US) {
    print_pressure(current_ms);
    prev_micros_press = current_micros;
  }

  // Thrust loop
  if (scale.is_ready()) {
    print_thrust(current_ms);
  }
}