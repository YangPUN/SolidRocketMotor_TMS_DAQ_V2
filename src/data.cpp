#include "daq_setting.h"

static float thrust_gram = 0.0;

float get_pressure(float voltage) {
  float current = voltage / R_MAGNITUDE * 1000.0;
  return ((current - 4.0) * 68.9476 / 16.0);
}

void print_value_to_serial(unsigned long time) {
  int16_t press_adc_raw_volt = ADS.readADC(PT_ADC_CH);
  float press_bar = get_pressure(ADS.toVoltage(press_adc_raw_volt));

  // Non-blocking HX711 read
  if (scale.is_ready()) {
    thrust_gram = scale.get_units();
  }

  // Payload: time(4) + press_bar(4) + thrust_gram(4) + press_adc_raw(2) = 14 bytes
  byte buf[14] = {0};
  memcpy(buf, &time, 4);
  memcpy(buf + 4, &press_bar, 4);
  memcpy(buf + 8, &thrust_gram, 4);
  memcpy(buf + 12, &press_adc_raw_volt, 2);
  
  Serial.write(buf, 14);
}