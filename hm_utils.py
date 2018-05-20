#
# Ian Horsley 2018

#
# Sets time and gets information on all controllers
#

# Assume Python 2.7.x
#
import serial
import time
import os
from datetime import datetime
import logging

# Import our own stuff
from stats_defn import *
from hm_constants import *
from comms_settings import *

class hmResponseError(RuntimeError):
    pass
class hmSerialError(RuntimeError):
    pass
class hmProtocolError(RuntimeError):
    #error for things not fixable by retrying
    #or if not fixed by retrying
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
              raise hmProtocolError("Failed after %i retries on %s"%(max_retries,str(lasterror))) 
      return inner
  return wraps
    
class hmNetwork:

  def __init__(self):
  
    setattr(self,"All",hmController(self,BROADCAST_ADDR,DEFAULT_PROTOCOL,"All","Broadcast to All",False,DEFAULT_PROG_MODE))
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

      logging.info("Gen %s port opened")
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
        logging.warning("C%s : Serial port error: %s" % ( source, str(e)))
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
          logging.warning("C%s : No response" % (self.lastsendtime, source))
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
      
  # TODO check master address is in legal range
  def _hmFormReadFrame(self, destination, protocol, source, start, length) :
    return self._hmFormFrame(destination, protocol, source, FUNC_READ, start, length, [])
  
  def _hmFormFrame(self, destination, protocol, source, function, start, length, payload) :
    """Forms a message payload, including CRC"""
    if protocol != HMV3_ID:
      raise hmProtocolError("Protocol unknown")
    start_low = (start & BYTEMASK)
    start_high = (start >> 8) & BYTEMASK
    length_low = (length & BYTEMASK)
    length_high = (length >> 8) & BYTEMASK
    payload_length = len(payload)
    frame_length = MIN_FRAME_SEND_LENGTH
    if function == FUNC_WRITE:
      if length != payload_length:
        raise hmProtocolError("Payload doesn't match length %s" % length)
      if length > MAX_PAYLOAD_SEND_LENGTH:
        raise hmProtocolError("Payload to long %s" % length)
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
      raise hmProtocolError("Protocol unknown")
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
      raise hmProtocolError("Protocol unknown")

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
      raise hmProtocolError("Protocol unknown")
      
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
      raise hmProtocolError("Protocol unknown")

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
        raise hmProtocolError("hmSetField: invalid requested value")
      elif fieldinfo[UNIADD_LEN] != 1 and fieldinfo[UNIADD_LEN] != 2 :
        raise hmProtocolError("hmSetField: field isn't single or dual")
      elif len(fieldinfo) < UNIADD_WRITE + 1 or fieldinfo[UNIADD_WRITE] != 'W':
        raise hmProtocolError("hmSetField: field isn't writeable")
      
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
        raise hmProtocolError("Un-supported protocol found %s" % protocol)

          
  def hmSetFields(self, controller,protocol,uniqueaddress,payload) :
      #set a field to a state. Defined for fields greater than 2 in length
      fieldinfo = uniadd[uniqueaddress]
      
      if len(payload) != fieldinfo[UNIADD_LEN]:
        raise hmProtocolError("hmSetFields: invalid payload length")
      elif fieldinfo[UNIADD_LEN] <= 2:
        raise hmProtocolError("hmSetFields: field isn't array")
      elif fieldinfo[UNIADD_WRITE] != 'W':
        raise hmProtocolError("hmSetFields: field isn't writeable")
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
        raise hmProtocolError("Un-supported protocol found %s" % protocol)

  def _checkPayloadValues(self, payload, ranges):
    #checks the payload matches the ranges if ranges are defined
    if ranges != []:
      for i, item in enumerate(payload):
        range = ranges[i % len(ranges)]
        if item < range[0] or item > range[1]:
          hmProtocolError("hmSetFields: payload out of range")
          
