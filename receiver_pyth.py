import re
import serial

def LoRa(COM_PORT):
    # Define the COM port and baud rate
    BAUD_RATE = 9600
    #COM_PORT = 'COM9'
    # Open the serial port

    try:
        ser = serial.Serial(COM_PORT, BAUD_RATE)
        # Read a line of data from the serial port
        data = ser.readline().decode('latin1').strip()
        data_labels = data

        # Split the string into individual labels
        labels_list = data_labels.split(', ')
        if data is not None:
            if len(labels_list) > 13:
                # Create a dictionary to map labels to column indices
                try:
                    label_to_index = {label.split()[0]: idx for idx, label in enumerate(labels_list)}
                    pattern = re.compile(r'\d+(\.\d+)?')

                    # Remove non-numeric characters and convert to float
                    filtered_data = [float(pattern.search(item).group()) for item in labels_list if pattern.search(item)]
                    return filtered_data
                except Exception as e:
                    LoRa(COM_PORT)
                    return [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            else:
                return [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        else:
            return [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    except serial.SerialException:
        # Close the serial port when Ctrl+C is pressed
        return [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]






