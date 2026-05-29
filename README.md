# SolidRocketMotor_TMS_DAQ_V2

## Overview
Thrust Measurement System (TMS) Data Acquisition (DAQ) software and firmware architecture for Solid Rocket Motors. This project is designed to acquire high-frequency physical thrust data via load cells and provides real-time monitoring through a graphical interface. It utilizes background threading to prevent data bottlenecks during static fire tests.

## Key Features
* **Independent Sensor Reading (Multi-rate DAQ)**: Implements asynchronous data acquisition using Python `threading`. This allows sensors (Pressure at 500Hz, Thrust driven by hardware ready-state) to be polled independently without blocking the main GUI execution.
* **Enhanced Real-time GUI**: Upgraded graphical user interface built with PyQt6 and PyQtGraph for high responsiveness. Features include real-time plotting of thrust/pressure curves and streamlined controls for test stand operations.
* **Hardware-level Calibration**: Load cell calibration factors are directly applied and managed within the Teensy microcontroller firmware for maximum reliability.
* **Robust Data Logging**: Safely and continuously records static fire test telemetry data to local storage in CSV format.

## System Architecture
### Hardware Requirements
* **Microcontroller**: Teensy 4.1
* **Pressure ADC**: ADS1115
* **Loadcell Amplifier/ADC**: HX711

### Software Stack
* **Language**: Python >= 3.14 / C++ (Firmware)
* **Package Manager**: [uv](https://github.com/astral-sh/uv)
* **Framework/Libraries**: PyQt6, pyqtgraph, pyserial, threading

## Installation & Setup
This project utilizes `uv` and `pyproject.toml` for fast dependency management.

**1. Clone the repository:**
```bash
git clone https://github.com/YangPUN/SolidRocketMotor_TMS_DAQ_V2.git
cd SolidRocketMotor_TMS_DAQ_V2
```

**2. Install uv (if not already installed):**
```bash
# macOS / Linux
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"
```

**3. Sync dependencies and Run:**
```bash
# Automatically creates .venv and installs dependencies from uv.lock
uv sync

# Run the real-time DAQ GUI
uv run tms_daq_realTimePlot.py
```

## Calibration Guide (Load Cell)
Accurate thrust measurement requires load cell calibration before testing. In this project, calibration is handled directly in the C++ firmware.

1. Measure the raw zero-point and the output with a known standard mass.
2. Calculate your calibration factor.
3. Open `src/daq_setting.h` in your firmware source code.
4. Update the `LOAD_CELL_CAL_FACTOR` macro with your calculated value.
5. Rebuild and upload the firmware to the Teensy board using PlatformIO.

## Calibration Guide (Pressure Sensor)
This system utilizes a  $4\text{-}20\text{mA}$ current loop pressure sensor. Calibration is achieved via a hardware shunt resistor and software conversion formulas.

1. **Shunt Resistor Measurement**
   * Use a multimeter to precisely measure the actual resistance of the shunt resistor installed on the circuit.
   * Update the `R_MAGNITUDE` macro in `src/daq_setting.h` with the measured value (e.g., 150.2).

2. **Verify Max Pressure (Span)**
   * The current C++ code is calibrated for a 1000 PSI (approx. 68.9476 Bar) sensor.
   * If using a sensor with a different specification, modify the pressure conversion constant (`68.9476`) in the `get_pressure()` function within `src/data.cpp` to match the maximum pressure (in Bar) of your specific sensor.

3. **Zero-point Offset Adjustment**
   * Run the system at ambient atmospheric pressure and observe the initial pressure reading on the GUI.
   * If the reading is not exactly 0 Bar, modify the return statement in `get_pressure()` (`src/data.cpp`) to subtract this specific offset value.
     
## Maintainer
* **Electronics Team Lead**
