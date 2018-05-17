#
# Ian Horsley 2018
#

import serial

COM_PORT = '/dev/ttyUSB0' # 1 less than com port, USB is 6=com7, ether is 9=10
COM_BAUD = 4800
COM_SIZE = serial.EIGHTBITS
COM_PARITY = serial.PARITY_NONE
COM_STOP = serial.STOPBITS_ONE
COM_TIMEOUT = 1 #time to wait for full response

COM_SEND_MIN_TIME = 1  #minimum time between sending commands to a device (broadcast only??)
COM_BUS_RESET_TIME = .1 #minimum time to let bus stabilise after ACK before sending to a different device
