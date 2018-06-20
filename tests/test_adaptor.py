import unittest
import logging
import serial

from heatmisercontroller.adaptor import Heatmiser_Adaptor
from heatmisercontroller.hm_constants import HMV3_ID

from mock_serial import SerialTestClass, setupTestClass
                                  
class test_serial(unittest.TestCase):
  def setUp(self):
    self.serialport = SerialTestClass()
    logging.basicConfig(level=logging.ERROR)
    setup = setupTestClass()
    self.func = Heatmiser_Adaptor(setup)
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

