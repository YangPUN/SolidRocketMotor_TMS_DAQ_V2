#ifndef DAQ_SETTING_H
#define DAQ_SETTING_H

#include <Arduino.h>
#include <ADS1X15.h>
#include <HX711.h>

#define SERIAL_BAUDRATE 115200
#define PT_ADC_CH 0
#define HX711_DATA_PIN 6
#define HX711_CLK_PIN 7
#define ADS1115_ADDR 0x48
#define R_MAGNITUDE 153
#define SENSOR_RATE 10
#define LOAD_CELL_CAL_FACTOR 86.39632

void print_value_to_serial(unsigned long time);

extern ADS1115 ADS;
extern HX711 scale;

#endif