import tkinter as tk
from tkinter import ttk
import tkintermapview
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pyquaternion import Quaternion
import math
import numpy as np
import serial
from serial.tools.list_ports import comports
import csv


filename = "dataCanSat"
def getCoordinate(theta, phi, altitude, latitude, longitude, a, b, c, d, xn, yn):
    # theta, phi - angles from the servo, in this case equal zero; altitude - here 35, latitude, longitude - from GPS, here 52.257071902441425, 20.992438191518758; a, b, c, d - data from 9DOF; xn, yn - here 9152/2 and 6944/2
    q1 = Quaternion(axis=[1, 0, 0], angle=theta)  # first angle from Klara
    q2 = Quaternion(axis=[0, 0, 1], angle=phi)  # second angle from Klara
    q3 = Quaternion(a, b, c, d)  
    q4 = Quaternion(axis=[1, 0, 0], angle=math.pi/2)
    P = (2 * altitude * math.tan(84 / 360 * math.pi)) / math.sqrt((9152 * 9152 + 6944 * 6944))
    qf = q1*q2*q3*q4 #final version

    
    v = np.array([P * (9152 / 2 - xn) / altitude, P * (6944 / 2 - yn) / altitude, -1])
    v_prime = qf.rotate(v)
    if v_prime[2] >= 0:
        print("None")
        return np.nan, np.nan

    t = -altitude / v_prime[2]
    dx = v_prime[0] * t
    dy = v_prime[1] * t
    r = 6371000

    latitude = latitude + dy / r / math.pi * 180

    longitude = longitude + dx / r / math.cos(latitude / 180 * math.pi) / math.pi * 180
    return latitude, longitude  


# Function definitions (update_table, add_data_to_plots, add_point, LoRa) remain unchanged
def update_table(data):
    # Clear existing rows
    for row in treeview.get_children():
        treeview.delete(row)

    # Insert new data into the table
    # relevant_labels = ['Time', 'Temperature', 'Pressure', 'Temperature', 'Latitude', 'Longitude', 'Height', 'RSSI']
    for label in data:
        treeview.insert('', 'end', values=(label, data[label]))
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        # Write all rows to the CSV file
        writer.writerows(data)

global local_history
local_history = []


def add_data_to_plots(data):
    if data:
        time = data['Time']
        temperature = data['Temperature']
        pressure = data['Pressure']
        rssi = data['RSSI']

        # Add data to the plots
        add_point1(time, temperature, "Temperature vs Time", ax1)
        add_point2(time, pressure, "Pressure vs Time", ax2)
        add_point3(time, rssi, "RSSI vs Time", ax3)

        # Add latitude and longitude to the map
        if 'Latitude' in data:
            # print('GPS received')
            lat = data['Latitude']
            lon = data['Longitude']
            localisation = (lat, lon)
            map_widget.delete_all_marker()
            map_widget.set_marker(lat, lon)
            if len(local_history)>1:
                map_widget.set_path([local_history[-1], localisation], width=3)
            local_history.append(localisation)
            #path1.set_position_list(local_history)

            try:
                map_widget.set_position(lat, lon)
            except:
                print('Map position not updated.')

            print(data)
            lat1, lon1 = getCoordinate(0, 0, data['Height'], data['Latitude'], data['Longitude'], data['q'], data['qx'],
                                     data['qy'], data['qz'], 9152, 0)
            lat2, lon2 = getCoordinate(0, 0, data['Height'], data['Latitude'], data['Longitude'], data['q'], data['qx'],
                                     data['qy'], data['qz'], 0, 0)
            lat3, lon3 = getCoordinate(0, 0, data['Height'], data['Latitude'], data['Longitude'], data['q'], data['qx'],
                                     data['qy'], data['qz'], 0, 6944)
            lat4, lon4 = getCoordinate(0, 0, data['Height'], data['Latitude'], data['Longitude'], data['q'], data['qx'],
                                     data['qy'], data['qz'], 9152, 6944)
            if np.isnan(lat1) & np.isnan(lat2) & np.isnan(lat3) & np.isnan(lat4):
                map_widget.set_polygon([(lat1, lon1), (lat2, lon2), (lat3, lon3), (lat4, lon4)])


global points1,point2, points3
points1 = []
points2 = []
points3 = []


def add_point1(x, y, title, ax):
    # ax.clear()
    points1.append((x, y))
    ax.plot([p[0] for p in points1], [p[1] for p in points1], color='red')
    ax.set_title(title)
    canvas1.draw()


