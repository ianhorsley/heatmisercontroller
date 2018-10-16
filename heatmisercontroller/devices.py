"""Heatmiser Device Classes

Modules handle all the DCB and fields for each device on the Heatmiser network

Ian Horsley 2018
"""

#read = return local if not to old, otherwise gets
#get = goes to network to get
#each field should it's own maximum age

import logging
import time
import serial
import copy

from hm_constants import *
from .exceptions import HeatmiserResponseError, HeatmiserControllerTimeError
from schedule_functions import SchedulerDayHeat, SchedulerWeekHeat, SchedulerDayWater, SchedulerWeekWater, SCH_ENT_TEMP
from decorators import ListWrapperClass, run_function_on_all
from operator import itemgetter

class HeatmiserDevice(object):
    """General device class for thermostats"""
    ## Variables used by code
    lastreadtime = 0 #records last time of a successful read

    ## Initialisation functions and low level functions
    def __init__(self, adaptor, devicesettings, generalsettings=None):
        
        self._adaptor = adaptor

        # initialise external parameters
        self.protocol = DEFAULT_PROTOCOL
        # initialise data structures
        self._uniquetodcb = []
        self._fieldsvalid = [True] * len(fields) # assume all fields are valid until shown otherwise
        self.dcb_length = None
        self.expected_prog_mode = None
        self._expected_model_number = None
        self.long_name = ''
        self._buildfieldtables()
        self.data = dict.fromkeys(self._fieldnametonum.keys(), None)
        self.floorlimiting = None
        self.datareadtime = dict.fromkeys(self._fieldnametonum.keys(), None)
        self.timeerr = None
        self.fullreadtime = 0 #default to full read
        self.heat_schedule = self.water_schedule = None
        
        self._update_settings(devicesettings, generalsettings)

        self.rawdata = [None] * self.dcb_length

    def _update_settings(self, settings, generalsettings):
        """Laod and process settings."""

        self._load_settings(settings, generalsettings)
        self._process_settings()
    
    def _load_settings(self, settings, generalsettings):
        """Loading settings from dictionary into properties"""
        
        if not generalsettings is None:
            for name, value in generalsettings.iteritems():
                setattr(self, name, value)

        for name, value in settings.iteritems():
            setattr(self, name, value)

        try:
            self.long_name
        except AttributeError:
            self.long_name = 'Unknown'
    
    def _process_settings(self):
        """Process settings based on device model and program mode"""
        
        # Create required schedule objects
        self.water_schedule = None
        if self.expected_prog_mode == PROG_MODE_DAY:
            self.heat_schedule = SchedulerDayHeat()
            if self.is_hot_water():
                self.water_schedule = SchedulerDayWater()
        elif self.expected_prog_mode == PROG_MODE_WEEK:
            self.heat_schedule = SchedulerWeekHeat()
            if self.is_hot_water():
                self.water_schedule = SchedulerWeekWater()
        else:
            raise ValueError("Unknown program mode")

        ### should replace this stuff with something based on the fieldranges which is much easier to understand
        if self.expected_model == 'prt_e_model':
            self.dcb_map = PRTEmap[self.expected_prog_mode]
        elif self.expected_model == 'prt_hw_model':
            self.dcb_map = PRTHWmap[self.expected_prog_mode]
        elif self.expected_model == False:
            self.dcb_map = STRAIGHTmap
        else:
            raise ValueError("Unknown model %s"%self.expected_model)

        self._build_dcb_tables()

        self._expected_model_number = DEVICE_MODELS[self.expected_model]

        if self.dcb_map[0][1] != DCB_INVALID:
            self.dcb_length = self.dcb_map[0][0] - self.dcb_map[0][1] + 1
        elif self.dcb_map[1][1] != DCB_INVALID:
            self.dcb_length = self.dcb_map[1][0] - self.dcb_map[1][1] + 1
        else:
            raise ValueError("DCB map length not found")

        # estimated read time for read_all method
        self.fullreadtime = self._estimate_read_time(self.dcb_length)
    
    def _get_dcb_address(self, uniqueaddress):
        """get the DCB address for a controller from the unique address"""
        return self._uniquetodcb[uniqueaddress]
    
    def _buildfieldtables(self):
        """build dict to map field name to index"""
        self._fieldnametonum = {}
        for key, data in enumerate(fields):
            fieldname = data[FIELD_NAME]
            self._fieldnametonum[fieldname] = key
                
    def _build_dcb_tables(self):
        """build list to map unique to dcb address and list of valid fields """
        #build a forward lookup table for the DCB values from unique address
        self._uniquetodcb = range(MAX_UNIQUE_ADDRESS+1)
        for uniquemax, offsetsel in self.dcb_map:
            self._uniquetodcb[0:uniquemax + 1] = [x - offsetsel for x in range(uniquemax + 1)] if not offsetsel is DCB_INVALID else [DCB_INVALID] * (uniquemax + 1)
        
        #build list of valid fields for this device
        self._fieldsvalid = [False] * len(fields)
        fieldranges = FIELDRANGES[self.expected_model][self.expected_prog_mode]
        for first, last in fieldranges:
            self._fieldsvalid[self._fieldnametonum[first]: self._fieldnametonum[last] + 1] = [True] * (self._fieldnametonum[last] - self._fieldnametonum[first] + 1)
        logging.debug("C%i Fieldsvalid %s"%(self.address, ','.join(str(int(x)) for x in self._fieldsvalid)))
    
    def _check_data_age(self, fieldnames, maxagein=None):
        """Check field data age is not more than maxage (in seconds)
        fieldnames can be list or string
        
        maxage = None, use the default from fields
        maxage = -1, only check if present
        maxage >=0, use maxage (0 is effectively always False)
        return False if old, True if recent"""
        if len(fieldnames) == 0:
            raise ValueError("Must list at least one field")
        
        if not isinstance(fieldnames, list):
            fieldnames = [fieldnames]
        
        for fieldname in fieldnames:
            if not self._check_data_present(fieldname):
                return False
            elif maxagein == -1: #only check present
                return True
            elif maxagein == None: #if none use field defaults
                maxage = fields[self._fieldnametonum[fieldname]][FIELD_MAX_AGE]
            else:
                maxage = maxagein
            #now check time
            if time.time() - self.datareadtime[fieldname] > maxage:
                logging.debug("C%i data item %s too old"%(self.address, fieldname))
                return False
        return True
        
    def _check_data_present(self, *fieldnames):
        """Check field(s) has data"""
        #Returns True if all present
        if len(fieldnames) == 0:
            raise ValueError("Must list at least one field")

        for fieldname in fieldnames:
            if self.datareadtime[fieldname] == None:
                logging.debug("C%i data item %s not available"%(self.address, fieldname))
                return False
        return True
    
    ## Basic reading and getting functions
    
    def read_all(self):
        """Returns all the field values having got them from the device"""
        try:
            self.rawdata = self._adaptor.read_all_from_device(self.address, self.protocol, self.dcb_length)
        except serial.SerialException as err:

            logging.warn("C%i Read all failed, Serial Port error %s"%(self.address, str(err)))
            raise
        else:
            logging.info("C%i Read all"%(self.address))

            self.lastreadtime = time.time()
            self._procpayload(self.rawdata)
            return self.rawdata

    def read_field(self, fieldname, maxage=None):
        """Returns a fields value, gets from the device if to old"""
        #return field value
        #get field from network if
        # maxage = None, older than the default from fields
        # maxage = -1, not read before
        # maxage >=0, older than maxage
        # maxage = 0, always
        if maxage == 0 or not self._check_data_age(fieldname, maxage):
            if self.autoreadall is True:
                self.get_field_range(fieldname)
            else:
                raise ValueError("Need to read %s first"%fieldname)
        return self.data[fieldname]
    
    def read_fields(self, fieldnames, maxage=None):
        """Returns a list of field values, gets from the device if any are to old"""
        #find which fields need getting because to old
        if not isinstance(fieldnames, list):
            raise TypeError("fieldnames must be a list")
        
        fieldids = [self._fieldnametonum[fieldname] for fieldname in fieldnames if self._fieldsvalid[self._fieldnametonum[fieldname]] and (maxage == 0 or not self._check_data_age(fieldname, maxage))]
        
        fieldids = list(set(fieldids)) #remove duplicates, ordering doesn't matter
        
        if len(fieldids) > 0 and self.autoreadall is True:
            self._get_fields(fieldids)
        elif len(fieldids) > 0:
            raise ValueError("Need to read fields first")
        return [self.data[fieldname] for fieldname in fieldnames]
    
    def get_variables(self):
        """Gets setroomtemp to hotwaterdemand fields from device"""
        self.get_field_range('setroomtemp', 'hotwaterdemand')
        
    def get_temps_and_demand(self):
        """Gets remoteairtemp to hotwaterdemand fields from device"""
        self.get_field_range('remoteairtemp', 'hotwaterdemand')
    
    def get_field_range(self, firstfieldname, lastfieldname=None):
        """gets fieldrange from device
        
        safe for blocks crossing gaps in dcb"""
        if lastfieldname == None:
            lastfieldname = firstfieldname

        blockstoread = self._get_field_blocks_from_range(firstfieldname, lastfieldname)
        logging.debug(blockstoread)
        estimatedreadtime = self._estimate_blocks_read_time(blockstoread)
        
        if estimatedreadtime < self.fullreadtime - 0.02: #if to close to full read time, then read all
            try:
                for firstfieldid, lastfieldid, blocklength in blockstoread:
                    logging.debug("C%i Reading ui %i to %i len %i, proc %s to %s"%(self.address, fields[firstfieldid][FIELD_ADD], fields[lastfieldid][FIELD_ADD], blocklength, fields[firstfieldid][FIELD_NAME], fields[lastfieldid][FIELD_NAME]))
                    rawdata = self._adaptor.read_from_device(self.address, self.protocol, fields[firstfieldid][FIELD_ADD], blocklength)
                    self.lastreadtime = time.time()
                    self._procpartpayload(rawdata, fields[firstfieldid][FIELD_NAME], fields[lastfieldid][FIELD_NAME])
            except serial.SerialException as err:
                logging.warn("C%i Read failed of fields %s to %s, Serial Port error %s"%(self.address, firstfieldname.ljust(FIELD_NAME_LENGTH), lastfieldname.ljust(FIELD_NAME_LENGTH), str(err)))
                raise
            else:
                logging.info("C%i Read fields %s to %s, in %i blocks"%(self.address, firstfieldname.ljust(FIELD_NAME_LENGTH), lastfieldname.ljust(FIELD_NAME_LENGTH), len(blockstoread)))
        else:
            logging.debug("C%i Read fields %s to %s by read_all, %0.3f %0.3f"%(self.address, firstfieldname.ljust(FIELD_NAME_LENGTH), lastfieldname.ljust(FIELD_NAME_LENGTH), estimatedreadtime, self.fullreadtime))
            self.read_all()

    def _get_fields(self, fieldids):
        """gets fields from device
        
        safe for blocks crossing gaps in dcb"""
        
        blockstoread = self._get_field_blocks_from_id_list(fieldids)
        logging.debug(blockstoread)
        estimatedreadtime = self._estimate_blocks_read_time(blockstoread)
        
        if estimatedreadtime < self.fullreadtime - 0.02: #if to close to full read time, then read all
            try:
                for firstfieldid, lastfieldid, blocklength in blockstoread:
                    logging.debug("C%i Reading ui %i to %i len %i, proc %s to %s"%(self.address, fields[firstfieldid][FIELD_ADD], fields[lastfieldid][FIELD_ADD], blocklength, fields[firstfieldid][FIELD_NAME], fields[lastfieldid][FIELD_NAME]))
                    rawdata = self._adaptor.read_from_device(self.address, self.protocol, fields[firstfieldid][FIELD_ADD], blocklength)
                    self.lastreadtime = time.time()
                    self._procpartpayload(rawdata, fields[firstfieldid][FIELD_NAME], fields[lastfieldid][FIELD_NAME])
            except serial.SerialException as err:
                logging.warn("C%i Read failed of fields %s, Serial Port error %s"%(self.address, ', '.join(fields[id][FIELD_NAME] for id in fieldids), str(err)))
                raise
            else:
                logging.info("C%i Read fields %s in %i blocks"%(self.address, ', '.join(fields[id][FIELD_NAME] for id in fieldids), len(blockstoread)))
                    
        else:
            logging.debug("C%i Read fields %s by read_all, %0.3f %0.3f"%(self.address, ', '.join(fields[id][FIELD_NAME] for id in fieldids), estimatedreadtime, self.fullreadtime))
            self.read_all()
                
        #data can only be requested from the controller in contiguous blocks
        #functions takes a first and last field and separates out the individual blocks available for the controller type
        #return, fieldstart, fieldend, length of read in bytes
    def _get_field_blocks_from_range(self, firstfieldname, lastfieldname):
        """Takes range of fieldnames and returns field blocks"""
        firstfieldid = self._fieldnametonum[firstfieldname]
        lastfieldid = self._fieldnametonum[lastfieldname]
        return self._get_field_blocks_from_id_range(firstfieldid, lastfieldid)
        
    def _get_field_blocks_from_id_range(self, firstfieldid, lastfieldid):
        """Takes range of fieldids and returns field blocks
        
        Splits by invalid fields"""
        blocks = []
        previousfieldvalid = False

        for fieldnum, fieldvalid in enumerate(self._fieldsvalid[firstfieldid:lastfieldid + 1], firstfieldid):
            if previousfieldvalid is False and not fieldvalid is False:
                start = fieldnum
            elif not previousfieldvalid is False and fieldvalid is False:
                blocks.append([start, fieldnum - 1, fields[fieldnum - 1][FIELD_ADD] + fields[fieldnum - 1][FIELD_LEN] - fields[start][FIELD_ADD]])
            
            previousfieldvalid = fieldvalid

        if not previousfieldvalid is False:
            blocks.append([start, lastfieldid, fields[lastfieldid][FIELD_ADD] + fields[lastfieldid][FIELD_LEN] - fields[start][FIELD_ADD]])
        return blocks
    
    def _get_field_blocks_from_id_list(self, fieldids):
        """Takes range of fieldids and returns field blocks
        
        Splits by invalid fields. Uses timing to determine the optimum blocking"""
        #find blocks between lowest and highest field
        fieldblocks = self._get_field_blocks_from_id_range(min(fieldids), max(fieldids))
        
        readblocks = []
        for block in fieldblocks:
            #find fields in that block
            inblock = [id for id in fieldids if block[0] <= id <= block[1]]
            if len(inblock) > 0:
                #if single read is shorter than individual
                readlen = fields[max(inblock)][FIELD_LEN] + fields[max(inblock)][FIELD_ADD] - fields[min(inblock)][FIELD_ADD]
                if self._estimate_read_time(readlen) < sum([self._estimate_read_time(fields[id][FIELD_LEN]) for id in inblock]):
                    readblocks.append([min(inblock), max(inblock), readlen])
                else:
                    for ids in inblock:
                        readblocks.append([ids, ids, fields[ids][FIELD_LEN]])
        return readblocks
    
    def _estimate_blocks_read_time(self, blocks):
        """estimates read time for a set of blocks, including the COM_BUS_RESET_TIME between blocks
        
        excludes the COM_BUS_RESET_TIME before first block"""
        readtimes = [self._estimate_read_time(x[2]) for x in blocks]
        return sum(readtimes) + self._adaptor.min_time_between_reads() * (len(blocks) - 1)
    
    @staticmethod
    def _estimate_read_time(length):
        """"estimates the read time for a call to read_from_device without COM_BUS_RESET_TIME
        
        based on empirical measurements of one prt_hw_model and 5 prt_e_model"""
        return length * 0.002075 + 0.070727
    
    def _procfield(self, data, fieldinfo, sentpayload=False):
        """Process data for a single field storing in relevant.
        
        Converts from bytes to integers/floats
        Checks the validity"""
        fieldname = fieldinfo[FIELD_NAME]
        length = fieldinfo[FIELD_LEN]
        factor = fieldinfo[FIELD_DIV]
        fieldrange = fieldinfo[FIELD_RANGE]
        #logging.debug("Processing %s %s"%(fieldinfo[FIELD_NAME],', '.join(str(x) for x in data)))
        if sentpayload: #some mapping required if was a sent payload
            data = self._map_write_to_read_payload(data, fieldname)
        
        if data is None:
            value = None
        elif length == 1:
            value = data[0]/factor
        elif length == 2:
            val_high = data[0]
            val_low = data[1]
            value = 1.0*(val_high*256 + val_low)/factor #force float, although always returns integer temps.
        elif length == 4:
            value = data
        elif length == 12:
            self.heat_schedule.set_raw(fieldname, data)
            value = data
        elif length == 16:
            self.water_schedule.set_raw(fieldname, data)
            value = data
        else:
            raise ValueError("_procpayload can't process field length")
    
        if fieldname == 'address' and value != self.address:
            raise HeatmiserResponseError('Address is unexpected')
    
        if len(fieldrange) == 2 and isinstance(fieldrange[0], (int, long)) and isinstance(fieldrange[1], (int, long)) and not value is None:
            if value < fieldrange[0] or value > fieldrange[1]:
                raise HeatmiserResponseError("Field value %i outside expected range"%value)
        
        if not self.dcb_length is None and fieldname == 'DCBlen' and value != self.dcb_length:
            raise HeatmiserResponseError('DCBlengh is unexpected')
            
        if not self._expected_model_number is None and fieldname == 'model' and value != self._expected_model_number:
            raise HeatmiserResponseError('Model is unexpected')
        
        if not self.expected_prog_mode is None and fieldname == 'programmode' and value != PROG_MODES[self.expected_prog_mode]:
            raise HeatmiserResponseError('Programme mode is unexpected')
        
        if fieldname == 'version' and self.expected_model != 'prt_hw_model':
            value = data[0] & 0x7f
            self.floorlimiting = data[0] >> 7
            self.data['floorlimiting'] = self.floorlimiting
        
        self.data[fieldname] = value
        setattr(self, fieldname, value)
        self.datareadtime[fieldname] = self.lastreadtime if not value is None else None #unless sent payload and don't know the read value
        
        if fieldname == 'currenttime':
            self._checkcontrollertime()
        
        ###todo, add range validation for other lengths

    @staticmethod
    def _map_write_to_read_payload(data, fieldname):
        """Maps written payload to equvialent read payload"""
        #returns None if unknown result.
        #handle odd effect on WRITE_hotwaterdemand_PROG
        if fieldname == 'hotwaterdemand':
            if data[0] == WRITE_HOTWATERDEMAND_PROG: #returned to program so outcome is unknown
                return None
            elif data[0] == WRITE_HOTWATERDEMAND_OVER_OFF: #if overridden off store the off read value
                return [READ_HOTWATERDEMAND_OFF]
            else:
                return data
        else:
            return data

    def _procpartpayload(self, rawdata, firstfieldname, lastfieldname, sentpayload=False):
        """Wraps procpayload by converting fieldnames to fieldids"""
        #rawdata must be a list
        #converts field names to unique addresses to allow process of shortened raw data
        logging.debug("C%i Processing Payload from field %s to %s"%(self.address, firstfieldname, lastfieldname))
        firstfieldid = self._fieldnametonum[firstfieldname]
        lastfieldid = self._fieldnametonum[lastfieldname]
        self._procpayload(rawdata, firstfieldid, lastfieldid, sentpayload)
        
    def _procpayload(self, rawdata, firstfieldid=0, lastfieldid=len(fields), sentpayload=False):
        """Split payload with field information and processes each field"""
        logging.debug("C%i Processing Payload from field %i to %i"%(self.address, firstfieldid, lastfieldid))

        fullfirstdcbadd = self._get_dcb_address(fields[firstfieldid][FIELD_ADD])
        
        for fieldinfo in fields[firstfieldid:lastfieldid + 1]:
            uniqueaddress = fieldinfo[FIELD_ADD]
            
            length = fieldinfo[FIELD_LEN]
            dcbadd = self._get_dcb_address(uniqueaddress)

            if dcbadd == DCB_INVALID:
                setattr(self, fieldinfo[FIELD_NAME], None)
                self.data[fieldinfo[FIELD_NAME]] = None
            else:
                dcbadd -= fullfirstdcbadd #adjust for the start of the request
                
                try:
                    self._procfield(rawdata[dcbadd:dcbadd+length], fieldinfo, sentpayload)
                except HeatmiserResponseError as err:
                    logging.warn("C%i Field %s process failed due to %s"%(self.address, fieldinfo[FIELD_NAME], str(err)))

        self.rawdata[fullfirstdcbadd:fullfirstdcbadd+len(rawdata)] = rawdata

    def _checkcontrollertime(self):
        """run check of device time against local read time, and try to fix if _autocorrectime"""
        try:
            self._comparecontrollertime()
        except HeatmiserControllerTimeError:
            if self.autocorrectime is True:
                ### Add warning that attempting to fix.
                self.set_time()
            else:
                raise
    
    def _comparecontrollertime(self):
        """Compare device and local time difference against threshold"""
        # Now do same sanity checking
        # Check the time is within range
        # currentday is numbered 1-7 for M-S
        # localday (python) is numbered 0-6 for Sun-Sat
        
        if not self._check_data_present('currenttime'):
            raise HeatmiserResponseError("Time not read before check")

        localtimearray = self._localtimearray(self.datareadtime['currenttime']) #time that time field was read
        localweeksecs = self._weeksecs(localtimearray)
        remoteweeksecs = self._weeksecs(self.data['currenttime'])
        directdifference = abs(localweeksecs - remoteweeksecs)
        wrappeddifference = abs(self.DAYSECS * 7 - directdifference) #compute the difference on rollover
        self.timeerr = min(directdifference, wrappeddifference)
        logging.debug("Local time %i, remote time %i, error %i"%(localweeksecs, remoteweeksecs, self.timeerr))

        if self.timeerr > self.DAYSECS:
            raise HeatmiserControllerTimeError("C%2d Incorrect day : local is %s, sensor is %s" % (self.address, localtimearray[CURRENT_TIME_DAY], self.data['currenttime'][CURRENT_TIME_DAY]))

        if self.timeerr > TIME_ERR_LIMIT:
            raise HeatmiserControllerTimeError("C%2d Time Error %d greater than %d: local is %s, sensor is %s" % (self.address, self.timeerr, TIME_ERR_LIMIT, localweeksecs, remoteweeksecs))

    @staticmethod
    def _localtimearray(timenow=time.time()):
        """creates an array in heatmiser format for local time. Day 1-7, 1=Monday"""
        #input time.time() (not local)
        localtimenow = time.localtime(timenow)
        nowday = localtimenow.tm_wday + 1 #python tm_wday, range [0, 6], Monday is 0
        nowsecs = min(localtimenow.tm_sec, 59) #python tm_sec range[0, 61]
        
        return [nowday, localtimenow.tm_hour, localtimenow.tm_min, nowsecs]
    
    DAYSECS = 86400
    HOURSECS = 3600
    MINSECS = 60
    def _weeksecs(self, localtimearray):
        """calculates the time from the start of the week in seconds from a heatmiser time array"""
        return (localtimearray[CURRENT_TIME_DAY] - 1) * self.DAYSECS + localtimearray[CURRENT_TIME_HOUR] * self.HOURSECS + localtimearray[CURRENT_TIME_MIN] * self.MINSECS + localtimearray[CURRENT_TIME_SEC]
    
    ## Basic set field functions
    
    def set_field(self, fieldname, payload):
        """Set a field (single member of fields) on a device to a state or payload. Defined for all known field lengths."""
        #Payload must not be list for field length 1 or 2
        fieldid = self._fieldnametonum[fieldname]
        if not self._fieldsvalid[fieldid]:
            raise IndexError('Field not valid for this device')
        fieldinfo = fields[fieldid]
        
        self._is_writable(fieldinfo)
        self._check_payload_values(payload, fieldinfo)
        payloadbytes = self._format_payload(payload, fieldinfo[FIELD_LEN])
        
        if not isinstance(payload, list): #adjust for the 
            payload = [payload]
        try:
            self._adaptor.write_to_device(self.address, self.protocol, fieldinfo[FIELD_ADD], fieldinfo[FIELD_LEN], payloadbytes)
        except serial.SerialException as err:
            logging.warn("C%i failed to set field %s to %s, due to %s"%(self.address, fieldname.ljust(FIELD_NAME_LENGTH), ', '.join(str(x) for x in payload), str(err)))
            raise
        else:
            logging.info("C%i set field %s to %s"%(self.address, fieldname.ljust(FIELD_NAME_LENGTH), ', '.join(str(x) for x in payload)))
        
        self.lastreadtime = time.time()
        self._procpartpayload(payloadbytes, fieldname, fieldname, True)
    
    @staticmethod
    def _format_payload(payload, field_len):
        """Convert fields to byte form for writting to device"""
        if field_len == 1:
            return [payload]
        elif field_len == 2:
            pay_lo = (payload & BYTEMASK)
            pay_hi = (payload >> 8) & BYTEMASK
            return [pay_lo, pay_hi]
        else:
            return payload
    
    @staticmethod
    def _is_writable(fieldinfo):
        """Checks if field is writable"""
        if len(fieldinfo) < FIELD_WRITE + 1 or fieldinfo[FIELD_WRITE] != 'W':
            #check that write is part of field info and is 'W'
            raise ValueError("set_field: field isn't writeable")
    
    def set_fields(self, fieldnames, payloads):
        """Set multiple fields on a device to a state or payload."""
        #It groups adjacent fields and issues multiple sets if required.
        #inputs must be mathcing length lists
        if not isinstance(fieldnames, list) or not isinstance(payloads, list):
            raise ValueError("fieldnames and payloads must be lists")
        if len(fieldnames) != len(payloads):
            raise IndexError("fields and payloads don't match")
        if len(fieldnames) != len(set(fieldnames)):
            raise ValueError("duplicated fieldnames")
        
        #Get field ids
        fieldids = [self._fieldnametonum[fieldname] for fieldname in fieldnames]
        outputdata = self._get_payload_blocks_from_list(fieldids, payloads)
        try:
            for unique_start_address, lengthbytes, payloadbytes, firstfieldname, lastfieldname in outputdata:
                logging.debug("C%i Setting ui %i len %i, proc %s to %s"%(self.address, unique_start_address, lengthbytes, firstfieldname, lastfieldname))
                self._adaptor.write_to_device(self.address, self.protocol, unique_start_address, lengthbytes, payloadbytes)
                self.lastreadtime = time.time()
                self._procpartpayload(payloadbytes, firstfieldname, lastfieldname, True)
        except serial.SerialException as err:
            logging.warn("C%i settings failed of fields %s, Serial Port error %s"%(self.address, ', '.join(fields[id][FIELD_NAME] for id in fieldids), str(err)))
            raise
        else:
            logging.info("C%i set fields %s in %i blocks"%(self.address, ', '.join(fields[id][FIELD_NAME] for id in fieldids), len(outputdata)))

    def _get_payload_blocks_from_list(self, fieldids, payloads):
        """Converts list of fields and payloads into groups of payload data"""
        #returns unique_start_address, lengthbytes, payloadbytes, firstfieldname, lastfieldname
        sortedfields = sorted(enumerate(fieldids), key=itemgetter(0))
        
        payloadscopy = copy.deepcopy(payloads) #force copy of payloads so doesn't get changed later.
        
        #Check field data and sort payloads
        sorteddata = []
        for orginalindex, fieldid in sortedfields:
            if self._fieldsvalid[fieldid]:
                fieldinfo = fields[fieldid]
                self._is_writable(fieldinfo)
                self._check_payload_values(payloadscopy[orginalindex], fieldinfo)
                sorteddata.append([fieldid, fieldinfo, payloadscopy[orginalindex]]) 
        
        #Groups and map to unique addresses
        outputdata = []
        previousfield = None
        for fieldid, fieldinfo, payload in sorteddata:
            if not previousfield is None and fieldid - previousfield == 1: #if follows previousfield
                outputdata[-1][1] += fieldinfo[FIELD_LEN]
                outputdata[-1][2].extend(self._format_payload(payload, fieldinfo[FIELD_LEN]))
                outputdata[-1][4] = fieldinfo[FIELD_NAME]
            else:
                #unique_start_address, bytelength, payloadbytes, firstfieldname, lastfieldname
                outputdata.append([fieldinfo[FIELD_ADD], fieldinfo[FIELD_LEN], self._format_payload(payload, fieldinfo[FIELD_LEN]), fieldinfo[FIELD_NAME], fieldinfo[FIELD_NAME]])
            previousfield = fieldid

        return outputdata
    
    @staticmethod
    def _check_payload_values(payload, fieldinfo):
        """check a single field payload matches field spec"""
        
        if fieldinfo[FIELD_LEN] in [1, 2] and not isinstance(payload, (int, long)):
            #one or two byte field, not single length payload
            raise TypeError("set_field: invalid requested value")
        elif fieldinfo[FIELD_LEN] > 2 and len(payload) != fieldinfo[FIELD_LEN]:
            #greater than two byte field, payload length must match field length
            raise ValueError("set_field: invalid payload length")

        #checks the payload matches the ranges if ranges are defined
        ranges = fieldinfo[FIELD_RANGE]
        if ranges != []:
            if isinstance(payload, (int, long)):
                if payload < ranges[0] or payload > ranges[1]:
                    raise ValueError("set_field: payload out of range")
            else:
                for i, item in enumerate(payload):
                    rangepair = ranges[i % len(ranges)]
                    if item < rangepair[0] or item > rangepair[1]:
                        raise ValueError("set_field: payload out of range")
    
    ## External functions for printing data
    def display_heating_schedule(self):
        """Prints heating schedule to stdout"""
        self.heat_schedule.display()
            
    def display_water_schedule(self):
        """Prints water schedule to stdout"""
        if not self.water_schedule is None:
            self.water_schedule.display()

    def print_target(self):
        """Returns text describing current heating state"""    
        current_state = self.read_temp_state()
        
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
            nexttarget = self.heat_schedule.get_next_schedule_item(locatimenow)
            return "temp overridden to %0.1f until %02d:%02d" % (self.setroomtemp, nexttarget[1], nexttarget[2])
        elif current_state == self.TEMP_STATE_PROGRAM:
            locatimenow = self._localtimearray()
            nexttarget = self.heat_schedule.get_next_schedule_item(locatimenow)
            return "temp set to %0.1f until %02d:%02d" % (self.setroomtemp, nexttarget[1], nexttarget[2])
    
    ## External functions for reading data

    def is_hot_water(self):
        """Does device manage hotwater?"""
        #returns True if stat is a model with hotwater control, False otherwise
        return self.expected_model == 'prt_hw_model'

    TEMP_STATE_OFF = 0    #thermostat display is off and frost protection disabled
    TEMP_STATE_OFF_FROST = 1 #thermostat display is off and frost protection enabled
    TEMP_STATE_FROST = 2 #frost protection enabled indefinitely
    TEMP_STATE_HOLIDAY = 3 #holiday mode, frost protection for a period
    TEMP_STATE_HELD = 4 #temperature held for a number of hours
    TEMP_STATE_OVERRIDDEN = 5 #temperature overridden until next program time
    TEMP_STATE_PROGRAM = 6 #following program
    
    def read_temp_state(self):
        """Returns the current temperature control state from off to following program"""
        self.read_fields(['mon_heat', 'tues_heat', 'wed_heat', 'thurs_heat', 'fri_heat', 'wday_heat', 'wend_heat'], -1)
        self.read_fields(['onoff', 'frostprot', 'holidayhours', 'runmode', 'tempholdmins', 'setroomtemp'])
        
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
        
            if not self._check_data_age(['currenttime'], MAX_AGE_MEDIUM):
                self.read_time()
            
            locatimenow = self._localtimearray()
            scheduletarget = self.heat_schedule.get_current_schedule_item(locatimenow)

            if scheduletarget[SCH_ENT_TEMP] != self.setroomtemp:
                return self.TEMP_STATE_OVERRIDDEN
            else:
                return self.TEMP_STATE_PROGRAM

    ### UNTESTED # last part about scheduletarget doesn't work
    def read_water_state(self):
        """Returns the current hot water control state from off to following program"""
        #does runmode affect hot water state?
        self.read_fields(['mon_water', 'tues_water', 'wed_water', 'thurs_water', 'fri_water', 'wday_water', 'wend_water'], -1)
        self.read_fields(['onoff', 'holidayhours', 'hotwaterdemand'])
        
        if self.onoff == WRITE_ONOFF_OFF:
            return self.TEMP_STATE_OFF
        elif self.holidayhours != 0:
            return self.TEMP_STATE_HOLIDAY
        else:
        
            if not self._check_data_age(['currenttime'], MAX_AGE_MEDIUM):
                self.read_time()
            
            locatimenow = self._localtimearray()
            scheduletarget = self.water_schedule.get_current_schedule_item(locatimenow)

            if scheduletarget[SCH_ENT_TEMP] != self.hotwaterdemand:
                return self.TEMP_STATE_OVERRIDDEN
            else:
                return self.TEMP_STATE_PROGRAM
                
    def read_air_sensor_type(self):
        """Reports airsensor type"""
        #1 local, 3 remote
        if not self._check_data_present('sensorsavaliable'):
            return False

        if self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_FLOOR:
            return 1
        elif self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_FLOOR:
            return 2
        else:
            return 0
            
    def read_air_temp(self):
        """Read the air temperature getting data from device if too old"""
        #if not read before read sensorsavaliable field
        self.read_field('sensorsavaliable', None)
        
        if self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_INT_FLOOR:
            return self.read_field('airtemp', self.max_age_temp)
        elif self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_ONLY or self.sensorsavaliable == READ_SENSORS_AVALIABLE_EXT_FLOOR:
            return self.read_field('remoteairtemp', self.max_age_temp)
        else:
            raise ValueError("sensorsavaliable field invalid")
    
    def read_raw_data(self, startfieldname=None, endfieldname=None):
        """Return subset of raw data"""
        if startfieldname == None or endfieldname == None:
            return self.rawdata
        else:
            return self.rawdata[self._get_dcb_address(uniadd[startfieldname][UNIADD_ADD]):self._get_dcb_address(uniadd[endfieldname][UNIADD_ADD])]
        
    def read_time(self, maxage=0):
        """Readtime, getting from device if required"""
        return self.read_field('currenttime', maxage)
        
    ## External functions for setting data

    def set_heating_schedule(self, day, schedule):
        """Set heating schedule for a single day"""
        padschedule = self.heat_schedule.pad_schedule(schedule)
        self.set_field(day, padschedule)
            
    def set_water_schedule(self, day, schedule):
        """Set water schedule for a single day"""
        padschedule = self.water_schedule.pad_schedule(schedule)
        if day == 'all':
            self.set_field('mon_water', padschedule)
            self.set_field('tues_water', padschedule)
            self.set_field('wed_water', padschedule)
            self.set_field('thurs_water', padschedule)
            self.set_field('fri_water', padschedule)
            self.set_field('sat_water', padschedule)
            self.set_field('sun_water', padschedule)
        else:
            self.set_field(day, padschedule)

    def set_time(self):
        """set time on device to match current localtime on server"""
        timenow = time.time() + 0.5 #allow a little time for any delay in setting
        return self.set_field('currenttime', self._localtimearray(timenow))

    #overriding

    def set_temp(self, temp):
        """sets the temperature demand overriding the program."""
        #Believe it returns at next prog change.
        if self.read_field('tempholdmins') == 0: #check hold temp not applied
            return self.set_field('setroomtemp', temp)
        else:
            logging.warn("%i address, temp hold applied so won't set temp"%(self.address))

    def release_temp(self):
        """release setTemp back to the program, but only if temp isn't held for a time (holdTemp)."""
        if self.read_field('tempholdmins') == 0: #check hold temp not applied
            return self.set_field('tempholdmins', 0)
        else:
            logging.warn("%i address, temp hold applied so won't remove set temp"%(self.address))

    def hold_temp(self, minutes, temp):
        """sets the temperature demand overrding the program for a set time."""
        #Believe it then returns to program.
        self.set_field('setroomtemp', temp)
        return self.set_field('tempholdmins', minutes)
        #didn't stay on if did minutes followed by temp.
        
    def release_hold_temp(self):
        """release setTemp or holdTemp back to the program."""
        return self.set_field('tempholdmins', 0)
        
    def set_holiday(self, hours):
        """sets holiday up for a defined number of hours."""
        return self.set_field('holidayhours', hours)
    
    def release_holiday(self):
        """cancels holiday mode"""
        return self.set_field('holidayhours', 0)

    #onoffs

    def set_on(self):
        """Switch stat on"""
        return self.set_field('onoff', WRITE_ONOFF_ON)
    def set_off(self):
        """Switch stat off"""
        return self.set_field('onoff', WRITE_ONOFF_OFF)
        
    def set_heat(self):
        """Switch stat to follow heat program"""
        return self.set_field('runmode', WRITE_RUNMODE_HEATING)
    def set_frost(self):
        """Switch stat to frost only"""
        return self.set_field('runmode', WRITE_RUNMODE_FROST)
        
    def set_lock(self):
        """Lock keypad"""
        return self.set_field('keylock', WRITE_KEYLOCK_ON)
    def set_unlock(self):
        """Unlock keypad"""
        return self.set_field('keylock', WRITE_KEYLOCK_OFF)
    