### Functions for setting specific states on controllers
    
  # def hmKeyLock_On(destination, serport) :
    # hmKeyLock(destination, KEY_LOCK_LOCK, serport)

  # def hmKeyLock_Off(destination, serport) :
    # hmKeyLock(destination, KEY_LOCK_UNLOCK, serport)

  # def hmKeyLock(destination, state, serport) :
      # """bla bla"""
      # protocol = HMV3_ID # TODO should look this up in statlist
      # if protocol == HMV3_ID:
          # payload = [state]
          # # TODO should not be necessary to pass in protocol as we can look that up in statlist
          # msg = hmFormMsgCRC(destination, protocol, MY_MASTER_ADDR, FUNC_WRITE, KEY_LOCK_ADDR, payload)
      # else:
          # "Un-supported protocol found %s" % protocol
          # assert 0, "Un-supported protocol found %s" % protocol
          # # TODO return error/exception

      # print msg
      # string = ''.join(map(chr,msg))

      # datal = hmSendMsg(serport, string)

      # if (hmVerifyMsgCRCOK(MY_MASTER_ADDR, protocol, destination, FUNC_WRITE, DONT_CARE_LENGTH, datal) == False):
          # print "OH DEAR BAD RESPONSE"
      # return 1

  def hmSetHolEnd(destination, enddatetime, serport) :
      """bla bla"""
      nowdatetime = datetime.now()
      print nowdatetime
      if enddatetime < nowdatetime:
          print "oh dear" # TODO
      duration = enddatetime - nowdatetime
      days = duration.days
      seconds = duration.seconds
      hours = seconds/(60*60)
      totalhours = days*24 + hours + 1
      print "Setting holiday to end in %d days %d hours or %d total_hours on %s, it is now %s" % (days, hours, totalhours, enddatetime, nowdatetime)
      hmSetHolHours(destination, totalhours, serport)

  def hmSetHolHours(self, controller, hours) :
      #sets holiday up for a defined number of hours
      return self.hmSetField(controller,'holidayhours',hours)
  
  def hmCancelHol(self, controller) :
      #cancels holiday mode
      return self.hmSetField(controller,'holidayhours',0)

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

