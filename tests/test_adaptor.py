import unittest
import logging

from heatmisercontroller.adaptor import HeatmiserAdaptor
from heatmisercontroller.exceptions import hmResponseError
from mock_serial import SerialTestClass, setupTestClass

class test_serial(unittest.TestCase):
  def setUp(self):
    self.serialport = SerialTestClass()
    logging.basicConfig(level=logging.ERROR)
    self.setup = setupTestClass()
    self.func = HeatmiserAdaptor(self.setup)
    self.func.serport = self.serialport.serialPort
    self.goodmessage = [5, 10, 129, 0, 34, 0, 8, 0, 193, 72]

  def tearDown(self):
    del self.func
  
  def test_sendmsg_1(self):
    # Send message
    self.func._send_message(self.goodmessage)
    # Use serial to receive raw transmission
    ret = self.serialport.serialPort.read(len(self.goodmessage))
    retasarray = map(ord,ret)

    # Check that the returned data from the serial port == goodmessage
    self.assertEqual(retasarray, self.goodmessage)

  def test_receivemsg_1(self):
    #string = ''.join(map(chr,self.goodmessage))
    self.serialport.serialPort.write(self.goodmessage)
    #self.func._disconnect() # make sure checks the reconnect function
    ret = self.func._receive_message(len(self.goodmessage))
    # Check that the returned data from the serial port == goodmessage
    self.assertEqual(ret, self.goodmessage)
    
  def test_receivemsg_2(self):
    self.serialport.serialPort.write(self.goodmessage)
    ret = self.func._receive_message(2)
    # Check that the returned data from the serial port == goodmessage
    self.assertEqual(ret, self.goodmessage[:2])
    
  def test_receivemsg_3(self):
    self.serialport.serialPort.write(self.goodmessage)
    ret = self.func._receive_message(1)
    # Check that the returned data from the serial port == goodmessage
    self.assertEqual(ret, self.goodmessage[:1])
  
  def test_receivemsg_none(self):
    with self.assertRaises(hmResponseError):
      self.func._receive_message(1)
  
  def test_updatesettings(self):
    # Send message to open serial port
    self.func._send_message(self.goodmessage)
    # update settings
    self.func._update_settings(self.setup.settings)
    
if __name__ == '__main__':
    unittest.main()