#other
#set floor limit

class HeatmiserUnknownDevice(HeatmiserDevice):
    """Device class for unknown thermostats"""
    
    def _update_settings(self, settings, generalsettings):
        """Check settings and get network data if needed"""

        self._load_settings(settings, generalsettings)
        
        # some basic config required before reading fields
        self._uniquetodcb = range(MAX_UNIQUE_ADDRESS + 1)
        self.rawdata = [None] * (MAX_UNIQUE_ADDRESS + 1)
        # assume fullreadtime is the worst case
        self.fullreadtime = self._estimate_read_time(MAX_UNIQUE_ADDRESS) 
        # use fields from device rather to set the expected mode and type
        self.read_fields(['model', 'programmode'], 0)
        self.expected_model = DEVICE_MODELS.keys()[DEVICE_MODELS.values().index(self.model)]
        self.expected_prog_mode = PROG_MODES.keys()[PROG_MODES.values().index(self.programmode)]
        
        self._process_settings()

class HeatmiserBroadcastDevice(HeatmiserDevice):
    """Broadcast device class for broadcast set functions and managing reading on all devices"""
    #List wrapper used to provide arguement to dectorator
    _controllerlist = ListWrapperClass()

    def __init__(self, network, long_name, controllerlist=None):
        self._controllerlist.list = controllerlist
        settings = {
            'address':BROADCAST_ADDR,
            'display_order': 0,
            'long_name': long_name,
            'protocol':DEFAULT_PROTOCOL,
            'expected_model':False,
            'expected_prog_mode':DEFAULT_PROG_MODE
            }
        super(HeatmiserBroadcastDevice, self).__init__(network, settings)
    
    #run read functions on all stats
    @run_function_on_all(_controllerlist)
    def read_field(self, fieldname, maxage=None):
        logging.info("All reading %s from %i controllers"%(fieldname, len(self._controllerlist.list)))
            
    @run_function_on_all(_controllerlist)
    def read_fields(self, fieldnames, maxage=None):
        logging.info("All reading %s from %i controllers"%(', '.join([fieldname for fieldname in fieldnames]), len(self._controllerlist.list)))
        
    @run_function_on_all(_controllerlist)
    def read_air_temp(self):
        pass
    
    @run_function_on_all(_controllerlist)
    def read_temp_state(self):
        pass
    
    @run_function_on_all(_controllerlist)
    def read_water_state(self):
        pass
    
    @run_function_on_all(_controllerlist)
    def read_air_sensor_type(self):
        pass
            
    @run_function_on_all(_controllerlist)
    def read_time(self, maxage=0):
        pass
    
    #run set functions which require a read on all stats
    @run_function_on_all(_controllerlist)
    def set_temp(self, temp):
        pass
    
    @run_function_on_all(_controllerlist)
    def release_temp(self):
        pass

