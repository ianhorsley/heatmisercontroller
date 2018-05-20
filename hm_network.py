#
# Ian Horsley 2018

#
# hmNetwork Class and helper functions
# handles serial connection and basic framing for the heatmiser protocol
# also loads heatmiser contollers

# Assume Python 2.7.x
#
import serial
import time
import os
from datetime import datetime
import logging

# Import our own stuff
from hm_controller import *
from stats_defn import *
from hm_constants import *
from comms_settings import *

class hmResponseError(RuntimeError):
    pass
    
def retryer(max_retries=3):
  def wraps(func):

      def inner(*args, **kwargs):
          for i in range(max_retries):
              try:    
                  result = func(*args, **kwargs)
              except hmResponseError as e:
                  logging.warn("Gen retrying due to %s"%str(e))
                  lasterror = e
                  continue
              else:
                  return result
          else:
              raise ValueError("Failed after %i retries on %s"%(max_retries,str(lasterror))) 
      return inner
  return wraps
    
class hmNetwork:

  def __init__(self):
  
    #setattr(self,"All",hmController(self,BROADCAST_ADDR,DEFAULT_PROTOCOL,"All","Broadcast to All",False,DEFAULT_PROG_MODE))
    setattr(self,"All",hmBroadcastController(self,"All","Broadcast to All"))
    
    self.current = self.All
    
    self.serport = serial.Serial()
    self.serport.port = COM_PORT
    self.serport.baudrate = COM_BAUD
    self.serport.bytesize = COM_SIZE
    self.serport.parity = COM_PARITY
    self.serport.stopbits = COM_STOP
    self.serport.timeout = COM_TIMEOUT
    self.serport.write_timeout = COM_TIMEOUT
    
    self.lastsendtime = None
    self.creationtime = time.time()
    
    self.lastreceivetime = time.time() - COM_BUS_RESET_TIME # so that system will get on with sending straight away
    
    self.write_max_retries = 3
    self.read_max_retries = 3
    
### low level serial commands

  def connect(self):
    if not self.serport.isOpen():
      try:
        self.serport.open()
      except serial.SerialException as e:
        logging.error("Could not open serial port %s: %s" % (self.serport.portstr, e))
        raise

      logging.info("Gen %s port opened"% (self.serport.portstr))
      logging.debug("Gen %s baud, %s bit, %s parity, with %s stopbits, timeout %s seconds" % (self.serport.baudrate, self.serport.bytesize, self.serport.parity, self.serport.stopbits, self.serport.timeout))
    else:
      logging.warn("Gen serial port was already open")
    
  def disconnect(self):
    if self.serport.isOpen():
      self.serport.close() # close port
      logging.info("Gen serial port closed")
    else:
      logging.warn("Gen serial port was already closed")
      
  def _hmSendMsg(self, message) :
      if not self.serport.isOpen():
        self.connect()

      #check time since last received to make sure bus has settled.
      waittime = COM_BUS_RESET_TIME - (time.time() - self.lastreceivetime)
      if waittime > 0:
        logging.debug("Gen waiting before sending %.2f"% ( waittime ))
        time.sleep(waittime)
      
      # http://stackoverflow.com/questions/180606/how-do-i-convert-a-list-of-ascii-values-to-a-string-in-python
      string = ''.join(map(chr,message))

      try:
        written = self.serport.write(string)  # Write a string
      except serial.SerialTimeoutException as e:
        self.serport.close() #need to close so that isOpen works correctly.
        logging.warning("Write timeout error: %s, sending %s" % (e, ', '.join(str(x) for x in message)))
        raise
      except serial.SerialException as e:
        self.serport.close() #need to close so that isOpen works correctly.
        logging.warning("Write error: %s, sending %s" % (e,  ', '.join(str(x) for x in message)))
      else:
        self.lastsendtime = time.strftime("%d %b %Y %H:%M:%S +0000", time.localtime(time.time())) #timezone is wrong
        logging.debug("Gen sent %s",', '.join(str(x) for x in message))

  def _hmClearInputBuffer(self):
    #clears input buffer
    #use after CRC check wrong encase more data was sent than expected.
  
    time.sleep(1) #wait a second to ensure slave finished sending
    self.serport.reset_input_buffer() #reset input buffer and dump any contents
    logging.warning("%s : Input buffer cleared" % (self.lastsendtime))
          
  def _hmRecieveMsg(self, source, length = MAX_FRAME_RESP_LENGTH) :
      # Listen for a reply
      if not self.serport.isOpen():
        self.connect()
      logging.debug("C%d listening for %d"%(source, length))
      
      try:
        byteread = self.serport.read(length)
      except serial.SerialException as e:
        #There is no new data from serial port (or port missing) (Doesn't include no response from stat)
        logging.warning("C%d : Serial port error: %s" % ( source, str(e)))
        self.serport.close()
        raise
      #except TypeError as e:
      #  #Disconnect of USB->UART occured
      #  self.port.close()
      #  raise#hmSerialError("Serial port closed" + str(e))
      else:
        self.lastreceivetime = time.time()
        data = []

        if (len(byteread)) == 0:
          logging.warning("C%d : No response" % (source))
          raise hmResponseError("Zero Length Response (Duplicate?)")

        #Now try converting it back to array
        data = data + (map(ord,byteread))
        logging.debug("Gen received %s",', '.join(str(x) for x in data))

        return data

