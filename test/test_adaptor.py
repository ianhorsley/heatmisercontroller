import unittest
import logging
import serial

from heatmisercontroller.adaptor import Heatmiser_Adaptor

class SerialTestClass(object):
    """A mock serial port test class"""
    def __init__(self):
        """Creates a mock serial port which is a loopback object"""
        self._port = "loop://"
        self._timeout = 0
        self._baudrate = 4800 
        self.serialPort = \
            serial.serial_for_url(url=self._port,
                                  timeout=self._timeout,
                                  baudrate=self._baudrate)
                                      
class test_serial(unittest.TestCase):
  def setUp(self):
  
    self.serialport = SerialTestClass()
    logging.basicConfig(level=logging.ERROR)
    self.func = Heatmiser_Adaptor()
    self.func.serport = self.serialport.serialPort
    self.goodmessage = [5, 10, 129, 0, 34, 0, 8, 0, 193, 72]      
      
      
  def test_sendmsg_1(self):
    # Send message
    self.func._hmSendMsg(self.goodmessage)
    # Use serial to receive raw transmission
    ret = self.serialport.serialPort.read(len(self.goodmessage))
    retasarray = map(ord,ret)

    # Check that the returned data from the serial port == goodmessage
    assert retasarray == self.goodmessage

  def test_receivemsg_1(self):
    string = ''.join(map(chr,self.goodmessage))
    self.serialport.serialPort.write(self.goodmessage)
    ret = self.func._hmReceiveMsg(len(self.goodmessage))
    # Check that the returned data from the serial port == goodmessage
    assert ret == self.goodmessage
    
  def test_receivemsg_2(self):
    string = ''.join(map(chr,self.goodmessage))
    self.serialport.serialPort.write(self.goodmessage)
    ret = self.func._hmReceiveMsg(2)
    # Check that the returned data from the serial port == goodmessage
    assert ret == self.goodmessage[:2]
    
  def test_receivemsg_3(self):
    string = ''.join(map(chr,self.goodmessage))
    self.serialport.serialPort.write(self.goodmessage)
    ret = self.func._hmReceiveMsg(1)
    # Check that the returned data from the serial port == goodmessage
    assert ret == self.goodmessage[:1]
      
if __name__ == '__main__':
    unittest.main()

