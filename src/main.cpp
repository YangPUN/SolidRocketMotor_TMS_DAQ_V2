#include "daq_setting.h"

ADS1115 ADS(ADS1115_ADDR);
HX711 scale;

static unsigned long prev_micros_press = 0;

void setup() {
  Serial.begin(SERIAL_BAUDRATE);

  scale.begin(HX711_DATA_PIN, HX711_CLK_PIN);
  scale.set_scale(LOAD_CELL_CAL_FACTOR);
  
  // Wait for loadcell stabilization
  delay(3000); 
  scale.tare(); 

  Wire.begin();
  ADS.begin();
  ADS.setGain(1);
  ADS.setDataRate(7); 
}

void loop() {
  unsigned long current_micros = micros();
  
  // Pressure loop (500Hz)
  if (current_micros - prev_micros_press >= PRESS_INTERVAL_US) {
    print_pressure(current_micros);
    prev_micros_press = current_micros;
  }

  // Thrust loop (Hardware-driven rate)
  if (scale.is_ready()) {
    // Fetch precise hardware ready time
    unsigned long thrust_micros = micros(); 
    print_thrust(thrust_micros);
  }
}