import serial
import csv
import pandas as pd
import serial.tools.list_ports as ports
from pyquaternion import Quaternion
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display





#data_labels = "0 t, 1 T, 2 p, 3 ax, 4 ay, 5 az, 6 q, 7 qx, 8 qy, 9 qz, 10 lat, 11 long, 12 height, 13 rssi"

#theta, phi = 0,
# altitude, latitude, longitude = lat, long, height, a, b, c, d = q, qx, qy, qz,
# xn, yn = 9152/2, 6944/2 - this is the centre of the picture
def getCoordinates(theta, phi, altitude, latitude, longitude, a, b, c, d, xn, yn, COM_PORT):
    ser = serial.Serial(COM_PORT, 9600, timeout=1)
    q1 = Quaternion(axis=[1, 0, 0], angle=theta)  # first angle from servo, to be equal zero in the test campgain as the servo doesn't move
    q2 = Quaternion(axis=[0, 0, 1], angle=phi)  # second angle from servo, to be equal zero in the test campgain as the servo doesn't move
    q3 = Quaternion(a, d, c, b) #b and d are swpaped here bc the 9DOF is not correctly positioned in the CanSat, thus I swapped the x-axis with the z-axis. If it still doesn't work, I recommend trying swapping d with c or adding minus sign before either b or d.
    P = (2 * altitude * math.tan(84 / 360 * math.pi)) / math.sqrt((9152 * 9152 + 6944 * 6944))
    qf = q1 * q2 * q3
    # qf = Quaternion(1, 0, 0, 0)
    v_prime = qf.rotate({P * (9152 / 2 - xn) / altitude, P * (6944 / 2 - yn) / altitude, -1})

    if v_prime[2] >= 0:
        return np.nan, np.nan

    t = -altitude / v_prime[2]
    dx = v_prime[0] * t
    dy = v_prime[1] * t
    r = 6371000

    latitude = latitude + dy / r / math.pi * 180

    longitude = longitude + dx / r / math.cos(latitude / 180 * math.pi) / math.pi * 180
    #print(longitude, latitude)
    return latitude, longitude #coordinates of the newly found point


