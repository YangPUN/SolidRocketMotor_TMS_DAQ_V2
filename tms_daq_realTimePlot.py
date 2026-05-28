import numpy as np
import serial
import pyqtgraph as pg
from pyqtgraph.Qt.QtCore import QTimer, pyqtSignal, pyqtSlot, QObject
from pyqtgraph.Qt.QtWidgets import QLineEdit, QWidget, QVBoxLayout, QGraphicsProxyWidget
from typing import List, Optional, Tuple
from datetime import datetime
import csv
import os
import threading
import struct
import time


class RealTimePlot(QObject):
    """
    A class used to plot real-time data from a serial port using PyQtGraph.

    Attributes
    ----------
    _num_of_data : int
        The number of data series to plot.
    _max_size : int
        The maximum number of data points to display on the plot.
    _app : QApplication
        The PyQtGraph application.
    _ser : Serial
        The serial port.
    _win : GraphicsLayoutWidget
        The PyQtGraph window.
    _plots : list
        The list of PlotItem objects.
    _curves : list
        The list of PlotDataItem objects.
    _datas_x : list
        The list of x data arrays.
    _datas_y : list
        The list of y data arrays.
    _update_rate : int
        The rate at which the plot updates, in milliseconds.
    _time : int
        The current time, in milliseconds.
    _timer : QTimer
        The timer that triggers the plot updates.
    _file_path : str
        The file path where the data is stored. Only created when _write_to_file is True.
    _write_to_file : bool
        Whether to create the file or not.
    """

    data_sent = pyqtSignal(tuple)

    def __init__(
        self,
        data_set: List[str],
        port: str,
        update_rate=50,
        sensor_rate=50,
        baud_rate=115200,
        window_title="Real-time Plotting",
        file_name=None,
        file_directory_name="csv_files",
        max_size=250,
        write_to_file=True,
    ):
        """
        Initializes the RealTimePlot object.
        """
        QObject.__init__(self)
        self.data_sent.connect(self.__update)

        # Set the update rate and initialize the current time
        self._update_rate = update_rate
        self._sensor_rate = sensor_rate
        self._time = 0
        self._time_from_serial = False

        # If time data comes from the serial port
        if data_set[0] == "time":
            self._time_from_serial = True
            data_set = data_set[1:]

        # Set the number of data series and the maximum number of data points
        self._num_of_data = len(data_set)
        self._max_size = max_size

        # Create the PyQtGraph application
        self._app = pg.mkQApp()

        # Open the serial port
        self._ser = serial.Serial(port, baud_rate)
        
        # 14 bytes packet for Teensy 4.1 without MAX6675
        self._data_packet = bytearray(14)

        # Create the PyQtGraph window
        self._win = pg.GraphicsLayoutWidget(show=True)
        self._win.resize(1200, 600)
        self._win.setWindowTitle(window_title)

        self._widget = QWidget()
        self._layout = QVBoxLayout()
        self._widget.setLayout(self._layout)

        # Enable antialiasing for smoother plot lines
        pg.setConfigOptions(antialias=True)

        # Create the plots
        self._plots = []
        for i, data in enumerate(data_set):
            self._plots.append(self._win.addPlot(title=data))
            if (i + 1) % 3 == 0:
                self._win.nextRow()

        # Create the curves
        self._curves = [plot.plot(pen="y") for plot in self._plots]

        # Initialize the data arrays
        self._datas_x = [np.array([])] * self._num_of_data
        self._datas_y = [np.array([])] * self._num_of_data

        # Create the timer
        self._timer = QTimer()

        # Set the option parameter
        self._write_to_file = write_to_file

        # Initialize the csv file if write_to_file is True.
        if self._write_to_file:
            # Create the directory where the data results are written
            os.makedirs(file_directory_name, exist_ok=True)

            # Set the default file name if file name is None
            if file_name is None:
                file_name = datetime.now().strftime("data_%Y-%m-%d,%H-%M-%S.csv")

            # Open the file
            self._file_path = os.path.join(file_directory_name, file_name)
            with open(self._file_path, "w", newline="") as file:
                csv.writer(file).writerow(["time"] + data_set)

    @pyqtSlot(tuple)
    def __update(self, data: Tuple[Optional[int], list[float]]) -> None:
        """
        Updates the plot with new data from the serial port.
        """
        current_time, values = data

        if values:
            # Append each value to the corresponding y data array
            self._datas_y = [
                np.append(data_y, value) for data_y, value in zip(self._datas_y, values)
            ]
            # Append the current time to each x data array
            self._datas_x = [
                np.append(data_x, current_time / 1000) for data_x in self._datas_x
            ]

            # If the length of a data array exceeds max_size, remove the oldest data point
            if len(self._datas_y[0]) > self._max_size:
                self._datas_y = [data_y[1:] for data_y in self._datas_y]
                self._datas_x = [data_x[1:] for data_x in self._datas_x]

            # Update the data for each curve with the new x and y data arrays
            for curve, data_x, data_y in zip(
                self._curves, self._datas_x, self._datas_y
            ):
                curve.setData(data_x, data_y)

    @pyqtSlot()
    def __get_data(self, sep=",") -> None:
        """
        Get the decoded data from the serial port.
        """
        count = 0
        while True:
            try:
                # Wait until full packet (14 bytes) is received
                if self._ser.in_waiting >= 14:
                    count += 1
                    self._ser.readinto(self._data_packet)
                    
                    timeStamp = struct.unpack('I', self._data_packet[0:4])[0] # unit: ms
                    pressBar = struct.unpack('f', self._data_packet[4:8])[0] # unit: bar
                    thrust_gram = struct.unpack('f', self._data_packet[8:12])[0] # unit: gram
                    thrust_Newton = thrust_gram * 0.001 * 9.81
                    pressRaw = struct.unpack('h', self._data_packet[12:14])[0] # raw voltage readings of pressure

                    raw_data = [timeStamp, pressBar, pressRaw, thrust_Newton]
                    
                    if self._time_from_serial:
                        data = raw_data[0], raw_data[1:]
                    else:
                        self._time += self._update_rate
                        data = self._time, raw_data

                    # Write value to CSV file.
                    if self._write_to_file:
                        self.__write_to_csv(raw_data)

                    if count >= self._update_rate // self._sensor_rate:
                        self.data_sent.emit(data)
                        count = 0
                else:
                    # Prevent high CPU usage by yielding
                    time.sleep(0.001)
                    
            except Exception as e:
                print(f"Serial Error: {e}")
                time.sleep(1)

    def run(self) -> None:
        """
        Display the plot to the pyqtgraph window.
        """
        # Connect the timer to the update method
        threading.Thread(target=self.__get_data, daemon=True).start()
        # execute the pyqtgraph
        pg.exec()

    def __write_to_csv(self, row: List[float]) -> None:
        """
        Write a row of data to a CSV file.
        """
        with open(self._file_path, "a", newline="") as file:
            csv.writer(file).writerow(row)


if __name__ == "__main__":
    datas = [
        "time",
        "chamber_press",
        "chamber_press_adc_raw",
        "thrust"
    ] 
    
    # Change port accordingly
    plotter = RealTimePlot(data_set=datas, port="/dev/cu.usbmodem178000601", update_rate=25, sensor_rate=10)
    plotter.run()