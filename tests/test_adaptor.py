"""Unittests for heatmisercontroller.adaptor module"""
import unittest
import logging

from heatmisercontroller.adaptor import HeatmiserAdaptor
from heatmisercontroller.exceptions import HeatmiserResponseError
from mock_serial import SerialTestClass, SetupTestClass
from heatmisercontroller.hm_constants import HMV3_ID
from heatmisercontroller.framing import crc16

class TestSerial(unittest.TestCase):
    """Low level serial send and recieve message tests"""
    def setUp(self):
        self.serialport = SerialTestClass()
        logging.basicConfig(level=logging.ERROR)
        self.setup = SetupTestClass()
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
        retasarray = map(ord, ret)

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
    
    def test_receivemsg_4(self):
        self.serialport.serialPort.write(self.goodmessage)
        ret = self.func._receive_message(1)
        # Check that the returned data from the serial port == goodmessage
        self.assertEqual(ret, self.goodmessage[0:1])
        ret = self.func._receive_message(1)
        # Check that the returned data from the serial port == goodmessage
        self.assertEqual(ret, self.goodmessage[1:2])
        self.func._clear_input_buffer()
        with self.assertRaises(HeatmiserResponseError):
            self.func._receive_message(1)
    
    def test_receivemsg_none(self):
        with self.assertRaises(HeatmiserResponseError):
            self.func._receive_message(1)
    
    def test_updatesettings(self):
        # Send message to open serial port
        self.func._send_message(self.goodmessage)
        # update settings
        self.func._update_settings(self.setup.settings)

class TestReadWrite(unittest.TestCase):
    """Tests for write to and read from device"""
    def setUp(self):
        self.serialport = SerialTestClass(0)
        logging.basicConfig(level=logging.ERROR)
        self.setup = SetupTestClass()
        self.func = HeatmiserAdaptor(self.setup)
        self.func.serport = self.serialport.serialPort
        #self.goodresponse = [129, 7, 0, 5, 1, 116, 39]
        self.crc = crc16()
        #print crc.run(self.goodresponse)

    def tearDown(self):
        del self.func
    
    def test_sendto_1(self):
        goodresponse = [129, 7, 0, 5, 1, 116, 39]
        goodrequest = [5, 11, 129, 1, 12, 0, 1, 0, 1, 19, 67]
        # Setup response
        self.serialport.serialPort.write(goodresponse)
        # Send message
        self.func.write_to_device(5, HMV3_ID, 12, 1, [1])
        # Use serial to receive raw transmission
        ret = self.serialport.serialPort.read(len(goodrequest))
        retasarray = map(ord, ret)
        # Check that the returned data from the serial port == goodmessage
        self.assertEqual(retasarray, goodrequest)
        
    def test_sendto_2(self):
        """Not good test as triggers retries but fails."""
        goodresponse = [129, 7, 0, 5, 1, 0, 0, 129, 7, 0, 5, 1, 116, 39]
        #goodrequest = [5, 11, 129, 1, 12, 0, 1, 0, 1, 19, 67]
        # Setup response
        self.serialport.serialPort.write(goodresponse)
        # Send message
        with self.assertRaises(HeatmiserResponseError):
            self.func.write_to_device(5, HMV3_ID, 12, 1, [1])
        # # Use serial to receive raw transmission
        # ret = self.serialport.serialPort.read(len(goodrequest))
        # retasarray = map(ord,ret)
        # # Check that the returned data from the serial port == goodmessage
        # self.assertEqual(retasarray, goodrequest)

    def test_readfrom_1(self):
        goodresponse = [129, 15, 0, 5, 0, 34, 0, 4, 0, 1, 2, 3, 4, 48, 246]
        goodrequest = [5, 10, 129, 0, 34, 0, 4, 0, 172, 13]
        # Setup response
        self.serialport.serialPort.write(goodresponse)
        # Send message
        self.func.read_from_device(5, HMV3_ID, 34, 4)
        # Use serial to receive raw transmission
        ret = self.serialport.serialPort.read(len(goodrequest))
        retasarray = map(ord,ret)
        # Check that the returned data from the serial port == goodmessage
        self.assertEqual(retasarray, goodrequest)
        
    def test_readall(self):
        goodresponse = [129, 21, 0, 5, 0, 0, 0, 10, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 33, 245]
        goodrequest = [5, 10, 129, 0, 0, 0, 255, 255, 65, 6]
        #print self.crc.run([129, 21, 0, 5, 0, 0, 0, 10, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        # Setup response
        self.serialport.serialPort.write(goodresponse)
        # Send message
        self.func.read_all_from_device(5, HMV3_ID, 10)
        # Use serial to receive raw transmission
        ret = self.serialport.serialPort.read(len(goodrequest))
        retasarray = map(ord,ret)
        # Check that the returned data from the serial port == goodmessage
        self.assertEqual(retasarray, goodrequest)
        
if __name__ == '__main__':
    unittest.main()
