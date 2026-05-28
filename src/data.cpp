#include "daq_setting.h"

float get_pressure(float voltage) {
  float current = voltage / R_MAGNITUDE * 1000.0;
  return ((current - 4.0) * 68.9476 / 16.0);
}

void print_pressure(unsigned long time_ms) {
  int16_t press_adc_raw_volt = ADS.readADC(PT_ADC_CH);
  float press_bar = get_pressure(ADS.toVoltage(press_adc_raw_volt));

  // Packet ID 1: Header(2) + ID(1) + Time(4) + PressBar(4) + PressRaw(2) = 13 bytes
  byte buf[13];
  buf[0] = 0xAA;
  buf[1] = 0x55;
  buf[2] = 0x01; 
  memcpy(buf + 3, &time_ms, 4);
  memcpy(buf + 7, &press_bar, 4);
  memcpy(buf + 11, &press_adc_raw_volt, 2);

  Serial.write(buf, 13);
}

void print_thrust(unsigned long time_ms) {
  float thrust_gram = scale.get_units();

  // Packet ID 2: Header(2) + ID(1) + Time(4) + ThrustGram(4) = 11 bytes
  byte buf[11];
  buf[0] = 0xAA;
  buf[1] = 0x55;
  buf[2] = 0x02; 
  memcpy(buf + 3, &time_ms, 4);
  memcpy(buf + 7, &thrust_gram, 4);

  Serial.write(buf, 11);
}