### stat list setup
      
  def setStatList(self, list):
    self.statlist = list
    self.statnum = len(self.statlist)

    self.controllers = []
    for stat in list:
      if hasattr(self,stat[SL_SHORT_NAME]):
        print "error duplicate stat short name"
      else:
        setattr(self,stat[SL_SHORT_NAME],hmController(self,stat[SL_ADDR],stat[SL_PROTOCOL],stat[SL_SHORT_NAME],stat[SL_LONG_NAME],stat[SL_EXPECTED_TYPE],stat[SL_MODE]))
        self.controllers.append(getattr(self,stat[SL_SHORT_NAME]))

    self.current = self.controllers[0]
  
  def getStatAddress(self,shortname):
    if isinstance(shortname,basestring):
      #matches = [x for x in self.statlist if x[SL_SHORT_NAME] == shortname]
      shorts = [row[SL_SHORT_NAME] for row in self.statlist]
      
      return self.statlist[shorts.index(shortname)][SL_ADDR]
    else:
      return shortname

  def setCurrentControllerByName(self,name):
    self.current = getattr(self,name)
    
  def setCurrentControllerByIndex(self,index):
    self.current = self.controllers[index]
    
  def controllerByName(self,name):
    return getattr(self,name)

### low level framing functions
      
  def _hmFormReadFrame(self, destination, protocol, source, start, length) :
    return self._hmFormFrame(destination, protocol, source, FUNC_READ, start, length, [])
  
  # TODO check master address is in legal range
  def _hmFormFrame(self, destination, protocol, source, function, start, length, payload) :
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

  def _mhCheckFrameCRC(self, protocol, controller, data):
    datalength = len(data)
    
    if protocol != HMV3_ID:
      raise ValueError("Protocol unknown")
    if datalength < 2 :
      logging.warning("C%s : No CRC: %s " % (controller, data))
      raise hmResponseError("No CRC")

    checksum = data[len(data)-2:]
    rxmsg = data[:len(data)-2]
    
    crc = crc16() # Initialises the CRC
    expectedchecksum = crc.run(rxmsg)
    if expectedchecksum != checksum:
      logging.warning("C%s : Incorrect CRC: %s %s " % (controller, data, expectedchecksum))
      self._hmClearInputBuffer()
      raise hmResponseError("CRC is incorrect")      
  
  def _mhCheckFrameLength(self, protocol, data, expectedLength):
  
    if protocol != HMV3_ID:
      raise ValueError("Protocol unknown")

    if (len(data) < MIN_FRAME_RESP_LENGTH):
      logging.warning("Gen Response too short length: %s %s" % (len(data), frame_len))
      raise hmResponseError("Response length too short")

    frame_len_l = data[FR_LEN_LOW]
    frame_len_h = data[FR_LEN_HIGH]
    frame_len = (frame_len_h << 8) | frame_len_l
    func_code = data[FR_FUNC_CODE]
    
    if (len(data) != frame_len):
      logging.warning("Gen Frame length mismatch against header: %s %s" % (len(data), frame_len))
      raise hmResponseError("Response length doesn't match header")

    if (expectedLength != RW_LENGTH_ALL and func_code == FUNC_READ and frame_len != MIN_FRAME_READ_RESP_LENGTH + expectedLength ):
      # Read response length is wrong
      logging.warning("Gen response length %s not EXPECTED value %s + %s given request" % (frame_len, MIN_FRAME_READ_RESP_LENGTH, expectedLength ))
      raise hmResponseError("Response length unexpected")

    if (func_code == FUNC_WRITE and frame_len != FRAME_WRITE_RESP_LENGTH):
      # Reply to Write is always 7 long
      logging.warning("%s : Controller %s : Incorrect length: %s" % (self.lastsendtime, loop, frame_len))
      raise hmResponseError("Response length incorrect for write reponse")
        
  def _mhCheckFrameAddresses(self, protocol, source, data):
  
    if protocol != HMV3_ID:
      raise ValueError("Protocol unknown")
      
    dest_addr = data[FR_DEST_ADDR]        
    source_addr = data[FR_SOURCE_ADDR]
    func_code = data[FR_FUNC_CODE]

    if (dest_addr != 129 and dest_addr != 160):
      logging.warning("C%s : Illegal Dest Addr: %s" % (source, dest_addr))
      raise hmResponseError("dest_addr is ILLEGAL")

    if (dest_addr != MY_MASTER_ADDR):
      logging.warning("C%s : Incorrect Dest Addr: %s" % (source, dest_addr))
      raise hmResponseError("dest_addr is INCORRECT")

    if (source_addr < 1 or source_addr > 32):
      logging.warning("C%s : Illegal Src Addr: %s" % (source, source_addr))
      raise hmResponseError("source_addr is ILLEGAL")

    if (source_addr != source):
      logging.warning("C%s : Incorrect Src Addr: %s" % (source, source_addr))
      raise hmResponseError("source addr is INCORRECT")
        
  def _mhCheckFrameFunc(self, protocol, expectedFunction, data):
  
    if protocol != HMV3_ID:
      raise ValueError("Protocol unknown")

    func_code = data[FR_FUNC_CODE]

    if (func_code != FUNC_WRITE and func_code != FUNC_READ):
      logging.warning("%s : Controller %s : Unknown Func Code: %s" % (self.lastsendtime, loop, func_code))
      raise hmResponseError("Func Code is UNKNWON")

    if (func_code != expectedFunction):
      logging.warning("%s : Controller %s : Unexpected Func Code: %s" % (self.lastsendtime, loop, func_code))
      raise hmResponseError("Func Code is UNEXPECTED")

