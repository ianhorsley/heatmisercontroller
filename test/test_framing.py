import unittest
import logging
import serial

from heatmisercontroller.framing import _hmCheckFrameCRC
from heatmisercontroller.exceptions import hmResponseError, hmResponseErrorCRC
from heatmisercontroller.hm_constants import HMV3_ID

class test_framing(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.ERROR)
    #self.func = Heatmiser_Adaptor()
    #self.func.COM_TIMEOUT = 0 #speed up testing when reset input buffer called
    self.goodmessage = [5, 10, 129, 0, 34, 0, 8, 0, 193, 72]
    
  def test_framecheck_short(self):
#    self.assertTrue(True)
    with self.assertRaises(hmResponseError):
      _hmCheckFrameCRC(HMV3_ID,[0])
      
  def test_framecheck_no_CRC(self):
    with self.assertRaises(hmResponseErrorCRC):
      _hmCheckFrameCRC(HMV3_ID,[0,0,0])
      
  def test_framecheck_good(self):
    _hmCheckFrameCRC(HMV3_ID,self.goodmessage)
    
  def test_framecheck_only_crc(self):
    _hmCheckFrameCRC(HMV3_ID,[255,255])

