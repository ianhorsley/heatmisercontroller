
import logging

from hm_constants import *
from .exceptions import hmResponseError, hmResponseErrorCRC

### low level framing functions
    
def _hmFormReadFrame(destination, protocol, source, start, length) :
  return _hmFormFrame(destination, protocol, source, FUNC_READ, start, length, [])

# TODO check master address is in legal range
def _hmFormFrame(destination, protocol, source, function, start, length, payload) :
  """Forms a message payload, including CRC"""
  if protocol != HMV3_ID:
    raise ValueError("Protocol unknown")
  start_low = (start & BYTEMASK)
  start_high = (start >> 8) & BYTEMASK
  length_low = (length & BYTEMASK)
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

def _hmCheckFrameCRC(protocol, data):
  """Takes frame with CRC and checks it is valid"""
  datalength = len(data)
  
  if protocol != HMV3_ID:
    raise ValueError("Protocol unknown")
  if datalength < 2 :
    raise hmResponseError("No CRC")

  checksum = data[len(data)-2:]
  rxmsg = data[:len(data)-2]
  
  crc = crc16() # Initialises the CRC
  expectedchecksum = crc.run(rxmsg)
  if expectedchecksum != checksum:
    raise hmResponseErrorCRC("CRC is incorrect")      

def _hmCheckResponseFrameLength(protocol, data, expectedLength):
  """Takes frame and checks length, must be a receive frame"""
  if protocol != HMV3_ID:
    raise ValueError("Protocol unknown")

  if (len(data) < MIN_FRAME_RESP_LENGTH):
    raise hmResponseError("Response length too short: %s %s"% (len(data), MIN_FRAME_RESP_LENGTH))

  frame_len_l = data[FR_LEN_LOW]
  frame_len_h = data[FR_LEN_HIGH]
  frame_len = (frame_len_h << 8) | frame_len_l
  func_code = data[FR_FUNC_CODE]
  
  if (len(data) != frame_len):
    raise hmResponseError("Frame length does not match header: %s %s" % (len(data), frame_len))

  if (expectedLength != RW_LENGTH_ALL and func_code == FUNC_READ and frame_len != MIN_FRAME_READ_RESP_LENGTH + expectedLength ):
    # Read response length is wrong
    raise hmResponseError("Response length %s not EXPECTED value %s + %s given read request" % (frame_len, MIN_FRAME_READ_RESP_LENGTH, expectedLength ))
  if (func_code == FUNC_WRITE and frame_len != FRAME_WRITE_RESP_LENGTH):
    # Reply to Write is always 7 long
    raise hmResponseError("Response length %s not EXPECTED value %s given write request" % (frame_len, FRAME_WRITE_RESP_LENGTH ))
      
def _hmCheckResponseFrameAddresses(protocol, source, destination, data):

  if protocol != HMV3_ID:
    raise ValueError("Protocol unknown")
    
  dest_addr = data[FR_DEST_ADDR]        
  source_addr = data[FR_SOURCE_ADDR]

  if (dest_addr < MASTER_ADDR_MIN or dest_addr > MASTER_ADDR_MAX):
    raise hmResponseError("Destination address out of valid range %i" % dest_addr)
  if (dest_addr != destination):
    raise hmResponseError("Destination address incorrect %i" % dest_addr)
  if (source_addr < SLAVE_ADDR_MIN or source_addr > SLAVE_ADDR_MAX):
    raise hmResponseError("Source address out of valid range %i" % source_addr)
  if (source_addr != source):
    raise hmResponseError("Source address does not match %i" % source_addr)
      
def _hmCheckResponseFrameFunc(protocol, expectedFunction, data):

  if protocol != HMV3_ID:
    raise ValueError("Protocol unknown")

  func_code = data[FR_FUNC_CODE]

  if (func_code != FUNC_WRITE and func_code != FUNC_READ):
    raise hmResponseError("Unknown function  code: %i" % (func_code))
  if (func_code != expectedFunction):
    raise hmResponseError("Function  code was not as expected: %i" % (func_code))
    
def _hmVerifyWriteAck(protocol, source, destination, data) :
  """Verifies message response to write is correct"""
  return _hmVerifyResponse(protocol, source, destination, FUNC_WRITE, DONT_CARE_LENGTH, data)
 
def _hmVerifyResponse(protocol, source, destination, expectedFunction, expectedLength, data) :
  """Verifies response frame appears legal"""
  try:
    # check CRC
    _hmCheckFrameCRC(protocol, data)
    # check length
    _hmCheckResponseFrameLength(protocol, data, expectedLength)
    # check addresses
    _hmCheckResponseFrameAddresses(protocol, source, destination, data)
    # check function
    _hmCheckResponseFrameFunc(protocol, expectedFunction, data)
  except hmResponseError as e:
    logging.warning("C%s Invalid Response: %s: %s" % (source, str(e), data))
    raise
    
  ## missing check that it is valid for this type of controller. Use DCBUnique function not false.
  ## although if needed should be in devices and not in framing

# Believe this is known as CCITT (0xFFFF)
# This is the CRC function converted directly from the Heatmiser C code
# provided in their API
class crc16:
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

    def Update4Bits(self, val):
        # Step one, extract the Most significant 4 bits of the CRC register
        #print "val is %d" % (val)
        t = self.high>>4
        #print "t is %d" % (t)

        # XOR in the Message Data into the extracted bits
        t = t^val
        #print "t is %d" % (t)

        # Shift the CRC Register left 4 bits
        self.high = (self.high << 4)|(self.low>>4)
        self.high = self.high & BYTEMASK    # force char
        self.low = self.low <<4
        self.low = self.low & BYTEMASK  # force char

        # Do the table lookups and XOR the result into the CRC tables
        #print "t for lookup is %d" % (t)
        self.high = self.high ^ self.LookupHigh[t]
        self.high = self.high & BYTEMASK    # force char
        self.low  = self.low  ^ self.LookupLow[t]
        self.low = self.low & BYTEMASK  # force char
        #print "high is %d Low is %d" % (self.high, self.low)

    def CRC16_Update(self, val):
        self.Update4Bits(val>>4) # High nibble first
        self.Update4Bits(val & 0x0f) # Low nibble

    def run(self, message):
        """Calculates a CRC"""
        for c in message:
            #print c
            self.CRC16_Update(c)
        #print "CRC is Low %d High  %d" % (self.low, self.high)
        return [self.low, self.high]
