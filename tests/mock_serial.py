"""Lookbock self class for overloading serial port in unitests and mock adaptor"""
import serial
import logging
from heatmisercontroller.adaptor import HeatmiserAdaptor
from heatmisercontroller.exceptions import HeatmiserResponseError

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
        self.settings['controller'] = {'my_master_addr':129, 'auto_connect': False}
        self.settings['serial'] = {'COM_BUS_RESET_TIME': 0.1}

class MockHeatmiserAdaptor(HeatmiserAdaptor):
    """Modified HeatmiserAdaptor that stores writes and and provide read responses."""
    def __init__(self, setup):
        super(MockHeatmiserAdaptor, self).__init__(setup)
        self.reset()
    
    def reset(self):
        """Resets input and output arrays"""
        self.arguments = []
        self.outputs = []
        
    def write_to_device(self, network_address, protocol, unique_address, length, payload):
        """Stores the arguments sent to write"""
        self.arguments.append((network_address, protocol, unique_address, length, payload))

    def setresponse(self, inputs):
        """Sets responses to read from device.
        
        Expects a list of lists"""
        self.outputs = inputs

    def read_from_device(self, network_address, protocol, unique_start_address, expected_length, readall=False):
        """Stores the arguments sent to read and provides a response"""
        if len(self.outputs) > 0:
            self.arguments.append((network_address, protocol, unique_start_address, expected_length, readall))
            logging.debug("Response %s"%(', '.join(str(x) for x in self.outputs[0])))
            return self.outputs.pop(0)
        else:
            raise HeatmiserResponseError("No Response")