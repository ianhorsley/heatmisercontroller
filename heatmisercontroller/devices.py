#
# Ian Horsley 2018

#
# hmController class
# handles all the DCB and data objects for each controller on the heatmiser network

# Assume Python 2.7.x
#

#relook at the setfield and setfields. Should they be in adaptor. Payload length checking should happen on all results.
#could clean up class setup. basic controller could be write only or read only. two classes that inherite. General, gets both, and broadcast, takes write only.

import logging
import time
import serial
from datetime import datetime

from hm_constants import *
from .exceptions import hmResponseError, hmControllerTimeError
from schedule_functions import schedulerdayheat, schedulerweekheat, schedulerdaywater, schedulerweekwater, SCH_ENT_TEMP

class hmController(object):
  ##Variables used by code
  lastreadtime = 0 #records last time of a successful read

  def __init__(self, adaptor, devicesettings, generalsettings = None):
    #address, protocol, short_name, long_name, model, mode
    self._adaptor = adaptor
    
    self.water_schedule = None
        
    #initialise data structures
    self._buildfieldtables()
    self.data = dict.fromkeys(self._fieldnametonum.keys(),None)
    self.datareadtime = dict.fromkeys(self._fieldnametonum.keys(),None)
    
    self._update_settings(devicesettings, generalsettings)

    self.rawdata = [None] * self.DCBlength
  
  def _update_settings(self, settings, generalsettings):
    """Check settings and update if needed."""   
    
    if not generalsettings is None:
        for name, value in generalsettings.iteritems():
            setattr(self, '_' + name, value)
    
    for name, value in settings.iteritems():
      setattr(self, '_' + name, value)
      
    if self._expected_prog_mode == PROG_MODE_DAY:
      self.heat_schedule = schedulerdayheat()
      if self.isHotWater():
        self.water_schedule = schedulerdaywater()
    elif self._expected_prog_mode == PROG_MODE_WEEK:
      self.heat_schedule = schedulerweekheat()
      if self.isHotWater():
        self.water_schedule = schedulerweekwater()
    else:
      raise ValueError("Unknown program mode")
    
    self._expected_prog_mode_number = PROG_MODES[self._expected_prog_mode]
    
    self._fieldranges = FIELDRANGES[self._expected_model][self._expected_prog_mode]
    
    if self._expected_model == 'prt_e_model':
      self.DCBmap = PRTEmap[self._expected_prog_mode]
    elif self._expected_model == 'prt_hw_model':
      self.DCBmap = PRTHWmap[self._expected_prog_mode]
    elif self._expected_model == False:
      self.DCBmap = STRAIGHTmap
    else:
      raise ValueError("Unknown model %s"%self._expected_model)

    self._buildDCBtables()
    
    self._expected_model_number = DEVICE_MODELS[self._expected_model]
    
    if self.DCBmap[0][1] != DCB_INVALID:
      self.DCBlength = self.DCBmap[0][0] - self.DCBmap[0][1] + 1
    elif self.DCBmap[1][1] != DCB_INVALID:
      self.DCBlength = self.DCBmap[1][0] - self.DCBmap[1][1] + 1
    else:
      raise ValueError("DCB map length not found")

    self.fullreadtime = self._estimateReadTime(self.DCBlength)
    
  def _getDCBaddress(self, uniqueaddress):
    #get the DCB address for a controller from the unique address
        return self._uniquetodcb[uniqueaddress]
  
  def _buildfieldtables(self):
    self._fieldnametonum = {}
    for key, data in enumerate(fields):
        fieldname = data[FIELD_NAME]
        self._fieldnametonum[fieldname] = key
        
  def _buildDCBtables(self):
    #build a forward lookup table for the DCB values from uniqueaddress
    self._uniquetodcb = range(MAX_UNIQUE_ADDRESS+1)
    for uniquemax, offsetsel in self.DCBmap:
        self._uniquetodcb[0:uniquemax + 1] = [x - offsetsel for x in range(uniquemax + 1)] if not offsetsel is DCB_INVALID else [DCB_INVALID] * (uniquemax + 1)
    
    #build list of valid fields for this stat
    self._fieldsvalid = [False] * len(fields)
    for first, last in self._fieldranges:
      self._fieldsvalid[self._fieldnametonum[first]: self._fieldnametonum[last] + 1] = [True] * (self._fieldnametonum[last] - self._fieldnametonum[first] + 1)
    #self._fullDCB = sum(x is not None for x in self._uniquetodcb))
    logging.debug("C%i Fieldsvalid %s"%(self._address,','.join(str(int(x)) for x in self._fieldsvalid)))
    
  def getRawData(self, startfieldname = None, endfieldname = None):
    if startfieldname == None or endfieldname == None:
      return self.rawdata
    else:
      return self.rawdata[self._getDCBaddress(uniadd[startfieldname][UNIADD_ADD]):self._getDCBaddress(uniadd[endfieldname][UNIADD_ADD])]
    
  def hmReadVariables(self):
    self.readFields('setroomtemp', 'hotwaterdemand')
    
  def hmReadTempsandDemand(self):
    self.readFields('remoteairtemp', 'hotwaterdemand')
    
  def readTime(self, maxage = 0):
    return self.readField('currenttime', maxage)

  def hmReadAll(self):
    try:
      self.rawdata = self._adaptor.hmReadAllFromController(self._address, self._protocol, self.DCBlength)
    except serial.SerialException as e:

      logging.warn("C%i Read all failed, Serial Port error %s"%(self._address, str(e)))
      raise
    else:
      logging.info("C%i Read all"%(self._address))

      self.lastreadtime = time.time()
      self._procpayload(self.rawdata)
      return self.rawdata

  def readField(self, fieldname, maxage = 0):
    #return field value
    #read field from network if
    # no maxage in request (maxage = 0)
    # maxage is valid and data too old
    # or not be read before (maxage = None)
    if maxage == 0 or (maxage is not None and not self._check_data_age(maxage, fieldname)) or not self._check_data_present(fieldname):
      if self._autoreadall is True:
        self.readFields(fieldname)
      else:
        raise ValueError("Need to read %s first"%fieldname)
    return self.data[fieldname]
    
  def _getFieldBlocks(self, firstfieldname, lastfieldname):
    #data can only be requested from the controller in contiguous blocks
    #functions takes a first and last field and seperates out the individual blocks avaliable for the controller type
    ###return, uniquestart, uniqueend, length of read
    #return, fieldstart, fieldend, length of read in bytes
    
    firstfieldid = self._fieldnametonum[firstfieldname]
    lastfieldid = self._fieldnametonum[lastfieldname]
    
    blocks = []
    previousfieldvalid = False

    for fieldnum, fieldvalid in enumerate(self._fieldsvalid[firstfieldid:lastfieldid + 1],firstfieldid):
        if previousfieldvalid is False and not fieldvalid is False:
            #start = fields[fieldnum][FIELD_ADD]
            start = fieldnum
        elif not previousfieldvalid is False and fieldvalid is False:
            #blocks.append([start,fields[fieldnum][FIELD_ADD],fields[fieldnum][FIELD_ADD] + fields[fieldnum][FIELD_LEN] - start])
            blocks.append([start,fieldnum - 1,fields[fieldnum - 1][FIELD_ADD] + fields[fieldnum - 1][FIELD_LEN] - fields[start][FIELD_ADD]])
        
        previousfieldvalid = fieldvalid

    if not previousfieldvalid is False:
        #blocks.append([start,fields[lastfieldid][FIELD_ADD],fields[lastfieldid][FIELD_ADD] + fields[lastfieldid][FIELD_LEN] - start])
        blocks.append([start,lastfieldid,fields[lastfieldid][FIELD_ADD] + fields[lastfieldid][FIELD_LEN] - fields[start][FIELD_ADD]])
    return blocks
  
  def _estimateBlocksReadTime(self,blocks):
    #estimates read time for a set of blocks, including the COM_BUS_RESET_TIME between blocks 
    #excludes the COM_BUS_RESET_TIME before first block
    readtimes = [self._estimateReadTime(x[2]) for x in blocks]
    return sum(readtimes) + self._adaptor.minTimeBetweenReads() * (len(blocks) - 1)
  
  def _estimateReadTime(self,length):
    #estiamtes the read time for a call to hmReadFromController without COM_BUS_RESET_TIME
    #based on empirical measurements of one prt_hw_model and 5 prt_e_model
    return length * 0.002075 + 0.070727
  
  def readFields(self, firstfieldname, lastfieldname = None):
    #reads fields from controller, safe for blocks crossing gaps in dcb
    if lastfieldname == None:
        lastfieldname = firstfieldname

    blockstoread = self._getFieldBlocks(firstfieldname, lastfieldname)
    logging.debug(blockstoread)
    estimatedreadtime = self._estimateBlocksReadTime(blockstoread)
    
    if estimatedreadtime < self.fullreadtime - 0.02: #if to close to full read time, then read all
        try:
            for firstfieldid, lastfieldid, blocklength in blockstoread:
                logging.debug("C%i Reading ui %i to %i len %i, proc %s to %s"%(self._address, fields[firstfieldid][FIELD_ADD],fields[lastfieldid][FIELD_ADD],blocklength,fields[firstfieldid][FIELD_NAME], fields[lastfieldid][FIELD_NAME]))
                rawdata = self._adaptor.hmReadFromController(self._address, self._protocol, fields[firstfieldid][FIELD_ADD], blocklength)
                self.lastreadtime = time.time()
                self._procpartpayload(rawdata, fields[firstfieldid][FIELD_NAME], fields[lastfieldid][FIELD_NAME])
        except serial.SerialException as e:
            logging.warn("C%i Read failed of fields %s to %s, Serial Port error %s"%(self._address, firstfieldname.ljust(FIELD_NAME_LENGTH),lastfieldname.ljust(FIELD_NAME_LENGTH), str(e)))
            raise
        else:
            logging.info("C%i Read fields %s to %s, in %i blocks"%(self._address, firstfieldname.ljust(FIELD_NAME_LENGTH),lastfieldname.ljust(FIELD_NAME_LENGTH),len(blockstoread)))
    else:
        logging.debug("C%i Read fields %s to %s by readAll, %0.3f %0.3f"%(self._address, firstfieldname.ljust(FIELD_NAME_LENGTH),lastfieldname.ljust(FIELD_NAME_LENGTH), estimatedreadtime, self.fullreadtime))
        self.hmReadAll()
  
  def _procfield(self,data,fieldinfo):
    fieldname = fieldinfo[FIELD_NAME]
    length = fieldinfo[FIELD_LEN]
    factor = fieldinfo[FIELD_DIV]
    range = fieldinfo[FIELD_RANGE]
    #logging.debug("Processing %s %s"%(fieldinfo[FIELD_NAME],', '.join(str(x) for x in data)))
    if length == 1:
      value = data[0]/factor
    elif length == 2:
      val_high = data[0]
      val_low  = data[1]
      value = 1.0*(val_high*256 + val_low)/factor #force float, although always returns integer temps.
    elif length == 4:
      value = data
    elif length == 12:
      self.heat_schedule.set_raw(fieldname,data)
      value = data
    elif length == 16:
      self.water_schedule.set_raw(fieldname,data)
      value = data
    else:
      raise ValueError("_procpayload can't process field length")
  
    if len(range) == 2 and isinstance(range[0], (int, long)) and isinstance(range[1], (int, long)):
      if value < range[0] or value > range[1]:
        raise hmResponseError("Field value %i outside expected range"%value)
    
    if fieldname == 'DCBlen' and value != self.DCBlength:
      raise hmResponseError('DCBlengh is unexpected')
    
    if fieldname == 'model' and value != self._expected_model_number:
      raise hmResponseError('Model is unexpected')
    
    if fieldname == 'programmode' and value != self._expected_prog_mode_number:
      raise hmResponseError('Programme mode is unexpected')
    
    if fieldname == 'version' and self._expected_model != 'prt_hw_model':
      value = data[0] & 0x7f
      self.floorlimiting = data[0] >> 7
      self.data['floorlimiting'] = self.floorlimiting
    
    self.data[fieldname] = value
    setattr(self, fieldname, value)
    self.datareadtime[fieldname] = self.lastreadtime
    
    if fieldname == 'currenttime':
      self._checkcontrollertime()
    
    ###todo, add range validation for other lengths

  def _procpartpayload(self, rawdata, firstfieldname, lastfieldname):
    #rawdata must be a list
    #converts field names to unique addresses to allow process of shortened raw data
    logging.debug("C%i Processing Payload from field %s to %s"%(self._address,firstfieldname,lastfieldname) )
    firstfieldid = self._fieldnametonum[firstfieldname]
    lastfieldid = self._fieldnametonum[lastfieldname]
    self._procpayload(rawdata, firstfieldid, lastfieldid)
    
  def _procpayload(self, rawdata, firstfieldid = 0, lastfieldid = len(fields)):
    logging.debug("C%i Processing Payload from field %i to %i"%(self._address,firstfieldid,lastfieldid) )

    fullfirstdcbadd = self._getDCBaddress(fields[firstfieldid][FIELD_ADD])
    
    for fieldinfo in fields[firstfieldid:lastfieldid + 1]:
      uniqueaddress = fieldinfo[FIELD_ADD]
      
      length = fieldinfo[FIELD_LEN]
      dcbadd = self._getDCBaddress(uniqueaddress)

      if dcbadd == DCB_INVALID:
        setattr(self, fieldinfo[FIELD_NAME], None)
        self.data[fieldinfo[FIELD_NAME]] = None
      else:
        dcbadd -= fullfirstdcbadd #adjust for the start of the request
        
        try:
          self._procfield(rawdata[dcbadd:dcbadd+length], fieldinfo)
        except hmResponseError as e:
          logging.warn("C%i Field %s process failed due to %s"%(self._address, fieldinfo[FIELD_NAME], str(e)))

    self.rawdata[fullfirstdcbadd:fullfirstdcbadd+len(rawdata)] = rawdata

  def _checkcontrollertime(self):
    #run compare of times, and try to fix if _autocorrectime
    try:
      self._comparecontrollertime()
    except hmControllerTimeError:
      if self._autocorrectime is True:
        self.setTime()
      else:
        raise
  
  def _comparecontrollertime(self):       
    # Now do same sanity checking
    # Check the time is within range
    # currentday is numbered 1-7 for M-S
    # localday (python) is numbered 0-6 for Sun-Sat
    
    if not self._check_data_present('currenttime'):
      raise hmResponseError("Time not read before check")

    localtimearray = self._localtimearray(self.datareadtime['currenttime']) #time that time field was read
    localweeksecs = self._weeksecs(localtimearray)
    remoteweeksecs = self._weeksecs(self.data['currenttime'])
    directdifference = abs(localweeksecs - remoteweeksecs)
    wrappeddifference = abs(self.DAYSECS * 7 - directdifference) #compute the difference on rollover
    self.timeerr = min(directdifference, wrappeddifference)
    logging.debug("Local time %i, remote time %i, error %i"%(localweeksecs,remoteweeksecs,self.timeerr))

    if self.timeerr > self.DAYSECS:
        raise hmControllerTimeError("C%2d Incorrect day : local is %s, sensor is %s" % (self._address, localtimearray[CURRENT_TIME_DAY], self.data['currenttime'][CURRENT_TIME_DAY]))

    if (self.timeerr > TIME_ERR_LIMIT):
        raise hmControllerTimeError("C%2d Time Error %d greater than %d: local is %s, sensor is %s" % (self._address, self.timeerr, TIME_ERR_LIMIT, localweeksecs, remoteweeksecs))

  def _localtimearray(self, timenow = time.time()):
    #creates an array in heatmiser format for local time. Day 1-7, 1=Monday
    #input time.time() (not local)
    localtimenow = time.localtime(timenow)
    nowday = localtimenow.tm_wday + 1  #python tm_wday, range [0, 6], Monday is 0
    nowsecs = min(localtimenow.tm_sec, 59) #python tm_sec range[0, 61]
    
    return [nowday, localtimenow.tm_hour, localtimenow.tm_min, nowsecs]
  
  DAYSECS = 86400
  HOURSECS = 3600
  MINSECS = 60
  def _weeksecs(self, localtimearray):
    #calculates the time from the start of the week in seconds from a heatmiser time array
    return ( localtimearray[CURRENT_TIME_DAY] - 1 ) * self.DAYSECS + localtimearray[CURRENT_TIME_HOUR] * self.HOURSECS + localtimearray[CURRENT_TIME_MIN] * self.MINSECS + localtimearray[CURRENT_TIME_SEC]
  
