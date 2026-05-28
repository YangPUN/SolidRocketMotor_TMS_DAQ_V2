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

// Check your actual hardware calibration factor
#define LOAD_CELL_CAL_FACTOR 86.39632

// Async interval
#define PRESS_INTERVAL_US 2000 // 500 Hz

// Change arguments to microseconds
void print_pressure(unsigned long time_us);
void print_thrust(unsigned long time_us);
float get_pressure(float voltage);

extern ADS1115 ADS;
extern HX711 scale;

#endif