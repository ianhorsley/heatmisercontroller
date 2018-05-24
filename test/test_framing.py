## Complete set of tests for framing functions

import unittest
import logging
import serial

from heatmisercontroller.framing import _hmCheckFrameCRC, _hmCheckResponseFrameLength, _hmCheckResponseFrameAddresses, _hmCheckResponseFrameFunc, _hmVerifyResponse, _hmFormFrame
#from heatmisercontroller.framing import crc16
from heatmisercontroller.exceptions import hmResponseError, hmResponseErrorCRC
from heatmisercontroller.hm_constants import HMV3_ID

class test_framing(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.ERROR)
    self.goodwritemessage = [5, 11, 129, 1, 34, 0, 1, 0, 255, 222, 138] #sent message
    self.goodreadmessage = [5, 10, 129, 0, 34, 0, 8, 0, 193, 72] #sent message
    self.goodresponsemessage = [129, 12, 0, 5, 0, 10, 0, 01, 00, 255, 145, 201]
    self.goodackmessage = [129, 7, 0, 5, 1, 116, 39]
    self.badackmessage = [129, 8, 0, 5, 1, 116, 39] # length doesn't match header and crc wrong
  
  #crc
  def test_framecheckcrc_short(self):
#    self.assertTrue(True)
    with self.assertRaises(hmResponseError):
      _hmCheckFrameCRC(HMV3_ID,[0])
      
  def test_framecheckcrc_bad_CRC(self):
    with self.assertRaises(hmResponseErrorCRC):
      _hmCheckFrameCRC(HMV3_ID,self.badackmessage)
      
  def test_framecheckcrc_good(self):
    _hmCheckFrameCRC(HMV3_ID,self.goodreadmessage)
    _hmCheckFrameCRC(HMV3_ID,[255,255]) #only crc
    _hmCheckFrameCRC(HMV3_ID,self.goodresponsemessage)
    _hmCheckFrameCRC(HMV3_ID,self.goodackmessage)
  
  #length
  def test_framechecklength(self):
    #crc = crc16()
    #print crc.run(self.goodackmessage)
    _hmCheckResponseFrameLength(HMV3_ID, self.goodresponsemessage, 1)
    _hmCheckResponseFrameLength(HMV3_ID, self.goodackmessage, 1)
    
  def test_framechecklength_short(self):
    with self.assertRaises(hmResponseError):
      _hmCheckResponseFrameLength(HMV3_ID, [0, 0, 0, 0], 1)
      
  def test_framechecklength_mismatch(self):
    with self.assertRaises(hmResponseError):
      _hmCheckResponseFrameLength(HMV3_ID, self.badackmessage, 1)
      
  def test_framechecklength_mismatch2(self):
    with self.assertRaises(hmResponseError):
      _hmCheckResponseFrameLength(HMV3_ID, self.goodresponsemessage, 2)
  
  #addresses
  def test_framecheckaddresses_good(self):
    _hmCheckResponseFrameAddresses(HMV3_ID, 5, 129, self.goodresponsemessage)
    
  def test_framecheckaddresses_dest(self):
    with self.assertRaises(hmResponseError):
      _hmCheckResponseFrameAddresses(HMV3_ID, 5, 1, self.goodresponsemessage)
      
  def test_framecheckaddresses_source(self):
    with self.assertRaises(hmResponseError):
      _hmCheckResponseFrameAddresses(HMV3_ID, 1, 129, self.goodresponsemessage)

  def test_framecheckaddresses_source_range(self):
    with self.assertRaises(hmResponseError):
      _hmCheckResponseFrameAddresses(HMV3_ID, 33, 129, [129, 7, 0, 33, 1, 116, 39])      
      
  def test_framecheckaddresses_dest_range(self):
    with self.assertRaises(hmResponseError):
      _hmCheckResponseFrameAddresses(HMV3_ID, 5, 128, [128, 7, 0, 5, 1, 116, 39])

  #function
  def test_framecheckfunction_good(self):
    _hmCheckResponseFrameFunc(HMV3_ID, 0, self.goodresponsemessage)

  def test_framecheckfunction_wrong(self):
    with self.assertRaises(hmResponseError):
      _hmCheckResponseFrameFunc(HMV3_ID, 1, self.goodresponsemessage) 
  
  def test_framecheckfunction_range(self):
    with self.assertRaises(hmResponseError):
      _hmCheckResponseFrameFunc(HMV3_ID, 2, [129, 7, 0, 5, 2, 116, 39]) 
  
  #verify
  def test_framecheck_good(self):
    _hmVerifyResponse(HMV3_ID, 5, 129, 0, 1, self.goodresponsemessage)
    
  def test_framecheck_bad(self):
    with self.assertRaises(hmResponseError):
      _hmVerifyResponse(HMV3_ID, 5, 129, 0, 1, self.badackmessage)
      
  #form
  def test_form_good_write(self):
  #self.goodwritemessage = [5, 11, 129, 1, 34, 0, 1, 0, 255, 193, 72] #sent message
    ret = _hmFormFrame(5, HMV3_ID, 129, 1, 34, 1, [255])
    self.assertEqual(ret, self.goodwritemessage)
    
  def test_form_good_read(self):
    ret = _hmFormFrame(5, HMV3_ID, 129, 0, 34, 8, [])
    self.assertEqual(ret, self.goodreadmessage)    

  def test_form_bad_length(self):
    with self.assertRaises(ValueError):
      ret = _hmFormFrame(5, HMV3_ID, 129, 1, 34, 10, [255])
      
  def test_form_bad_prot(self):
    with self.assertRaises(ValueError):
      ret = _hmFormFrame(5, HMV3_ID+99, 129, 1, 34, 1, [255])
