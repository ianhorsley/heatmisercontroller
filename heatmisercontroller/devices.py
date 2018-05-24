#
# Ian Horsley 2018

#
# hmController class
# handles all the DCB and data objects for each controller on the heatmiser network

# Assume Python 2.7.x
#

#consider adding timestamps to all parameters for their age.

import logging
import time
import serial
from datetime import datetime

from hm_constants import *

class hmController(object):

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
        raise ValueError("Need to read all before reading subset")

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
        raise ValueError("Need to read all before reading subset")
  
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

    ###remove next line?
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
        raise ValueError("Need to read all before reading processing payload")

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
        raise ValueError("Need to read all before getting temp state")
        
    if not self._check_vars_current():
      if self.autoreadall:
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

  def setFields(self,field,value):
    return self.network.hmSetFields(self.address,self.protocol,field,value)

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


class hmBroadcastController(hmController):
  #create a controller that only broadcasts
  def __init__(self, network, short_name, long_name):
    super(hmBroadcastController, self).__init__(network, BROADCAST_ADDR, DEFAULT_PROTOCOL, short_name, long_name, False, DEFAULT_PROG_MODE)
  
  ##add methods to block or remove get functions