#### External functions for printing data
  def display_heating_schedule(self):
    self.heat_schedule.display()
      
  def display_water_schedule(self):
    if not self.water_schedule is None:
      self.water_schedule.display()

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
      locatimenow = self._localtimearray()
      nexttarget = self.heat_schedule.getNextScheduleItem(locatimenow)
      return "temp overridden to %0.1f until %02d:%02d" % (self.setroomtemp, nexttarget[1], nexttarget[2])
    elif current_state == self.TEMP_STATE_PROGRAM:
      locatimenow = self._localtimearray()
      nexttarget = self.heat_schedule.getNextScheduleItem(locatimenow)
      return "temp set to %0.1f until %02d:%02d" % (self.setroomtemp, nexttarget[1], nexttarget[2])
    
  def _check_data_age(self, maxage, *fieldnames):
    #field data age is not more than maxage (in seconds)
    #return False if old, True if recent
    if len(fieldnames) == 0:
      raise ValueError("Must list at least one field")
    
    for fieldname in fieldnames:
      if not self._check_data_present(fieldname):
        return False
      if time.time() - self.datareadtime[fieldname] > maxage:
        logging.warning("C%i data item %s too old"%(self._address, fieldname))
        return False
    return True
    
  def _check_data_present(self, *fieldnames):
    if len(fieldnames) == 0:
      raise ValueError("Must list at least one field")

    for fieldname in fieldnames:
      if self.datareadtime[fieldname] == None:
        logging.warning("C%i data item %s not avaliable"%(self._address, fieldname))
        return False
    return True
        
