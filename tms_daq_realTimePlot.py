import os
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt6"

import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QFrame, QPushButton, QLineEdit)
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QObject, Qt, QTimer
from datetime import datetime
import csv
import threading
import struct
import time
import serial


class SerialReader(QObject):
    pressure_sent = pyqtSignal(tuple)
    thrust_sent = pyqtSignal(tuple)

    def __init__(self, port, baud_rate):
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self.is_recording = False
        self.file_path = ""
        self._ser = None

        if self.port:
            try:
                self._ser = serial.Serial(self.port, self.baud_rate, timeout=0.1)
                print(f"Connected to {self.port}")
            except Exception as e:
                print(f"Hardware not connected or port error: {e}")
                self._ser = None

    def start_recording(self, file_path):
        self.file_path = file_path
        with open(self.file_path, "w", newline="") as f:
            csv.writer(f).writerow(["Timestamp_us", "Packet_Type", "Chamber_Press_Bar", "Press_ADC_Raw", "Thrust_N", "Thrust_Gram"])
        self.is_recording = True

    def stop_recording(self):
        self.is_recording = False

    def start_reading(self):
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self):
        buffer = b''
        count_p = 0
        count_t = 0
        
        while True:
            try:
                if self._ser and self._ser.is_open and self._ser.in_waiting > 0:
                    buffer += self._ser.read(self._ser.in_waiting)
                    
                    while len(buffer) >= 3:
                        sync_idx = buffer.find(b'\xaa\x55')
                        if sync_idx == -1:
                            buffer = b''
                            break
                        if sync_idx > 0:
                            buffer = buffer[sync_idx:]
                            if len(buffer) < 3:
                                break
                        
                        packet_type = buffer[2]
                        
                        if packet_type == 0x01: 
                            if len(buffer) < 13:
                                break
                            packet = buffer[:13]
                            buffer = buffer[13:]
                            
                            ts_us = struct.unpack('<I', packet[3:7])[0]
                            p_bar = struct.unpack('<f', packet[7:11])[0]
                            p_raw = struct.unpack('<h', packet[11:13])[0]
                            
                            if self.is_recording:
                                self._write_csv(ts_us, 1, p_bar, p_raw, "", "")
                                
                            count_p += 1
                            if count_p >= 5: 
                                self.pressure_sent.emit((ts_us / 1000000.0, p_bar, p_raw))
                                count_p = 0
                                
                        elif packet_type == 0x02: 
                            if len(buffer) < 11:
                                break
                            packet = buffer[:11]
                            buffer = buffer[11:]
                            
                            ts_us = struct.unpack('<I', packet[3:7])[0]
                            t_gram = struct.unpack('<f', packet[7:11])[0]
                            t_newton = t_gram * 0.001 * 9.81
                            
                            if self.is_recording:
                                self._write_csv(ts_us, 2, "", "", t_newton, t_gram)
                                
                            count_t += 1
                            if count_t >= 1: 
                                self.thrust_sent.emit((ts_us / 1000000.0, t_newton, t_gram))
                                count_t = 0
                        else:
                            buffer = buffer[2:]
                else:
                    time.sleep(0.01)
                    
            except Exception as e:
                print(f"Read Loop Error: {e}")
                time.sleep(1)

    def _write_csv(self, ts, p_type, bar, raw, thrust, t_gram):
        with open(self.file_path, "a", newline="") as f:
            csv.writer(f).writerow([ts, p_type, bar, raw, thrust, t_gram])