def add_point2(x, y, title, ax):
    # ax.clear()
    points2.append((x, y))
    ax.plot([p[0] for p in points2], [p[1] for p in points2], color='blue')
    ax.set_title(title)
    canvas2.draw()


def add_point3(x, y, title, ax):
    # ax.clear()
    points3.append((x, y))
    ax.plot([p[0] for p in points3], [p[1] for p in points3], color='green')
    ax.set_title(title)
    canvas3.draw()


def LoRa():
    # Define the baud rate
    try:
        # Read a line of data from the serial port
        global ser
        if ser.is_open:
            data = ser.readline().decode('latin1').strip()
            data = data.split(',')
            print(data)

            # Create a dictionary to store data labels and values
            data_dict = {}
            valid_data = False
            if len(data) == 4:
                label = ['Time', 'Temperature', 'Pressure', 'RSSI']
                valid_data = True
            if len(data) == 11:
                label = ['Time', 'Temperature', 'Pressure', 'q', 'qx', 'qy', 'qz', 'Latitude', 'Longitude', 'Height', 'RSSI']
                valid_data = True
            if len(data) == 6:
                valid_data = True
                label = ['Time', 'Temperature', 'Pressure', 'Latitude', 'Longitude', 'RSSI']

            if valid_data:
                hours = int(data[0][:2])
                minutes = int(data[0][3:5])
                seconds = int(data[0][6:])
                # Calculate total seconds
                total_seconds = hours * 3600 + minutes * 60 + seconds
                data_dict['Time'] = total_seconds
                for i in range(1,len(data)):
                    data_dict[label[i]] = float(data[i])

            return data_dict
        else:
            return False
    except serial.SerialException:
        return False


def update_data():
    # Retrieve data from LoRa function using the selected COM port
    data = LoRa()
    print(data)
    if data:
        print('Data received')
        # Update the table with new data
        update_table(data)
        # Add new data to the plots
        add_data_to_plots(data)

    # Schedule the function to be called again after 1000 ms (1 second)
    print(data)
    root.after(100, update_data)


# Initialize Tkinter and Matplotlib Figure
root = tk.Tk()
root.title("LoRa Data Visualization")
root.geometry("1000x800")

# Create the main frames
top_left_frame = tk.Frame(root)
top_right_frame = tk.Frame(root)
bottom_frame_1 = tk.Frame(root)
bottom_frame_2 = tk.Frame(root)
bottom_frame_3 = tk.Frame(root)

top_left_frame.grid(row=0, rowspan=2, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
top_right_frame.grid(row=0, rowspan=2, column=4, columnspan=2, sticky="nsew", padx=5, pady=5)
bottom_frame_1.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
bottom_frame_2.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=5, pady=5)
bottom_frame_3.grid(row=2, column=4, columnspan=2, sticky="nsew", padx=5, pady=5)

root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=2)
root.grid_columnconfigure([0, 1, 2], weight=1)

# Create the map widget
map_widget = tkintermapview.TkinterMapView(top_left_frame, width=200, height=200)
map_widget.pack(fill=tk.BOTH, expand=True)
map_widget.set_zoom(10)

# Create a label and combobox for selecting COM port
com_port_label = ttk.Label(top_left_frame, text="Select COM Port:")
com_port_label.pack(pady=(5,0))
com_port_var = tk.StringVar()
com_port_combobox = ttk.Combobox(top_left_frame, textvariable=com_port_var, width=48)
com_port_combobox.pack(pady=5)
# Example COM ports, modify as needed
com_ports = [port.name for port in comports()]
# Set COM port options
com_port_combobox['values'] = com_ports
com_port_combobox.current(0)  # Set default value

COM_PORT = com_port_var.get()
BAUD_RATE = 9600
ser = serial.Serial(COM_PORT, BAUD_RATE)

# Create Treeview widget for the table
columns = ('Label', 'Value')
treeview = ttk.Treeview(top_right_frame, columns=columns, show='headings')
treeview.pack(fill=tk.BOTH, expand=True)
for col in columns:
    treeview.heading(col, text=col)

# Initialize Matplotlib Figures and Axes for the plots
fig1, ax1 = plt.subplots(figsize=(5, 4))
canvas1 = FigureCanvasTkAgg(fig1, master=bottom_frame_1)
canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)

fig2, ax2 = plt.subplots(figsize=(5, 4))
canvas2 = FigureCanvasTkAgg(fig2, master=bottom_frame_2)
canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

fig3, ax3 = plt.subplots(figsize=(5, 4))
canvas3 = FigureCanvasTkAgg(fig3, master=bottom_frame_3)
canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Call update_data() to start updating the data visualization
update_data()

root.mainloop()