#### External functions for getting data

  def isHotWater(self):
    #returns True if stat is a model with hotwater control, False otherwise
    return self._expected_model == 'prt_hw_model'

  TEMP_STATE_OFF = 0  #thermostat display is off and frost protection disabled
  TEMP_STATE_OFF_FROST = 1 #thermostat display is off and frost protection enabled
  TEMP_STATE_FROST = 2 #frost protection enabled indefinitely
  TEMP_STATE_HOLIDAY = 3 #holiday mode, frost protection for a period
  TEMP_STATE_HELD = 4 #temperature held for a number of hours
  TEMP_STATE_OVERRIDDEN = 5 #temperature overridden until next program time
  TEMP_STATE_PROGRAM = 6 #following program
  
  def getTempState(self):
    if not self._check_data_present('onoff','frostprot','holidayhours','runmode','tempholdmins','setroomtemp'):
      if self._autoreadall is True:
        self.hmReadAll()
      else:
        raise ValueError("Need to read all before getting temp state")
        
    if not self._check_data_age(self._max_age_variables, 'onoff','holidayhours','runmode','tempholdmins','setroomtemp'):
      if self._autoreadall is True:
        self.hmReadVariables()
      else:
        raise ValueError("Vars to old to get temp state")
    
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
    
      if not self._check_data_age(self._max_age_time, 'currenttime'):
        currenttime = self.readTime()
      
      locatimenow = self._localtimearray()
      scheduletarget = self.heat_schedule.getCurrentScheduleItem(locatimenow)

      if scheduletarget[SCH_ENT_TEMP] != self.setroomtemp:
        return self.TEMP_STATE_OVERRIDDEN
      else:
        return self.TEMP_STATE_PROGRAM

  ### UNTESTED OR EVEN CHECKED
  def getWaterState(self):
    #does runmode affect hot water state?
    if not self._check_data_present('onoff','holidayhours','hotwaterdemand'):
      if self._autoreadall is True:
        self.hmReadAll()
      else:
        raise ValueError("Need to read all before getting temp state")
        
    if not self._check_data_age(self._max_age_variables, 'onoff','holidayhours','hotwaterdemand'):
      if self._autoreadall is True:
        self.hmReadVariables()
      else:
        raise ValueError("Vars to old to get temp state")
    
    if self.onoff == WRITE_ONOFF_OFF:
      return self.TEMP_STATE_OFF
    elif self.holidayhours != 0:
      return self.TEMP_STATE_HOLIDAY
    else:
    
      if not self._check_data_age(self._max_age_time, 'currenttime'):
        currenttime = self.readTime()
      
      locatimenow = self._localtimearray()
      scheduletarget = self.water_schedule.getCurrentScheduleItem(locatimenow)

      if scheduletarget[SCH_ENT_TEMP] != self.hotwaterdemand:
        return self.TEMP_STATE_OVERRIDDEN
      else:
        return self.TEMP_STATE_PROGRAM
        
  def getAirSensorType(self):
    if not self._check_data_present('sensorsavaliable'):
      return False

    if self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_FLOOR:
      return 1
    elif self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_FLOOR:
      return 2
    else:
      return 0
      
  def getAirTemp(self):
    #if not read before read sensorsavaliable field
    self.readField('sensorsavaliable',None) 
    
    if self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_FLOOR:
      return self.readField('airtemp', self._max_age_temp)
    elif self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_FLOOR:
      return self.readField('remoteairtemp', self._max_age_temp)
    else:
      raise ValueError("sensorsavaliable field invalid")
     