class hmController:

  def __init__(self, network, address, protocol, short_name, long_name, model, mode):
    self.network = network
    self.address = address
    self.protocol = protocol
    self.expected_model = model
    self.expected_prog_mode = mode
    
    if model == PRT_E_MODEL:
      self.DCBmap = PRTEmap[mode]
    elif model == PRT_HW_MODEL:
      self.DCBmap = PRTHWmap[mode]
    elif model == False:
      self.DCBmap = STRAIGHTmap
    else:
      print "UNKNOWN MODEL"
      
    if self.DCBmap[0][1] != DCB_INVALID:
      self.DCBlength = self.DCBmap[0][0] - self.DCBmap[0][1] + 1
    elif self.DCBmap[1][1] != DCB_INVALID:
      self.DCBlength = self.DCBmap[1][0] - self.DCBmap[1][1] + 1
    else:
      print "DCB map length not found"
    
    self.name = short_name
    self.long_name = long_name
    
    self.floorlimiting = 0
    self.lastreadalltime = 0
    self.lastreadvarstime = 0 #time since last read things like temps and demand
    
    self.autoreadall = True
   
  def _checkpayload(self,data):  
    if len(data) == 0:
      print "OH DEAR NO DATA"
      return False
    else :
      payload_len_l = data[PL_LEN_LOW]
      payload_len_h = data[PL_LEN_HIGH]
      payload_len = (payload_len_h << 8) | payload_len_l
      model_code = data[PL_MODEL]
      prog_mode = data[PL_PROG_MODE]
        
      if payload_len != len(data):
        print "OH DEAR PAYLOAD LENGTH WRONG"
        return False
      elif model_code != self.expected_model:
        print "OH DEAR SENSOR TYPE WRONG"
        return False
      elif prog_mode != self.expected_prog_mode:
        print "OH DEAR PROG MODE WRONG"
        return False
        
    return True
  
  def _getDCBaddress(self, uniqueaddress):
    #get the DCB address for a controller from the unique address

    offset = DCB_INVALID
    for uniquemax, offsetsel in self.DCBmap:
      if uniqueaddress <= uniquemax:
        offset = offsetsel
    
    if offset != DCB_INVALID:
      return uniqueaddress-offset
    else:
      return False
      
  def getRawData(self, startfieldname = None, endfieldname = None):
    if startfieldname == None or endfieldname == None:
      return self.rawdata
    else:
      return self.rawdata[self._getDCBaddress(uniadd[startfieldname][UNIADD_ADD]):self._getDCBaddress(uniadd[endfieldname][UNIADD_ADD])]
  
  def hmReadAll(self):
    self.rawdata = self.network.hmReadAllFromController(self.address, self.protocol, self.DCBlength)
    logging.info("C%i Read all, %s"%(self.address, ', '.join(str(x) for x in self.rawdata)))
    self.lastreadalltime = time.time()
    self.lastreadvarstime = self.lastreadalltime
    self.lastreadtempstime = self.lastreadalltime
    self.lastreadtimetime = self.lastreadalltime
    self.procpayload()
    return self.rawdata
    
  def hmReadVariables(self):
    if not self._check_data_present():
      if self.autoreadall:
        self.hmReadAll()
        self.procpayload()
      
        if self.model == PRT_HW_MODEL:
          lastfield = 'hotwaterstate'
        else:
          lastfield = 'heatingstate'
      
        return self.getRawData('setroomtemp', 'holidayhours') + self.getRawData('tempholdmins', lastfield)
      else:
        raise hmProtocolError("Need to read all before reading subset")

    rawdata1 = self.hmReadFields('setroomtemp', 'holidayhours')
    #self.procpayload(rawdata1,'setroomtemp', 'holidayhours')
  
    if self.model == PRT_HW_MODEL:
      lastfield = 'hotwaterstate'
    else:
      lastfield = 'heatingstate'

    rawdata2 = self.hmReadFields('tempholdmins', lastfield)
    #self.procpayload(rawdata2,'tempholdmins', lastfield)
    
    #if len(rawdata1) > 0 and len(rawdata2) > 0:
    self.lastreadvarstime = time.time()
    self.lastreadtempstime = time.time()
    return rawdata1 + rawdata2
    
  def hmReadTempsandDemand(self):
    if not self._check_data_present():
      if self.autoreadall:
        self.hmReadAll()
        self.procpayload()
        if self.model == PRT_HW_MODEL:
          lastfield = 'hotwaterstate'
        else:
          lastfield = 'heatingstate'
        return self.getRawData('remoteairtemp', lastfield)
      else:
        raise hmProtocolError("Need to read all before reading subset")
  
    if self.model == PRT_HW_MODEL:
      lastfield = 'hotwaterstate'
    else:
      lastfield = 'heatingstate'

    rawdata = self.hmReadFields('remoteairtemp', lastfield)
    #self.procpayload(rawdata,'remoteairtemp', lastfield)

    if rawdata != None:
      self.lastreadtempstime = time.time()

    return rawdata
    
  def hmReadTime(self):
    rawdata = self.hmReadFields('currenttime', 'currenttime')
    self.lastreadtimetime = time.time()
    return rawdata

  def hmReadFields(self,firstfieldname,lastfieldname):
    firstfieldinfo = uniadd[firstfieldname]
    lastfieldinfo = uniadd[lastfieldname]

    startnormaldcb = self._getDCBaddress(firstfieldinfo[UNIADD_ADD])
    
    readlength = lastfieldinfo[UNIADD_ADD] - firstfieldinfo[UNIADD_ADD] + lastfieldinfo[UNIADD_LEN]

    try:
      rawdata = self.network.hmReadFromController(self.address, self.protocol, firstfieldinfo[UNIADD_ADD], readlength)
    except serial.SerialException as e:
      logging.warn("C%i Read failed of fields %s to %s, Serial Port error %s"%(self.address, firstfieldname.ljust(FIELD_NAME_LENGTH),lastfieldname.ljust(FIELD_NAME_LENGTH), str(e)))
      return None
    else:
      logging.info("C%i Read fields %s to %s, %s"%(self.address, firstfieldname.ljust(FIELD_NAME_LENGTH),lastfieldname.ljust(FIELD_NAME_LENGTH), ', '.join(str(x) for x in rawdata)))
    
      self.procpayload(rawdata,firstfieldname, lastfieldname)

      return rawdata
    
  def hmReadField(self,fieldname):
    fieldinfo = uniadd[fieldname]

    rawdata = self.network.hmReadFromController(self.address, self.protocol, fieldinfo[UNIADD_ADD], fieldinfo[UNIADD_LEN])
    
    if fieldinfo[UNIADD_LEN] == 1:
      value = rawdata[0]/fieldinfo[UNIADD_DIV]
    elif fieldinfo[UNIADD_LEN] == 2:
      val_high = rawdata[0]
      val_low  = rawdata[1]
      value = 1.0*(val_high*256 + val_low)/fieldinfo[UNIADD_DIV] #force float, although always returns integer temps.
    else:
      print "field not processed"
      value = False
      
    setattr(self, fieldname, value)
    logging.info("C%i Read field %s is %s"%(self.address, fieldname.ljust(FIELD_NAME_LENGTH), ', '.join(str(x) for x in rawdata)))

    return value

  def procpayload(self, rawdata = None, firstfieldadd = 0, lastfieldadd = MAX_UNIQUE_ADDRESS):
    if not self._check_data_present():
      if self.autoreadall:
        self.hmReadAll()
      else:
        raise hmProtocolError("Need to read all before reading processing payload")

    logging.debug("C%i Processing Payload"%(self.address) )
    
    if rawdata == None:
      rawdata = self.rawdata
    
    if isinstance(firstfieldadd, basestring):
      firstfieldadd = uniadd[firstfieldadd][UNIADD_ADD]  
    fullfirstdcbadd = self._getDCBaddress(firstfieldadd)
    if isinstance(lastfieldadd, basestring):
      lastfieldadd = uniadd[lastfieldadd][UNIADD_ADD]

    if firstfieldadd == 0 and lastfieldadd == MAX_UNIQUE_ADDRESS:
      if not self._checkpayload(rawdata): ###add errors to this module
        raise hmResponseError("Payload Faulty")
    ###add payload length check if not full length data
    
    #take model from full rawdata
    model = self.rawdata[UNIQUE_ADD_MODEL]
  
    for attrname, values in uniadd.iteritems():
      uniqueaddress = values[UNIADD_ADD]
      if uniqueaddress >= firstfieldadd and uniqueaddress <= lastfieldadd:
        length = values[UNIADD_LEN]
        factor = values[UNIADD_DIV]
        range = values[UNIADD_RANGE]
        ###todo, add 7 day prog to getDCBaddress selection
        dcbadd = self._getDCBaddress(uniqueaddress)
        #todo, add range validation
        if dcbadd == DCB_INVALID:
          setattr(self, attrname, False)
        else:
          dcbadd -= fullfirstdcbadd #adjust for the start of the request
          if length == 1:
            setattr(self, attrname, rawdata[dcbadd]/factor)
          elif length == 2:
            val_high = rawdata[dcbadd]
            val_low  = rawdata[dcbadd+1]
            setattr(self, attrname, 1.0*(val_high*256 + val_low)/factor) #force float, although always returns integer temps.
          elif length == 4 or length == 12 or length == 16:
            setattr(self, attrname, rawdata[dcbadd:dcbadd+length])
          else:
            print "field length error"
            
    version_add = uniadd['version'][UNIADD_ADD]
    if self.model != PRT_HW_MODEL and version_add >= firstfieldadd and version_add <= lastfieldadd:
      dcbfieldnum = self._getDCBaddress(version_add)
      self.version = rawdata[dcbfieldnum] & 0x7f
      self.floorlimiting = rawdata[dcbfieldnum] >> 7
      self.hotwaterstate = False
    
    self.rawdata[fullfirstdcbadd:fullfirstdcbadd+len(rawdata)] = rawdata
    
    currenttime_add = uniadd['currenttime'][UNIADD_ADD]
    if currenttime_add >= firstfieldadd and currenttime_add <= lastfieldadd:
      self._checkcontrollertime(time.localtime(self.lastreadalltime))

  def _checkcontrollertime(self,checktime):       
    # Now do same sanity checking
    # Check the time is within range
    # If we only do this at say 1 am then there is no issues/complication of day wrap rounds
    # TODO only do once a day
    # currentday is numbered 1-7 for M-S
    # localday (pyhton) is numbered 0-6 for Sun-Sat
    localday = time.strftime("%w", checktime)
    
    if (int(localday) != int((self.currenttime[CURRENT_TIME_DAY]%7))):
        s= "%s : Controller %2d : Incorrect day : local is %s, sensor is %s" % (datetime.now().isoformat(), self.address, localday, currentday)

        # TODO ++ here
    remoteseconds = (((self.currenttime[CURRENT_TIME_HOUR] * 60) + self.currenttime[CURRENT_TIME_MIN]) * 60) + self.currenttime[CURRENT_TIME_SEC]

    nowhours = time.localtime(time.time()).tm_hour
    nowmins = time.localtime(time.time()).tm_min
    nowsecs = time.localtime(time.time()).tm_sec
    nowseconds = (((nowhours * 60) + nowmins) * 60) + nowsecs
    logging.debug("Time %d %d" % (remoteseconds, nowseconds))
    self.timeerr = nowseconds - remoteseconds
    if (abs(self.timeerr) > TIME_ERR_LIMIT):
        logging.warn("%s : Controller %2d : Time Error : Greater than %d local is %s, sensor is %s" % (datetime.now().isoformat(), self.address, TIME_ERR_LIMIT, nowseconds, remoteseconds))

  TEMP_STATE_OFF = 0  #thermostat display is off and frost protection disabled
  TEMP_STATE_OFF_FROST = 1 #thermostat display is off and frost protection enabled
  TEMP_STATE_FROST = 2 #frost protection enabled indefinitely
  TEMP_STATE_HOLIDAY = 3 #holiday mode, frost protection for a period
  TEMP_STATE_HELD = 4 #temperature held for a number of hours
  TEMP_STATE_OVERRIDDEN = 5 #temperature overridden until next program time
  TEMP_STATE_PROGRAM = 6 #following program
  
  def getTempState(self):
    if not self._check_data_present() or not self._check_data_current():
      if self.autoreadall:
        self.hmReadAll()
        self.procpayload()
      else:
        raise hmProtocolError("Need to read all before getting temp state")
        
    if not self._check_vars_current():
      if self.autoreadall:
        self.hmReadVariables()
      else:
        raise hmProtocolError("Vars to old to get temp state")
    
    if self.onoff == WRITE_ONOFF_OFF and self.frostprot == READ_FROST_PROT_OFF:
      return self.TEMP_STATE_OFF
    elif self.onoff == WRITE_ONOFF_OFF and self.frostprot == READ_FROST_PROT_ON:
      return self.TEMP_STATE_OFF_FROST
    elif self.holidayhours != 0:
      return self.TEMP_STATE_HOLIDAY
    elif self.runmode == WRITE_RUNMODE_FROST:
      return self.TEMP_STATE_FROST
    elif self.tempholdmins != 0:
      return self.TEMP_STATE_HELD
    else:
    
      if not self._check_time_current():
        currenttime = self.hmReadTime()
        self._checkcontrollertime(time.localtime(self.lastreadtimetime))
      
      locatimenow = self.localtimearray()
      scheduletarget = self.getCurrentScheduleEntry(locatimenow)

      if scheduletarget[self.SCH_ENT_TEMP] != self.setroomtemp:
        return self.TEMP_STATE_OVERRIDDEN
      else:
        return self.TEMP_STATE_PROGRAM
  
  def localtimearray(self):
    nowday = time.localtime(time.time()).tm_wday + 1
    nowhours = time.localtime(time.time()).tm_hour
    nowmins = time.localtime(time.time()).tm_min
    nowsecs = time.localtime(time.time()).tm_sec
    
    return [nowday, nowhours, nowmins, nowsecs]
  
  def getCurrentScheduleEntry(self,timearray):
    ####check time and vars current
    
    todayschedule = self._getHeatSchedule(timearray[CURRENT_TIME_DAY])
      
    scheduletarget = self._getCurrentEntryFromASchedule(todayschedule,timearray)
      
    if scheduletarget == None:
      yestschedule = self._getPreviousHeatSchedule(timearray)
      scheduletarget = self._getLastEntryFromASchedule(yestschedule)
      return [self._getPreviousDay(timearray)] + scheduletarget
    else:
      return [timearray[CURRENT_TIME_DAY]] + scheduletarget
  
  SCH_ENT_DAY = 0
  SCH_ENT_HOUR = 1
  SCH_ENT_MIN = 2
  SCH_ENT_TEMP = 3
  
  def getNextScheduleEntry(self,timearray):

    todayschedule = self._getHeatSchedule(timearray[CURRENT_TIME_DAY])
    
    scheduletarget = self._getNextEntryFromASchedule(todayschedule,timearray)
      
    if scheduletarget == None:
      tomschedule = self._getNextHeatSchedule(timearray)
      scheduletarget = self._getFirstEntryFromASchedule(tomschedule)
      return [self._getNextDay(timearray)] + scheduletarget
    else:
      return [timearray[CURRENT_TIME_DAY]] + scheduletarget

  def _getNextEntryFromASchedule(self,schedule,timearray):
    hour_minutes = 60
  
    scheduletarget = None
    dayminutes = timearray[CURRENT_TIME_HOUR] * hour_minutes + timearray[CURRENT_TIME_MIN]

    for i in self._reversechunks(schedule,3):
      if dayminutes < i[HEAT_MAP_HOUR] * hour_minutes + i[HEAT_MAP_MIN] and i[HEAT_MAP_HOUR] != HOUR_UNUSED:
        scheduletarget = i
    
    return scheduletarget
    
  def _getCurrentEntryFromASchedule(self,schedule,timearray):
    hour_minutes = 60
  
    scheduletarget = None
    dayminutes = timearray[CURRENT_TIME_HOUR] * hour_minutes + timearray[CURRENT_TIME_MIN]
    
    for i in self._chunks(schedule,3):
      if dayminutes >= i[HEAT_MAP_HOUR] * hour_minutes + i[HEAT_MAP_MIN] and i[HEAT_MAP_HOUR] != HOUR_UNUSED:
        scheduletarget = i
    
    return scheduletarget

  def _getFirstEntryFromASchedule(self,schedule):
    #gets first schedule entry if valid (not 24)
    firstentry = self._chunks(schedule,3).next()
    if firstentry[HEAT_MAP_HOUR] != HOUR_UNUSED:
      return firstentry
    else:
      return None

  def _getLastEntryFromASchedule(self,schedule):
    #gets last valid schedule entry (not 24)
    scheduletarget = None
    for i in self._reversechunks(schedule,3):
          if i[HEAT_MAP_HOUR] != HOUR_UNUSED:
            scheduletarget = i
            break
    
    return scheduletarget
  
  def _getPreviousDay(self, timearray):
    ##bugged
    if timearray[CURRENT_TIME_DAY] > 1:
      day = timearray[CURRENT_TIME_DAY] - 1
    else:
      day = 7
    return day
  
  def _getNextDay(self,timearray):
    ##bugged
    if timearray[CURRENT_TIME_DAY] < 7:
      day = timearray[CURRENT_TIME_DAY] + 1
    else:
      day = 7
    return day
  
  def _getPreviousHeatSchedule(self,timearray):
    return self._getHeatSchedule(self._getPreviousDay(timearray))
  
  def _getNextHeatSchedule(self,timearray):
    return self._getHeatSchedule(self._getNextDay(timearray))
    
  def _getHeatSchedule(self, day):
    if self.programmode == READ_PROGRAM_MODE_5_2:
      if day == 6 or day == 7:
        return self.wend_heat
      elif day >= 1 and day <= 5:
        return self.wday_heat
      else:
        logging.error("Gen day not recognised")
    elif self.programmode == READ_PROGRAM_MODE_7:
      if day == 1:
        return self.mon_heat
      elif day == 2:
        return self.tues_heat
      elif day == 3:
        return self.wed_heat
      elif day == 4:
        return self.thurs_heat
      elif day == 5:
        return self.fri_heat
      elif day == 6:
        return self.sat_heat
      elif day == 7:
        return self.sun_heat
      else:
        logging.error("Gen day not recognised")
    
    else:
      logging.error("Gen program mode not recognised")
    
  