### protocol functions
        
  def _hmVerifyWriteAck(self, protocol, source, data) :
    """Verifies message response to write is correct"""
    return self._hmVerifyResponse(protocol, source, FUNC_WRITE, DONT_CARE_LENGTH, data)
   
  def _hmVerifyResponse(self, protocol, source, expectedFunction, expectedLength, data) :
    """Verifies message appears legal"""
    # check CRC
    self._mhCheckFrameCRC(protocol, source, data)
    # check length
    self._mhCheckFrameLength(protocol, data, expectedLength)
    # check addresses
    self._mhCheckFrameAddresses(protocol, source, data)
    # check function
    self._mhCheckFrameFunc(protocol, expectedFunction, data)
    
    ## missing check that it is valid for this type of controller. Use DCBUnique function not false.
  
  @retryer(max_retries = 3)
  def hmWriteToController(self, network_address, protocol, dcb_address, length, payload):

      msg = self._hmFormFrame(network_address, protocol, MY_MASTER_ADDR, FUNC_WRITE, dcb_address, length, payload)
      
      try:
        self._hmSendMsg(msg)
      except Exception as e:
        logging.warn("C%i writing to address, no message sent"%(network_address))
        raise
      else:
        logging.debug("C%i written to address %i length %i payload %s"%(network_address,dcb_address, length, ', '.join(str(x) for x in payload)))
        if network_address == BROADCAST_ADDR:
          self.lastreceivetime = time.time() + COM_SEND_MIN_TIME - COM_BUS_RESET_TIME # if broadcasting force it to wait longer until next send
        else:
          response = self._hmRecieveMsg(network_address,FRAME_WRITE_RESP_LENGTH)
          self._hmVerifyWriteAck(protocol, network_address, response)
  
  @retryer(max_retries = 2)
  def hmReadFromController(self, network_address, protocol, dcb_start_address, expectedLength, readall = False):
      if readall:
        msg = self._hmFormReadFrame(network_address, protocol, MY_MASTER_ADDR, DCB_START, RW_LENGTH_ALL)
        logging.debug("C %i read request to address %i length %i"%(network_address,DCB_START, RW_LENGTH_ALL))
      else:
        msg = self._hmFormReadFrame(network_address, protocol, MY_MASTER_ADDR, dcb_start_address, expectedLength)
        logging.debug("C %i read request to address %i length %i"%(network_address,dcb_start_address, expectedLength))
      
      try:
        self._hmSendMsg(msg)
      except:
        logging.warn("C%i address, read message not sent"%(network_address))
        raise
      else:
        time1 = time.time()

        try:
          response = self._hmRecieveMsg(network_address,MIN_FRAME_READ_RESP_LENGTH + expectedLength)
        except:
          logging.warn("C%i read failed from address %i length %i"%(network_address,dcb_start_address, expectedLength))
          raise
        else:
          logging.debug("C%i read in %.2f s from address %i  length %i payload %s"%(network_address,time.time()-time1,dcb_start_address, expectedLength, ', '.join(str(x) for x in response)))
        
          self._hmVerifyResponse(protocol, network_address, FUNC_READ, expectedLength , response)
          return response[FR_CONTENTS:-CRC_LENGTH]

        
  def hmReadAllFromController(self, network_address, protocol, expectedLength):
      return self.hmReadFromController(network_address, protocol, DCB_START, expectedLength, True)

  def hmSetField(self, controller, protocol, fieldname,state) :
      #set a field to a state. Defined for single or double length fields
      fieldinfo = uniadd[fieldname]
      
      if not isinstance(state, (int, long)) or state < fieldinfo[UNIADD_RANGE][0] or state > fieldinfo[UNIADD_RANGE][1]:
        raise ValueError("hmSetField: invalid requested value")
      elif fieldinfo[UNIADD_LEN] != 1 and fieldinfo[UNIADD_LEN] != 2 :
        raise ValueError("hmSetField: field isn't single or dual")
      elif len(fieldinfo) < UNIADD_WRITE + 1 or fieldinfo[UNIADD_WRITE] != 'W':
        raise ValueError("hmSetField: field isn't writeable")
      
      network_address = self.getStatAddress(controller) #broken

      if network_address == BROADCAST_ADDR or protocol == HMV3_ID:
        if fieldinfo[UNIADD_LEN] == 1:
          payload = [state]
        else:
          pay_lo = (state & BYTEMASK)
          pay_hi = (state >> 8) & BYTEMASK
          payload = [pay_lo, pay_hi]
        try:
          self.hmWriteToController(network_address, protocol, fieldinfo[UNIADD_ADD], fieldinfo[UNIADD_LEN], payload)
        except:
          logging.info("C%i failed to set field %s to %i"%(network_address, fieldname.ljust(FIELD_NAME_LENGTH), state))
          raise
        else:
          logging.info("C%i set field %s to %i"%(network_address, fieldname.ljust(FIELD_NAME_LENGTH), state))
      else:
        raise ValueError("Un-supported protocol found %s" % protocol)

          
  def hmSetFields(self, controller,protocol,uniqueaddress,payload) :
      #set a field to a state. Defined for fields greater than 2 in length
      fieldinfo = uniadd[uniqueaddress]
      
      if len(payload) != fieldinfo[UNIADD_LEN]:
        raise ValueError("hmSetFields: invalid payload length")
      elif fieldinfo[UNIADD_LEN] <= 2:
        raise ValueError("hmSetFields: field isn't array")
      elif fieldinfo[UNIADD_WRITE] != 'W':
        raise ValueError("hmSetFields: field isn't writeable")
      self._checkPayloadValues(payload, fieldinfo[UNIADD_RANGE])
      
      ###could add payload padding
      
      #payloadgrouped=chunks(payload,len(fieldinfo[UNIADD_RANGE]))
      network_address = self.getStatAddress(controller)
      
      if network_address == BROADCAST_ADDR or protocol == HMV3_ID:
        try :
          self.hmWriteToController(network_address, protocol, fieldinfo[UNIADD_ADD], len(payload), payload)
        except:
          logging.debug("C%i failed to set field %s to %s"%(network_address, uniqueaddress.ljust(FIELD_NAME_LENGTH), ', '.join(str(x) for x in payload)))
          raise
        else:
          logging.info("C%i Set field %s to %s"%(network_address, uniqueaddress.ljust(FIELD_NAME_LENGTH), ', '.join(str(x) for x in payload)))
      else:
        raise ValueError("Un-supported protocol found %s" % protocol)

  def _checkPayloadValues(self, payload, ranges):
    #checks the payload matches the ranges if ranges are defined
    if ranges != []:
      for i, item in enumerate(payload):
        range = ranges[i % len(ranges)]
        if item < range[0] or item > range[1]:
          ValueError("hmSetFields: payload out of range")

  ## Shouldn't be here move to controllers
  def hmUpdateTime(self, controller) :
      """bla bla"""
      #protocol = HMV3_ID # TODO should look this up in statlist
      #if protocol == HMV3_ID:
      msgtime = time.time()
      msgtimet = time.localtime(msgtime)
      day  = int(time.strftime("%w", msgtimet))
      if (day == 0):
          day = 7		# Convert python day format to Heatmiser format
      hour = int(time.strftime("%H", msgtimet))
      mins = int(time.strftime("%M", msgtimet))
      secs = int(time.strftime("%S", msgtimet))
      if (secs == 61):
          secs = 60 # Need to do this as pyhton seconds can be  [0,61]
      print "%d %d:%d:%d" % (day, hour, mins, secs)
      payload = [day, hour, mins, secs]
          #msg = hmFormMsgCRC(destination, protocol, MY_MASTER_ADDR, FUNC_WRITE, CUR_TIME_ADDR, payload)
          #return self.hmWriteToController(controller, CUR_TIME_ADDR, 4, payload)
      #else:
      #    "Un-supported protocol found %s" % protocol
      #    assert 0, "Un-supported protocol found %s" % protocol
      #    return 0
      return self.hmSetFields(controller,'currenttime',payload)
      
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


    
### general functions
from logging.handlers import RotatingFileHandler

def initialize_logger(output_dir, screenlevel, debugLog = None):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
     
    # create console handler and set level to info
    handler = logging.StreamHandler()
    handler.setLevel(screenlevel)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # create error file handler and set level to error
    handler = logging.FileHandler(os.path.join(output_dir, "error.log"),"w", encoding=None, delay="true")
    handler.setLevel(logging.WARN)
    formatter = logging.Formatter("%(asctime)-15s %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    #a is append, w is write
    if debugLog != None:
      #create debug file handler and set level to debug
      handler = RotatingFileHandler(os.path.join(output_dir, "all.log"), mode='a', maxBytes=5*1024*1024, 
                                   backupCount=2, encoding=None, delay=0)
      #handler = logging.FileHandler(os.path.join(output_dir, "all.log"),"w", encoding=None, delay="true")
      handler.setLevel(logging.DEBUG)
      formatter = logging.Formatter("%(asctime)-15s %(levelname)s - %(message)s")
      handler.setFormatter(formatter)
      logger.addHandler(handler)