#### External functions for setting data

  def setHeatingSchedule(self, day, schedule):
    padschedule = self.heat_schedule.pad_schedule(schedule)
    self._adaptor.setField(self._address,self._protocol,day,padschedule)
    
  def setWaterSchedule(self, day, schedule):
    padschedule = self.water_schedule.pad_schedule(schedule)
    if day == 'all':
      self.setField('mon_water',padschedule)
      self.setField('tues_water',padschedule)
      self.setField('wed_water',padschedule)
      self.setField('thurs_water',padschedule)
      self.setField('fri_water',padschedule)
      self.setField('sat_water',padschedule)
      self.setField('sun_water',padschedule)
    else:
      self.setField(day,padschedule)

  def setTime(self) :
      """set time on controller to match current localtime on server"""
      timenow = time.time() + 0.5 #allow a little time for any delay in setting
      return self.setField('currenttime',self._localtimearray(timenow))
      
#general field setting

  def setField(self,fieldname,payload):
    #set a field (single member of fields) to a state or payload. Defined for all field lengths.
    fieldinfo = fields[self._fieldnametonum[fieldname]]
    
    if len(fieldinfo) < FIELD_WRITE + 1 or fieldinfo[FIELD_WRITE] != 'W':
        #check that write is part of field info and is 'W'
        raise ValueError("setField: field isn't writeable")        
               
    self._checkPayloadValues(payload, fieldinfo)

    if fieldinfo[FIELD_LEN] == 1:
        payload = [payload]
    elif fieldinfo[FIELD_LEN] == 2:
        pay_lo = (payload & BYTEMASK)
        pay_hi = (payload >> 8) & BYTEMASK
        payload = [pay_lo, pay_hi]
    try:
        print payload
        self._adaptor.hmWriteToController(self._address, self._protocol, fieldinfo[FIELD_ADD], fieldinfo[FIELD_LEN], payload)
    except:
        logging.info("C%i failed to set field %s to %s"%(self._address, fieldname.ljust(FIELD_NAME_LENGTH), ', '.join(str(x) for x in payload)))
        raise
    else:
        logging.info("C%i set field %s to %s"%(self._address, fieldname.ljust(FIELD_NAME_LENGTH), ', '.join(str(x) for x in payload)))
    
    self.lastreadtime = time.time()
    
    ###should really be handled by a specific overriding function, rather than in here.
    #handle odd effect on WRITE_hotwaterdemand_PROG
    if fieldname == 'hotwaterdemand':
      if value == WRITE_HOTWATERDEMAND_PROG: #returned to program so outcome is unknown
        self.datareadtime[field] = None
        return None
      elif value == WRITE_HOTWATERDEMAND_OFF: #if overridden off store the off read value
        value = READ_HOTWATERDEMAND_OFF
    
    self._procpartpayload(payload,fieldname,fieldname)
    
  def _checkPayloadValues(self, payload, fieldinfo):
      #check the payload matches field details
      
      if fieldinfo[FIELD_LEN] in [1, 2] and not isinstance(payload, (int, long)):
          #one or two byte field, not single length payload
          raise TypeError("setField: invalid requested value")
      elif fieldinfo[FIELD_LEN] > 2 and len(payload) != fieldinfo[FIELD_LEN]:
          #greater than two byte field, payload length must match field length
          raise ValueError("setField: invalid payload length")
  
      #checks the payload matches the ranges if ranges are defined 
      ranges = fieldinfo[FIELD_RANGE]
      if ranges != []:
          if isinstance(payload, (int, long)):
              if ( payload < ranges[0] or payload > ranges[1] ):
                  raise ValueError("setField: payload out of range")
          else:
              for i, item in enumerate(payload):
                  range = ranges[i % len(ranges)]
                  if item < range[0] or item > range[1]:
                      raise ValueError("setField: payload out of range")
  
