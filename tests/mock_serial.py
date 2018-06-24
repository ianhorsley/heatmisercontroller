"""Lookbock self class for overloading serial port in unitests"""
import serial

class SerialTestClass(object):
    """A mock serial port test class"""
    def __init__(self, noTimeOut=None):
        """Creates a mock serial port which is a loopback object"""
        self._port = "loop://"
        self._timeout = 0
        self._baudrate = 4800 
        self.serialPort = \
            serial.serial_for_url(url=self._port,
                                  timeout=self._timeout,
                                  baudrate=self._baudrate)
        if noTimeOut is None:
            self.serialPort.COM_BUS_RESET_TIME = 0.1
            self.serialPort.COM_START_TIMEOUT = 0.1
            self.serialPort.COM_TIMEOUT = 1
            self.serialPort.COM_MIN_TIMEOUT = 0.1
        else:
            self.serialPort.COM_BUS_RESET_TIME = noTimeOut
            self.serialPort.COM_START_TIMEOUT = noTimeOut
            self.serialPort.COM_TIMEOUT = noTimeOut
            self.serialPort.COM_MIN_TIMEOUT = noTimeOut

class SetupTestClass(object):
    """Dummy serial config for unittesting"""
    def __init__(self):
        self.settings = {}
        self.settings['controller'] = {'my_master_addr':129}
        self.settings['serial'] = {'COM_BUS_RESET_TIME': 0.1}