#### External functions for printing data
  def printTarget(self):
      
    current_state = self.getTempState()
    
    if current_state == self.TEMP_STATE_OFF:
      return "controller off without frost protection"
    elif current_state == self.TEMP_STATE_OFF_FROST:
      return "controller off"
    elif current_state == self.TEMP_STATE_HOLIDAY:
      return "controller on holiday for %i hours" % self.holidayhours
    elif current_state == self.TEMP_STATE_FROST:
      return "controller in frost mode"
    elif current_state == self.TEMP_STATE_HELD:
      return "temp held for %i mins at %i"%(self.tempholdmins, self.setroomtemp)
    elif current_state == self.TEMP_STATE_OVERRIDDEN:
      locatimenow = self.localtimearray()
      nexttarget = self.getNextScheduleEntry(locatimenow)
      return "temp overridden to %0.1f until %02d:%02d" % (self.setroomtemp, nexttarget[1], nexttarget[2])
    elif current_state == self.TEMP_STATE_PROGRAM:
      locatimenow = self.localtimearray()
      nexttarget = self.getNextScheduleEntry(locatimenow)
      return "temp set to %0.1f until %02d:%02d" % (self.setroomtemp, nexttarget[1], nexttarget[2])

  def display_heating_schedule(self):
    print "Heating Schedule"
    if self.programmode == READ_PROGRAM_MODE_5_2:
      print "Weekdays ",
      self._print_heat_schedule(self.wday_heat)
      print "Weekends ",
      self._print_heat_schedule(self.wend_heat)
    if self.programmode == READ_PROGRAM_MODE_7:
      print "Monday    ",
      self._print_heat_schedule(self.mon_heat)
      print "Tuesday   ",
      self._print_heat_schedule(self.tues_heat)
      print "Wednesday ",
      self._print_heat_schedule(self.wed_heat)
      print "Thursday  ",
      self._print_heat_schedule(self.thurs_heat)
      print "Friday    ",
      self._print_heat_schedule(self.fri_heat)
      print "Saturday  ",
      self._print_heat_schedule(self.sat_heat)
      print "Sunday    ",
      self._print_heat_schedule(self.sun_heat)
    
  def _chunks(self, l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]
        
  def _reversechunks(self, l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(len(l)-n, -1, -n):
        yield l[i:i + n]
  
  def _check_data_current(self):
    #check general data is current
    current = time.time() - self.lastreadalltime < 60 * 60 * 8
    if not current:
      logging.warning("C%i full data too old"%(self.address))
    return current

  def _check_time_current(self):
    #check time is current. If has been checked in the last 2 hours assume current 
    current = time.time() - self.lastreadtimetime < 60 * 60 * 2
    if not current:
      print "data too old to process"
    return current
    
  def _check_vars_current(self):
    #check variables, such as target temp, hold, onoff, current
    current = time.time() - self.lastreadvarstime < 60
    if not current:
      logging.warning("C%i variable data too old"%(self.address))
    return current
    
  def _check_temps_current(self):
    #check temp and demand current
    current = time.time() - self.lastreadtempstime < 10
    if not current:
      print "data too old to process"
    return current
    
  def _check_data_present(self):
    current = self.lastreadalltime != 0
    if not current:
      logging.warning("C%i full data not avaliable"%(self.address))
    return current
    
  def _print_heat_schedule(self,data):
    if len(data) != 12:
      logging.warning("Gen heat sch data not valid")
      return False
    
    tempstr = ''
    for set in self._chunks(data,3):
      if set[HEAT_MAP_HOUR] != HOUR_UNUSED:
        tempstr += "%02d:%02d at %02iC " % (set[HEAT_MAP_HOUR],set[HEAT_MAP_MIN],set[HEAT_MAP_TEMP])
        
    print tempstr
    logging.info(tempstr)
      
  def display_water_schedule(self):
    
    if self.model == PRT_HW_MODEL:
      print "Hot Water Schedule"
      if self.programmode == READ_PROGRAM_MODE_5_2:
        print "Weekdays"
        self._print_water_schedule(self.wday_water)
        print "Weekends"
        self._print_water_schedule(self.wend_water)
      if self.programmode == READ_PROGRAM_MODE_7:
        print "Monday    ",
        self._print_water_schedule(self.mon_water)
        print "Tuesday   ",
        self._print_water_schedule(self.tues_water)
        print "Wednesday ",
        self._print_water_schedule(self.wed_water)
        print "Thursday  ",
        self._print_water_schedule(self.thurs_water)
        print "Friday    ",
        self._print_water_schedule(self.fri_water)
        print "Saturday  ",
        self._print_water_schedule(self.sat_water)
        print "Sunday    ",
        self._print_water_schedule(self.sun_water)
        
  def _print_water_schedule(self,data):
    if len(data) != 16:
      logging.warning("Gen water sch data not valid")
      return False
    toggle = True
    count = 1
    
    tempstr = ''
    for set in self._chunks(data,2):
      if set[0] != HOUR_UNUSED:
        if toggle:
          tempstr += "Time %i On at %02d:%02d " % (count,set[0],set[1])
        else:
          tempstr += "Off at %02d:%02d, " % (set[0],set[1])
          count=count+1
        toggle = not toggle
        
    print tempstr
    logging.info(tempstr)
        
#### External functions for getting data

  def getAirSensorType(self):
    if not self._check_data_present():
      return False

    if self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_FLOOR:
      return 1
    elif self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_FLOOR:
      return 2
    else:
      return 0
      
  def getAirTemp(self):
    if not self._check_temps_current():
      return False
    
    if self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_FLOOR:
      return self.airtemp
    elif self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_FLOOR:
      return self.remoteairtemp
    else:
      return False
     
#### External functions for setting data

  def setHeatingSchedule(self, day, schedule):
    schedule += [HOUR_UNUSED,0,12] * ((uniadd[day][UNIADD_LEN] - len(schedule))/3)
    self.network.hmSetFields(self.address,self.protocol,day,schedule)
    
  def setWaterSchedule(self, day, schedule):
    if day == 'all':
      schedule += [HOUR_UNUSED,0] * ((uniadd['mon_water'][UNIADD_LEN] - len(schedule))/2)
      self.network.hmSetFields(self.address,self.protocol,'mon_water',schedule)
      self.network.hmSetFields(self.address,self.protocol,'tues_water',schedule)
      self.network.hmSetFields(self.address,self.protocol,'wed_water',schedule)
      self.network.hmSetFields(self.address,self.protocol,'thurs_water',schedule)
      self.network.hmSetFields(self.address,self.protocol,'fri_water',schedule)
      self.network.hmSetFields(self.address,self.protocol,'sat_water',schedule)
      self.network.hmSetFields(self.address,self.protocol,'sun_water',schedule)
    else:
      schedule += [HOUR_UNUSED,0] * ((uniadd[day][UNIADD_LEN] - len(schedule))/2)
      self.network.hmSetFields(self.address,self.protocol,day,schedule)
      
#general field setting

  def setField(self,field,value):
    return self.network.hmSetField(self.address,self.protocol,field,value)

#overriding      
      
  def setTemp(self, temp) :
    #sets the temperature demand overriding the program. Believe it returns at next prog change.
  
    #check hold temp not applied
    if self.hmReadField('tempholdmins') == 0:
      return self.network.hmSetField(self.address,self.protocol,'setroomtemp',temp)
    else:
      logging.warn("%i address, temp hold applied so won't set temp"%(self.address))

  def releaseTemp(self) :
    #release SetTemp back to the program, but only if temp isn't held
    
    if self.hmReadField('tempholdmins') == 0:
      return self.network.hmSetField(self.address,self.protocol,'tempholdmins',0)
    else:
      logging.warn("%i address, temp hold applied so won't remove set temp"%(self.address))     

  def holdTemp(self, minutes, temp) :
    #sets the temperature demand overrding the program for a set time. Believe it then returns to program.
    self.network.hmSetField(self.address,self.protocol,'setroomtemp',temp)
    return self.network.hmSetField(self.address,self.protocol,'tempholdmins',minutes)
    #didn't stay on if did minutes followed by temp.
    
  def releaseHoldTemp(self) :
    #release SetTemp or HoldTemp back to the program
    return self.network.hmSetField(self.address,self.protocol,'tempholdmins',0)

#onoffs

  def setOn(self):
    return self.network.hmSetField(self.address,self.protocol,'onoff',WRITE_ONOFF_ON)
  def setOff(self):
    return self.network.hmSetField(self.address,self.protocol,'onoff',WRITE_ONOFF_OFF)
    
  def setHeat(self):
    return self.network.hmSetField(self.address,self.protocol,'runmode',WRITE_RUNMODE_HEATING)
  def setFrost(self):
    return self.network.hmSetField(self.address,self.protocol,'runmode',WRITE_RUNMODE_FROST)
    
  def setLock(self):
    return self.network.hmSetField(self.address,self.protocol,'keylock',WRITE_KEYLOCK_ON)
  def setUnlock(self):
    return self.network.hmSetField(self.address,self.protocol,'keylock',WRITE_KEYLOCK_OFF)
  
#other
#set floor limit
#set holiday
    
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