#overriding      
      
  def setTemp(self, temp) :
    #sets the temperature demand overriding the program. Believe it returns at next prog change.
  
    #check hold temp not applied
    if self.readField('tempholdmins') == 0:
      return self._adaptor.setField(self._address,self._protocol,'setroomtemp',temp)
    else:
      logging.warn("%i address, temp hold applied so won't set temp"%(self._address))

  def releaseTemp(self) :
    #release SetTemp back to the program, but only if temp isn't held
    if self.readField('tempholdmins') == 0:
      return self._adaptor.setField(self._address,self._protocol,'tempholdmins',0)
    else:
      logging.warn("%i address, temp hold applied so won't remove set temp"%(self._address))     

  def holdTemp(self, minutes, temp) :
    #sets the temperature demand overrding the program for a set time. Believe it then returns to program.
    self._adaptor.setField(self._address,self._protocol,'setroomtemp',temp)
    return self._adaptor.setField(self._address,self._protocol,'tempholdmins',minutes)
    #didn't stay on if did minutes followed by temp.
    
  def releaseHoldTemp(self) :
    #release SetTemp or HoldTemp back to the program
    return self._adaptor.setField(self._address,self._protocol,'tempholdmins',0)
    
  def setHoliday(self, hours) :
    #sets holiday up for a defined number of hours
    return self._adaptor.setField(self._address,self._protocol,'holidayhours',hours)
  
  def releaseHoliday(self) :
    #cancels holiday mode
    return self._adaptor.setField(self._address,self._protocol,'holidayhours',0)

