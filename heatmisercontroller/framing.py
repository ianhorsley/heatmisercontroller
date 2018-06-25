"""Functions for creating and checking Heatmiser protocol frames"""
import logging

from hm_constants import *
from .exceptions import HeatmiserResponseError, HeatmiserResponseErrorCRC

### low level framing functions

def form_read_frame(destination, protocol, source, start, length):
    """Forms a read message payload, including CRC"""
    return form_frame(destination, protocol, source, FUNC_READ, start, length, [])

# TODO check master address is in legal range
def form_frame(destination, protocol, source, function, start, length, payload):
    """Forms a message payload, including CRC"""
    if protocol != HMV3_ID:
        raise ValueError("Protocol unknown")
    start_low = start & BYTEMASK
    start_high = (start >> 8) & BYTEMASK
    length_low = length & BYTEMASK
    length_high = (length >> 8) & BYTEMASK
    payload_length = len(payload)
    frame_length = MIN_FRAME_SEND_LENGTH
    if function == FUNC_WRITE:
        if length != payload_length:
            raise ValueError("Payload doesn't match length %s" % length)
        if length > MAX_PAYLOAD_SEND_LENGTH:
            raise ValueError("Payload to long %s" % length)
        frame_length = MIN_FRAME_SEND_LENGTH + payload_length
    msg = [destination, frame_length, source, function, start_low, start_high, length_low, length_high]
    if function == FUNC_WRITE:
        msg = msg + payload

    crc = crc16()
    msg = msg + crc.run(msg)
    return msg

def _check_frame_crc(protocol, data):
    """Takes frame with CRC and checks it is valid"""
    datalength = len(data)

    if protocol != HMV3_ID:
        raise ValueError("Protocol unknown")
    if datalength < 2:
        raise HeatmiserResponseError("No CRC")

    checksum = data[len(data)-2:]
    rxmsg = data[:len(data)-2]

    crc = crc16() # Initialises the CRC
    expectedchecksum = crc.run(rxmsg)
    if expectedchecksum != checksum:
        raise HeatmiserResponseErrorCRC("CRC is incorrect")

def _check_response_frame_length(protocol, data, expected_length):
    """Takes frame and checks length, must be a receive frame"""
    if protocol != HMV3_ID:
        raise ValueError("Protocol unknown")

    if len(data) < MIN_FRAME_RESP_LENGTH:
        raise HeatmiserResponseError("Response length too short: %s %s"%(len(data), MIN_FRAME_RESP_LENGTH))

    frame_len_l = data[FR_LEN_LOW]
    frame_len_h = data[FR_LEN_HIGH]
    frame_len = (frame_len_h << 8) | frame_len_l
    func_code = data[FR_FUNC_CODE]
    
    if len(data) != frame_len:
        raise HeatmiserResponseError("Frame length does not match header: %s %s" %(len(data), frame_len))

    if expected_length != RW_LENGTH_ALL and func_code == FUNC_READ and frame_len != MIN_FRAME_READ_RESP_LENGTH + expected_length:
        # Read response length is wrong
        raise HeatmiserResponseError("Response length %s not EXPECTED value %s + %s given read request" %(frame_len, MIN_FRAME_READ_RESP_LENGTH, expected_length))
    if func_code == FUNC_WRITE and frame_len != FRAME_WRITE_RESP_LENGTH:
        # Reply to Write is always 7 long
        raise HeatmiserResponseError("Response length %s not EXPECTED value %s given write request" %(frame_len, FRAME_WRITE_RESP_LENGTH))
            
