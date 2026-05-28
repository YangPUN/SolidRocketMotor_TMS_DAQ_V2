#include "daq_setting.h"

ADS1115 ADS(ADS1115_ADDR);
HX711 scale;

static unsigned long last_print_time = 0;

void setup() {
  Serial.begin(SERIAL_BAUDRATE);

  scale.begin(HX711_DATA_PIN, HX711_CLK_PIN);
  scale.set_scale(LOAD_CELL_CAL_FACTOR);
  
  // Wait for sensors to stabilize FIRST
  delay(3000); 
  
  // Tare AFTER stabilization
  scale.tare(); 

  Wire.begin();
  ADS.begin();
  ADS.setGain(1);
  ADS.setDataRate(7);
  ADS.readADC(0);
}

void loop() {
  unsigned long current_time = millis();
  
  if (current_time - last_print_time >= SENSOR_RATE) {
    print_value_to_serial(current_time);
    last_print_time = current_time;
  }
}