#onoffs

  def setOn(self):
    return self._adaptor.setField(self._address,self._protocol,'onoff',WRITE_ONOFF_ON)
  def setOff(self):
    return self._adaptor.setField(self._address,self._protocol,'onoff',WRITE_ONOFF_OFF)
    
  def setHeat(self):
    return self._adaptor.setField(self._address,self._protocol,'runmode',WRITE_RUNMODE_HEATING)
  def setFrost(self):
    return self._adaptor.setField(self._address,self._protocol,'runmode',WRITE_RUNMODE_FROST)
    
  def setLock(self):
    return self._adaptor.setField(self._address,self._protocol,'keylock',WRITE_KEYLOCK_ON)
  def setUnlock(self):
    return self._adaptor.setField(self._address,self._protocol,'keylock',WRITE_KEYLOCK_OFF)
  
#other
#set floor limit
#set holiday

class hmBroadcastController(hmController):
  #create a controller that only broadcasts
  def __init__(self, network, long_name):
    settings = {'address':BROADCAST_ADDR,'display_order': 0, 'long_name': long_name,'protocol':DEFAULT_PROTOCOL,'expected_model':False,'expected_prog_mode':DEFAULT_PROG_MODE}
    super(hmBroadcastController, self).__init__(network, settings)
  
  ##add methods to block or remove get functions
