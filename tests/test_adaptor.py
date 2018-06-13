import unittest
import logging
import serial

from heatmisercontroller.adaptor import Heatmiser_Adaptor
from heatmisercontroller.hm_constants import HMV3_ID

class SerialTestClass(object):
    """A mock serial port test class"""
    def __init__(self, noTimeOut = None):
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

class argstore(object):
    def store(self, *args):
        self.args = args
            
class setupTestClass(object):
    def __init__(self):
      self.settings = {}
      self.settings['controller'] = {'my_master_addr':129}
      self.settings['serial'] = {'COM_BUS_RESET_TIME': 0.1}
                                  
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

class test_protocol(unittest.TestCase):
  def setUp(self):
    self.serialport = SerialTestClass(0)
    logging.basicConfig(level=logging.ERROR)
    setup = setupTestClass()
    self.func = Heatmiser_Adaptor(setup)
    self.func.serport = self.serialport.serialPort

  def test_setfield_1(self):
    #checks the arguements sent to hmWriteToController
    #network_address, protocol, fieldname, payload
    tester = argstore()
    self.func.hmWriteToController = tester.store
    self.func.setField(5, HMV3_ID, 'frosttemp', 7 )
    self.assertEqual(tester.args,(5, 3, 17, 1, [7]))
    
  def test_setfield_2(self):
    tester = argstore()
    self.func.hmWriteToController = tester.store
    self.func.setField(5, HMV3_ID, 'currenttime', [7,7,7,7] )
    self.assertEqual(tester.args,(5, 3, 43, 4, [7,7,7,7]))
    
  def test_setfield_errors(self):
    with self.assertRaises(ValueError):
        self.func.setField(5, HMV3_ID, 'frosttemp', 3 )
    with self.assertRaises(TypeError):
        self.func.setField(5, HMV3_ID, 'frosttemp', [3,3] )
    with self.assertRaises(ValueError):
        self.func.setField(5, HMV3_ID, 'currenttime', [8,7,7,7] )
    with self.assertRaises(TypeError):
        self.func.setField(5, HMV3_ID, 'currenttime', 7  )    
    
if __name__ == '__main__':
    unittest.main()