def _check_response_frame_addresses(protocol, source, destination, data):
    """Takes frame and checks addresses are correct"""
    if protocol != HMV3_ID:
        raise ValueError("Protocol unknown")
        
    dest_addr = data[FR_DEST_ADDR]
    source_addr = data[FR_SOURCE_ADDR]

    if dest_addr < MASTER_ADDR_MIN or dest_addr > MASTER_ADDR_MAX:
        raise HeatmiserResponseError("Destination address out of valid range %i" % dest_addr)
    if dest_addr != destination:
        raise HeatmiserResponseError("Destination address incorrect %i" % dest_addr)
    if source_addr < SLAVE_ADDR_MIN or source_addr > SLAVE_ADDR_MAX:
        raise HeatmiserResponseError("Source address out of valid range %i" % source_addr)
    if source_addr != source:
        raise HeatmiserResponseError("Source address does not match %i" % source_addr)
            
def _check_response_frame_function(protocol, expected_function, data):
    """Takes frame and read or write bit is set correctly"""
    if protocol != HMV3_ID:
        raise ValueError("Protocol unknown")

    func_code = data[FR_FUNC_CODE]

    if func_code != FUNC_WRITE and func_code != FUNC_READ:
        raise HeatmiserResponseError("Unknown function    code: %i" %(func_code))
    if func_code != expected_function:
        raise HeatmiserResponseError("Function    code was not as expected: %i" %(func_code))
        
def verify_write_ack(protocol, source, destination, data):
    """Verifies message response to write is correct"""
    return verify_response(protocol, source, destination, FUNC_WRITE, DONT_CARE_LENGTH, data)
 
def verify_response(protocol, source, destination, expected_function, expected_length, data):
    """Verifies response frame appears legal"""
    try:
        # check CRC
        _check_frame_crc(protocol, data)
        # check length
        _check_response_frame_length(protocol, data, expected_length)
        # check addresses
        _check_response_frame_addresses(protocol, source, destination, data)
        # check function
        _check_response_frame_function(protocol, expected_function, data)
    except HeatmiserResponseError as err:
        logging.warning("C%s Invalid Response: %s: %s" %(source, str(err), data))
        raise
        
    ## missing check that it is valid for this type of controller. Use DCBUnique function not false.
    ## although if needed should be in devices and not in framing

# Believe this is known as CCITT (0xFFFF)
# This is the CRC function converted directly from the Heatmiser C code
# provided in their API
class crc16:
    """Computes CRC for Heatmiser Message"""
    LookupHigh = [
    0x00, 0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70,
    0x81, 0x91, 0xa1, 0xb1, 0xc1, 0xd1, 0xe1, 0xf1
    ]
    LookupLow = [
    0x00, 0x21, 0x42, 0x63, 0x84, 0xa5, 0xc6, 0xe7,
    0x08, 0x29, 0x4a, 0x6b, 0x8c, 0xad, 0xce, 0xef
    ]
    def __init__(self):
        self.high = BYTEMASK
        self.low = BYTEMASK

    def _update_4_bits(self, val):
        # Step one, extract the Most significant 4 bits of the CRC register
        #print "val is %d" %(val)
        t = self.high>>4
        #print "t is %d" %(t)

        # XOR in the Message Data into the extracted bits
        t = t^val
        #print "t is %d" %(t)

        # Shift the CRC Register left 4 bits
        self.high = (self.high << 4)|(self.low>>4)
        self.high = self.high & BYTEMASK # force char
        self.low = self.low <<4
        self.low = self.low & BYTEMASK # force char

        # Do the table lookups and XOR the result into the CRC tables
        #print "t for lookup is %d" %(t)
        self.high = self.high ^ self.LookupHigh[t]
        self.high = self.high & BYTEMASK # force char
        self.low = self.low ^ self.LookupLow[t]
        self.low = self.low & BYTEMASK # force char
        #print "high is %d Low is %d" %(self.high, self.low)

    def _crc16_update(self, val):
        self._update_4_bits(val>>4) # High nibble first
        self._update_4_bits(val & 0x0f) # Low nibble

    def run(self, message):
        """Calculates a CRC"""
        for c in message:
            #print c
            self._crc16_update(c)
        #print "CRC is Low %d High    %d" %(self.low, self.high)
        return [self.low, self.high]
