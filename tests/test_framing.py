"""Complete set of tests for framing functions

## Imported crc16 function not tested"""

import unittest
import logging

from heatmisercontroller.framing import _check_frame_crc, _check_response_frame_length, _check_response_frame_addresses, _check_response_frame_function, verify_response, form_frame
from heatmisercontroller.exceptions import HeatmiserResponseError, HeatmiserResponseErrorCRC
from heatmisercontroller.hm_constants import HMV3_ID

class TestFraming(unittest.TestCase):
    """Unitests for framing"""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        self.goodwritemessage = [5, 11, 129, 1, 34, 0, 1, 0, 255, 222, 138] #sent message
        self.goodreadmessage = [5, 10, 129, 0, 34, 0, 8, 0, 193, 72] #sent message
        self.goodresponsemessage = [129, 12, 0, 5, 0, 10, 0, 01, 00, 255, 145, 201]
        self.goodackmessage = [129, 7, 0, 5, 1, 116, 39]
        self.badackmessage = [129, 8, 0, 5, 1, 116, 39] # length doesn't match header and crc wrong

    #crc
    def test_framecheckcrc_short(self):
        with self.assertRaises(HeatmiserResponseError):
            _check_frame_crc(HMV3_ID, [0])
            
    def test_framecheckcrc_bad_CRC(self):
        with self.assertRaises(HeatmiserResponseErrorCRC):
            _check_frame_crc(HMV3_ID, self.badackmessage)
            
    def test_framecheckcrc_good(self):
        _check_frame_crc(HMV3_ID, self.goodreadmessage)
        _check_frame_crc(HMV3_ID, [255, 255]) #only crc
        _check_frame_crc(HMV3_ID, self.goodresponsemessage)
        _check_frame_crc(HMV3_ID, self.goodackmessage)
    
    #length
    def test_framechecklength(self):
        #crc = crc16()
        #print crc.run(self.goodackmessage)
        _check_response_frame_length(HMV3_ID, self.goodresponsemessage, 1)
        _check_response_frame_length(HMV3_ID, self.goodackmessage, 1)
        
    def test_framechecklength_short(self):
        with self.assertRaises(HeatmiserResponseError):
            _check_response_frame_length(HMV3_ID, [0, 0, 0, 0], 1)
            
    def test_framechecklength_mismatch(self):
        with self.assertRaises(HeatmiserResponseError):
            _check_response_frame_length(HMV3_ID, self.badackmessage, 1)
            
    def test_framechecklength_mismatch2(self):
        with self.assertRaises(HeatmiserResponseError):
            _check_response_frame_length(HMV3_ID, self.goodresponsemessage, 2)
    
    #addresses
    def test_framecheckaddresses_good(self):
        _check_response_frame_addresses(HMV3_ID, 5, 129, self.goodresponsemessage)
        
    def test_framecheckaddresses_dest(self):
        with self.assertRaises(HeatmiserResponseError):
            _check_response_frame_addresses(HMV3_ID, 5, 1, self.goodresponsemessage)
            
    def test_framecheckaddresses_source(self):
        with self.assertRaises(HeatmiserResponseError):
            _check_response_frame_addresses(HMV3_ID, 1, 129, self.goodresponsemessage)

    def test_framecheckaddresses_source_range(self):
        with self.assertRaises(HeatmiserResponseError):
            _check_response_frame_addresses(HMV3_ID, 33, 129, [129, 7, 0, 33, 1, 116, 39])            

    def test_framecheckaddresses_dest_range(self):
        with self.assertRaises(HeatmiserResponseError):
            _check_response_frame_addresses(HMV3_ID, 5, 128, [128, 7, 0, 5, 1, 116, 39])

    #function
    def test_framecheckfunction_good(self):
        _check_response_frame_function(HMV3_ID, 0, self.goodresponsemessage)

    def test_framecheckfunction_wrong(self):
        with self.assertRaises(HeatmiserResponseError):
            _check_response_frame_function(HMV3_ID, 1, self.goodresponsemessage)
    
    def test_framecheckfunction_range(self):
        with self.assertRaises(HeatmiserResponseError):
            _check_response_frame_function(HMV3_ID, 2, [129, 7, 0, 5, 2, 116, 39])
    
    #verify
    def test_framecheck_good(self):
        verify_response(HMV3_ID, 5, 129, 0, 1, self.goodresponsemessage)
        
    def test_framecheck_bad(self):
        with self.assertRaises(HeatmiserResponseError):
            verify_response(HMV3_ID, 5, 129, 0, 1, self.badackmessage)
            
    #form frames
    def test_form_good_write(self):
        ret = form_frame(5, HMV3_ID, 129, 1, 34, 1, [255])
        self.assertEqual(ret, self.goodwritemessage)
        
    def test_form_good_read(self):
        ret = form_frame(5, HMV3_ID, 129, 0, 34, 8, [])
        self.assertEqual(ret, self.goodreadmessage)

    def test_form_bad_length(self):
        with self.assertRaises(ValueError):
            form_frame(5, HMV3_ID, 129, 1, 34, 10, [255])
            
    def test_form_bad_prot(self):
        with self.assertRaises(ValueError):
            form_frame(5, HMV3_ID+99, 129, 1, 34, 1, [255])
