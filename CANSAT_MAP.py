import sys
import random
import re
import folium
import serial
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QMessageBox, QFrame
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib as plt
from folium.plugins import MarkerCluster
from colour import Color
from pyquaternion import Quaternion
import math
import where_human as wh
import numpy as np
import pandas as pd
from receiver_pyth import LoRa


# Data labels
# 0 t, 1 T, 2 p, 3 ax, 4 ay, 5 az, 6 q, 7 qx, 8 qy, 9 qz, 10 lat, 11 long, 12 height, 13 rssi


class SensorDataWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.temperature_label = QLabel("Temperature: N/A")
        self.pressure_label = QLabel("Pressure: N/A")
        self.height_label = QLabel("Height: N/A")
        self.rssi_label = QLabel("RSSI: N/A")
        self.human_label = QLabel("Latest human detected: N/A")

        layout = QVBoxLayout()
        layout.addWidget(self.temperature_label)
        layout.addWidget(self.pressure_label)
        layout.addWidget(self.height_label)
        layout.addWidget(self.rssi_label)
        layout.addWidget(self.human_label)

        self.setLayout(layout)

    def update_widget(self, data, selected_com_port):
        if data:
            self.temperature_label.setText(f"Temperature: {data[1]}")
            self.pressure_label.setText(f"Pressure: {data[2]}")
            self.height_label.setText(f"Height: {data[12]}")
            self.rssi_label.setText(f"RSSI: {data[13]}")
            self.human_label.setText(f"Latest human detected: ", wh.getCoordinates(0, 0, data[12], data[10], data[11], data[6], data[7], data[8], data[9], 9152/2, 6944/2, selected_com_port))


class RealTimePlot(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        self.axes.grid(True)  # Enabling gridlines
        super(RealTimePlot, self).__init__(fig)
        self.setParent(parent)

    def plot(self, data):
        self.axes.clear()
        self.axes.plot(data, color='red')  # Setting plot color to red
        self.axes.grid(True)  # Enabling gridlines
        self.draw()


class RealTimeMap(QWidget):
    def __init__(self):
        super().__init__()

        self.zoom_level = 10  # Adjust the zoom level here
        self.map_object = folium.Map(location=[0, 0], zoom_start=self.zoom_level)
        self.marker_cluster = MarkerCluster().add_to(self.map_object)
        self.coordinates_history = []
        self.is_auto_refresh = True
        self.temperature_data = []
        self.pressure_data = []
        self.height_data = []
        self.time_data = []
        self.RSSI_data = []

        self.lora = None  # Initialize as None

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
        main_layout = QVBoxLayout()

        # Creating a QHBoxLayout for the buttons above the map
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.com_port_combobox)

        self.temp_plot = RealTimePlot(self, width=5, height=4, dpi=100)
        self.pressure_plot = RealTimePlot(self, width=5, height=4, dpi=100)
        self.height_plot = RealTimePlot(self, width=5, height=4, dpi=100)
        self.RSSI_plot = RealTimePlot(self, width=5, height=4, dpi=100)

        self.rssi_label = QLabel("RSSI:")
        self.temperature_label = QLabel("Temperature:")
        self.pressure_label = QLabel("Pressure:")
        self.height_label = QLabel("Height:")

        controls_layout = QHBoxLayout()

        labels_layout = QHBoxLayout()
        labels_layout.addWidget(self.temperature_label)
        labels_layout.addWidget(self.pressure_label)
        labels_layout.addWidget(self.height_label)
        labels_layout.addWidget(self.rssi_label)

        plots_layout = QHBoxLayout()
        plots_layout.addWidget(self.temp_plot)
        plots_layout.addWidget(self.pressure_plot)
        plots_layout.addWidget(self.height_plot)
        plots_layout.addWidget(self.RSSI_plot)

        layout = QVBoxLayout()
        layout.addLayout(buttons_layout)  # Add buttons layout above the map
        layout.addWidget(self.webview)
        layout.addLayout(controls_layout)
        layout.addLayout(labels_layout)
        layout.addLayout(plots_layout)

        # New widget for sensor data
        self.sensor_data_widget = SensorDataWidget()

        # Frame for sensor data widget
        sensor_frame = QFrame()
        sensor_frame.setLayout(QVBoxLayout())
        sensor_frame.layout().addWidget(self.sensor_data_widget)
        sensor_frame.setFrameShape(QFrame.Box)
        sensor_frame.setLineWidth(1)

        # Add map and sensor data frame in the same row
        row_layout = QHBoxLayout()
        row_layout.addWidget(sensor_frame)
        row_layout.addLayout(layout)

        self.setLayout(row_layout)

    def connect_to_com_port(self, index):
        selected_com_port = self.com_port_combobox.currentText()
        self.lora = LoRa(selected_com_port)

    def update_data(self):
        if self.is_auto_refresh:
            if self.lora:
                self.update_map()
                self.update_plots()

    def update_map(self):
        if self.lora:
            latitude = self.lora[10]
            longitude = self.lora[11]

            coordinates = (latitude, longitude)
            self.coordinates_history.append(coordinates)

            # Update map location
            self.map_object.location = coordinates

            # Calculate the latest coordinates
            latest_coordinates = self.coordinates_history[-1]

            # Center the map on the latest coordinates using JavaScript
            js_code = f"""
                              var latlng = L.latLng({latest_coordinates[0]}, {latest_coordinates[1]});
                              window.map.setView(latlng);
                          """
            self.webview.page().runJavaScript(js_code)

            if len(self.coordinates_history) > 1:
                # Calculate color gradient
                num_points = len(self.coordinates_history)
                color_gradient = list(Color("blue").range_to(Color("red"), num_points))
                for i in range(1, num_points):
                    start_color = color_gradient[i - 1].hex
                    end_color = color_gradient[i].hex
                    folium.PolyLine([self.coordinates_history[i - 1], self.coordinates_history[i]],
                                    color=start_color,
                                    fill=False,
                                    weight=2,
                                    opacity=0.7).add_to(self.map_object)

            self.map_object.options['zoom'] = 7
            self.webview.setHtml(self.map_object._repr_html_())

    def update_plots(self):
        if self.lora:
            # data_labels = "0 t, 1 T, 2 p, 3 ax, 4 ay, 5 az, 6 q, 7 qx, 8 qy, 9 qz, 10 lat, 11 long, 12 height, 13 rssi"
            time = len(self.temperature_data)
            self.time_data.append(time)
            self.temperature_data.append(self.lora[1])
            self.pressure_data.append(self.lora[2])
            self.height_data.append(self.lora[12])
            self.RSSI_data.append(self.lora[13])

            self.temp_plot.plot(self.temperature_data)
            self.pressure_plot.plot(self.pressure_data)
            self.height_plot.plot(self.height_data)
            self.RSSI_plot.plot(self.RSSI_data)

    def get_bounds(self, coordinates_history):
        min_lat = min(lat for lat, lon in coordinates_history)
        max_lat = max(lat for lat, lon in coordinates_history)
        min_lon = min(lon for lat, lon in coordinates_history)
        max_lon = max(lon for lat, lon in coordinates_history)
        return [(min_lat, min_lon), (max_lat, max_lon)]


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RealTimeMap()
    window.setWindowIcon(QIcon(r"C:\Users\sherl\Downloads\eye_logo.png"))  # Inserting logo in the top right corner
    window.setWindowTitle('Eye-In-The-Sky control center')
    window.setGeometry(100, 100, 800, 600)  # Adjust the window size
    window.show()
    sys.exit(app.exec_())
