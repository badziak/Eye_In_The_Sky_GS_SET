import sys
import random
import re
import folium
import serial
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from folium.plugins import MarkerCluster
from colour import Color


def LoRa(COM_PORT):
    try:
        ser = serial.Serial(COM_PORT, 9600)
        data = ser.readline().decode('latin1').strip()
        labels_list = data.split(', ')
        if len(labels_list) > 13:
            label_to_index = {label.split()[0]: idx for idx, label in enumerate(labels_list)}
            pattern = re.compile(r'\d+(\.\d+)?')
            filtered_data = [float(pattern.search(item).group()) for item in labels_list if pattern.search(item)]
            return filtered_data
        else:
            return [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0]
    except serial.SerialException:
        print(f"Could not open serial port {COM_PORT}")
        return [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0]


class RealTimeMap(QWidget):
    def __init__(self):
        super().__init__()

        self.zoom_level = 5
        self.map_object = folium.Map(location=[0, 0], zoom_start=self.zoom_level)
        self.marker_cluster = MarkerCluster().add_to(self.map_object)
        self.coordinates_history = []
        self.is_auto_refresh = True

        self.init_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(1000)  # Update every 1 second

    def init_ui(self):
        self.webview = QWebEngineView()
        self.webview.setHtml(self.map_object._repr_html_())

        self.com_port_combobox = QComboBox()
        for i in range(1, 13):
            self.com_port_combobox.addItem(f"COM{i}")

        self.com_port_combobox.currentIndexChanged.connect(self.connect_to_com_port)
        self.com_port_combobox.setFixedSize(300, 20)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.com_port_combobox)

        layout = QVBoxLayout()
        layout.addLayout(buttons_layout)
        layout.addWidget(self.webview)

        self.setLayout(layout)

    def connect_to_com_port(self, index):
        selected_com_port = self.com_port_combobox.currentText()
        LoRa(selected_com_port)

    def update_data(self):
        if self.is_auto_refresh:
            self.update_map()

    def update_map(self):
        latitude, longitude = 0, 0  # Default values
        data = LoRa(self.com_port_combobox.currentText())
        if data:
            latitude = data[10]
            longitude = data[11]

        coordinates = (latitude, longitude)
        self.coordinates_history.append(coordinates)

        self.map_object.location = coordinates
        self.webview.setHtml(self.map_object._repr_html_())


class SensorValuesWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.temperature_label = QLabel("Temperature: N/A")
        self.pressure_label = QLabel("Pressure: N/A")
        self.height_label = QLabel("Height: N/A")
        self.rssi_label = QLabel("RSSI: N/A")

        layout = QVBoxLayout()
        layout.addWidget(self.temperature_label)
        layout.addWidget(self.pressure_label)
        layout.addWidget(self.height_label)
        layout.addWidget(self.rssi_label)

        self.setLayout(layout)

    def update_values(self, data):
        if data:
            self.temperature_label.setText(f"Temperature: {data[1]}")
            self.pressure_label.setText(f"Pressure: {data[2]}")
            self.height_label.setText(f"Height: {data[12]}")
            self.rssi_label.setText(f"RSSI: {data[13]}")


class SensorPlotWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.grid(True)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        self.setLayout(layout)

    def plot_data(self, data):
        if data:
            self.ax.clear()
            self.ax.plot(data, color='red')
            self.ax.grid(True)
            self.canvas.draw()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.real_time_map = RealTimeMap()
        self.sensor_values_widget = SensorValuesWidget()
        self.sensor_plot_widget = SensorPlotWidget()

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.real_time_map)
        main_layout.addWidget(self.sensor_values_widget)
        main_layout.addWidget(self.sensor_plot_widget)

        self.setLayout(main_layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setWindowTitle('Eye-In-The-Sky Control Center')
    window.setGeometry(100, 100, 800, 600)
    window.show()
    sys.exit(app.exec_())