class DaqDashboard(QMainWindow):
    def __init__(self, port=None, max_size=600):
        super().__init__()
        self.max_size = max_size
        self.is_running = False

        self.setWindowTitle("Solid Rocket Motor DAQ")
        self.resize(1400, 850)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")
        
        pg.setConfigOptions(antialias=True)
        pg.setConfigOption('background', '#1e1e2e')
        pg.setConfigOption('foreground', '#cdd6f4')
        
        self._init_ui()
        self._init_data_arrays()
        
        os.makedirs("csv_files", exist_ok=True)
        
        self.reader = SerialReader(port=port, baud_rate=115200)
        self.reader.pressure_sent.connect(self.update_pressure)
        self.reader.thrust_sent.connect(self.update_thrust)
        self.reader.start_reading()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        left_panel = QFrame()
        left_panel.setFixedWidth(320)
        left_panel.setStyleSheet("background-color: #181825; border-radius: 10px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        title_label = QLabel("THRUST TMS DAQ V2")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #89b4fa;")
        left_layout.addWidget(title_label)
        
        self.time_label = QLabel("0000-00-00 00:00:00")
        self.time_label.setStyleSheet("font-size: 14px; color: #a6adc8; margin-bottom: 10px;")
        left_layout.addWidget(self.time_label)
        
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()
        
        control_frame = QFrame()
        control_frame.setStyleSheet("background-color: #313244; border-radius: 8px; padding: 10px;")
        control_layout = QVBoxLayout(control_frame)
        
        # Custom filename input field
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("파일 이름 입력 (예: test_01)")
        self.filename_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e; 
                color: #cdd6f4; 
                font-size: 13px; 
                padding: 8px; 
                border: 1px solid #45475a; 
                border-radius: 4px;
                margin-bottom: 10px;
            }
        """)
        control_layout.addWidget(self.filename_input)

        self.btn_toggle = QPushButton("측정 시작 (START)")
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1; 
                color: #11111b; 
                font-size: 16px; 
                font-weight: bold; 
                padding: 15px; 
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #94e2d5; }
        """)
        self.btn_toggle.clicked.connect(self.toggle_measurement)
        control_layout.addWidget(self.btn_toggle)
        
        self.status_label = QLabel("상태: 대기 중 (Idle)")
        self.status_label.setStyleSheet("font-size: 12px; color: #bac2de; margin-top: 5px;")
        control_layout.addWidget(self.status_label)
        
        self.filename_label = QLabel("파일: 대기 중")
        self.filename_label.setWordWrap(True)
        self.filename_label.setStyleSheet("font-size: 11px; color: #a6adc8;")
        control_layout.addWidget(self.filename_label)
        
        left_layout.addWidget(control_frame)
        left_layout.addSpacing(20)
        
        self.press_label = self._create_indicator(left_layout, "Chamber Press [Bar]", "#89b4fa")
        self.press_raw_label = self._create_indicator(left_layout, "Press Raw [ADC]", "#b4befe")
        self.thrust_label = self._create_indicator(left_layout, "Thrust [N]", "#f38ba8")
        self.thrust_raw_label = self._create_indicator(left_layout, "Thrust Raw [g]", "#f5c2e7")

        self.plot_widget = pg.GraphicsLayoutWidget()
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.plot_widget)

        self.p_press = self.plot_widget.addPlot(title="Chamber Pressure (Bar, 500 Hz)")
        self.p_press.showGrid(x=True, y=True, alpha=0.3)
        self.curve_press = self.p_press.plot(pen=pg.mkPen('#89b4fa', width=2))
        
        self.plot_widget.nextRow()
        
        self.p_thrust = self.plot_widget.addPlot(title="Loadcell Thrust (N, 80 Hz)")
        self.p_thrust.showGrid(x=True, y=True, alpha=0.3)
        self.curve_thrust = self.p_thrust.plot(pen=pg.mkPen('#f38ba8', width=2))

    def _create_indicator(self, layout, title, color):
        lbl = QLabel(title)
        lbl.setStyleSheet("font-size: 13px; color: #a6adc8; margin-top: 15px;")
        val = QLabel("0.00")
        val.setStyleSheet(f"font-size: 30px; font-weight: bold; color: {color}; margin-bottom: 5px;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(lbl)
        layout.addWidget(val)
        return val

    def _init_data_arrays(self):
        self.p_time, self.p_data = np.array([]), np.array([])
        self.t_time, self.t_data = np.array([]), np.array([])

    @pyqtSlot()
    def update_clock(self):
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.setText(current_time_str)

    @pyqtSlot()
    def toggle_measurement(self):
        if not self.is_running:
            self.is_running = True
            self._init_data_arrays()
            
            # Determine filename
            custom_name = self.filename_input.text().strip()
            if custom_name:
                if not custom_name.endswith('.csv'):
                    custom_name += '.csv'
                filename = custom_name
            else:
                filename = datetime.now().strftime("async_daq_%Y-%m-%d_%H-%M-%S.csv")
                
            filepath = os.path.join("csv_files", filename)
            self.reader.start_recording(filepath)
            
            # Update UI for recording state
            self.filename_input.setEnabled(False) # Lock input field
            self.filename_label.setText(f"파일: {filename}")
            self.status_label.setText("상태: 데이터 기록 중 (Recording)")
            self.btn_toggle.setText("측정 중지 (STOP)")
            self.btn_toggle.setStyleSheet("""
                QPushButton { background-color: #f38ba8; color: #11111b; font-size: 16px; font-weight: bold; padding: 15px; border-radius: 5px;}
                QPushButton:hover { background-color: #f5c2e7; }
            """)
        else:
            self.is_running = False
            self.reader.stop_recording()
            
            # Update UI for idle state
            self.filename_input.setEnabled(True) # Unlock input field
            self.status_label.setText("상태: 대기 중 (Idle)")
            self.btn_toggle.setText("측정 시작 (START)")
            self.btn_toggle.setStyleSheet("""
                QPushButton { background-color: #a6e3a1; color: #11111b; font-size: 16px; font-weight: bold; padding: 15px; border-radius: 5px;}
                QPushButton:hover { background-color: #94e2d5; }
            """)

    @pyqtSlot(tuple)
    def update_pressure(self, data):
        ts, bar, raw = data
        self.p_time = np.append(self.p_time, ts)
        self.p_data = np.append(self.p_data, bar)
        
        if len(self.p_data) > self.max_size:
            self.p_time = self.p_time[1:]
            self.p_data = self.p_data[1:]
            
        self.curve_press.setData(self.p_time, self.p_data)
        self.press_label.setText(f"{bar:.2f}")
        self.press_raw_label.setText(f"{int(raw)}")

    @pyqtSlot(tuple)
    def update_thrust(self, data):
        ts, thrust_n, thrust_g = data
        self.t_time = np.append(self.t_time, ts)
        self.t_data = np.append(self.t_data, thrust_n)
        
        if len(self.t_data) > (self.max_size // 6): 
            self.t_time = self.t_time[1:]
            self.t_data = self.t_data[1:]
            
        self.curve_thrust.setData(self.t_time, self.t_data)
        self.thrust_label.setText(f"{thrust_n:.2f}")
        self.thrust_raw_label.setText(f"{thrust_g:.1f}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DaqDashboard(port=None) 
    window.show()
    sys.exit(app.exec())