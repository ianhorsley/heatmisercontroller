"""field definitions for Heatmiser protocol"""
import logging
import time

from .hm_constants import WRITE_HOTWATERDEMAND_PROG, WRITE_HOTWATERDEMAND_OVER_OFF, READ_HOTWATERDEMAND_OFF
from hm_constants import CURRENT_TIME_DAY, CURRENT_TIME_HOUR, CURRENT_TIME_MIN, CURRENT_TIME_SEC, TIME_ERR_LIMIT
from hm_constants import BYTEMASK
from .exceptions import HeatmiserResponseError, HeatmiserControllerTimeError

class HeatmiserFieldUnknown(object):
    """Class for variable length unknown read only field"""
    def __init__(self, name, address, max_age, length):
        self.name = name
        self.address = address
        self.dcbaddress = address
        self.divisor = 1
        self.max_age = max_age
        self.writeable = False
        self.fieldlength = length
        self._reset()
    
    def __eq__(self, other):
        return self.value == other
        
    def __int__(self):
        return self.value

    def __str__(self):
        return str(self.value)

    def _reset(self):
        """Reset data and values to unknown."""
        self.data = None
        self.value = None
        self.lastreadtime = None #used to record when the field was last read
    
    def last_dcb_byte_address(self):
        """returns the address of the last dcb byte"""
        return self.dcbaddress + self.fieldlength - 1
    
    def update_data(self, data, readtime):
        """update stored data and readtime. Don't compute value because don't know how to map"""
        self.data = data
        self.lastreadtime = readtime
        return data
    
    def update_value(self, value, writetime):
        """Don't update because don't know how to map to data."""
        raise NotImplementedError

    def is_writable(self):
        """Checks if field is writable"""
        if not self.writeable:
            raise ValueError("set_field: field isn't writeable")

    def check_values(self, values):
        """check a payload matches field spec"""
        raise NotImplementedError
        
    def check_data_valid(self):
        """check whether data has been set"""
        data_not_valid = self.lastreadtime == None
        if data_not_valid:
            logging.debug("Data item %s not available"%(self.name))
        return not data_not_valid
        
    def check_data_fresh(self, maxagein=None):
        """check whether data is fresh
        
        Check field data age is not more than maxage (in seconds)
        maxagein = None, use the default self.maxage
        maxagein = -1, only check if present
        maxagein >=0, use maxagein (0 is effectively always False)
        return False if old, True if recent"""
        if not self.check_data_valid():
            return False
        elif maxagein == -1: #only check present
            return True
        elif maxagein == None: #if none use field defaults
            maxage = self.max_age
        else:
            maxage = maxagein
        #now check time
        if time.time() - self.lastreadtime > maxage:
            logging.debug("Data item %s too old"%(self.name))
            return False
        return True
        
class HeatmiserField(HeatmiserFieldUnknown):
    """Base class for fields providing basic method calls"""
    #single value and hence single range
    def __init__(self, name, address, validrange, max_age):
        super(HeatmiserField, self).__init__(name, address, max_age, self.fieldlength)
        self.validrange = validrange
        self.writeable = True
        self.value = None
        self.expectedvalue = None
        #check isinstance(fieldrange[0], (int, long)) and isinstance(fieldrange[1], (int, long))
        if len(validrange) < 2:
            self.validrange = [0, self.maxdatavalue / self.divisor]
    
    def update_data(self, data, readtime):
        """update stored data and readtime if data valid. Compute and store value from data."""
        value = self._calculate_value(data)
        if not self.expectedvalue is None and value != self.expectedvalue:
            raise HeatmiserResponseError('Value %i is unexpected for %s, expected %i'%(value, self.name, self.expectedvalue))
        self._validate_range(value)
        self.data = data
        self.value = value
        self.lastreadtime = readtime
        return value

    def update_value(self, value, writetime):
        """Update the field value once successfully written to network"""
        self._validate_range(value, ValueError)
        data = self.format_data_from_value(value)
        self.data = data
        self.value = value
        self.lastreadtime = writetime
        return value
        
    def _validate_range(self, values, errortype=HeatmiserResponseError):
        """validate the value is within range."""
        if values < self.validrange[0] or values > self.validrange[1]:
            raise errortype("Value %i outside expected range for %s"%(values, self.name))

    def _calculate_value(self, data):
        """Calculate value from payload bytes"""
        raise NotImplementedError
        
    def format_data_from_value(self, value):
        """Convert field to byte form for writting to device"""
        raise NotImplementedError
        
    def check_values(self, values):
        """check a single or double byte field value matches field spec"""
        if not isinstance(values, (int, long)):
            #one or two byte field, not single length values
            raise TypeError("set_field: invalid requested value")

        #checks the values matches the ranges if ranges are defined
        self._validate_range(values, ValueError)

class HeatmiserFieldSingle(HeatmiserField):
    """Class for writable 1 byte field"""
    def __init__(self, name, address, validrange, max_age):
        self.maxdatavalue = 255
        self.fieldlength = 1
        super(HeatmiserFieldSingle, self).__init__(name, address, validrange, max_age)

    def _calculate_value(self, data):
        """Calculate value from payload bytes"""
        return data[0]/self.divisor
    
    def format_data_from_value(self, value):
        """Convert field to byte form for writting to device"""
        return [value]

class HeatmiserFieldSingleReadOnly(HeatmiserFieldSingle):
    """Class for read only 1 byte field"""
    def __init__(self, name, address, validrange, max_age):
        super(HeatmiserFieldSingleReadOnly, self).__init__(name, address, validrange, max_age)
        self.writeable = False

class HeatmiserFieldHotWaterVersion(HeatmiserFieldSingleReadOnly):
    """Class for version on hotwater models."""
    def __init__(self, name, address, validrange, max_age):
        super(HeatmiserFieldHotWaterVersion, self).__init__(name, address, validrange, max_age)
        self.floorlimiting = None
        
    def _calculate_value(self, data):
        """Calculate value from payload bytes"""
        self.floorlimiting = data[0] >> 7
        return data[0] & 0x7f
        
class HeatmiserFieldHotWaterDemand(HeatmiserFieldSingle):
    """Class to impliment read and write differences for hotwater demand field."""
    def __init__(self, name, address, validrange, max_age):
        super(HeatmiserFieldHotWaterDemand, self).__init__(name, address, validrange, max_age)

    def update_value(self, value, writetime):
        """Update the field value once successfully written to network if known. Otherwise reset"""
        #handle odd effect on WRITE_hotwaterdemand_PROG
        
        if value == WRITE_HOTWATERDEMAND_PROG: #returned to program so outcome is unknown
            self._reset()
            return None
        elif value == WRITE_HOTWATERDEMAND_OVER_OFF: #if overridden off store the off read value
            return super(HeatmiserFieldHotWaterDemand, self).update_value(READ_HOTWATERDEMAND_OFF, writetime)
        else:
            return super(HeatmiserFieldHotWaterDemand, self).update_value(value, writetime)
        
class HeatmiserFieldDouble(HeatmiserField):
    """Class for writable 2 byte field"""
    def __init__(self, name, address, validrange, max_age):
        self.maxdatavalue = 65536
        self.fieldlength = 2
        super(HeatmiserFieldDouble, self).__init__(name, address, validrange, max_age)
        
    def _calculate_value(self, data):
        """Calculate value from payload bytes"""
        val_high = data[0]
        val_low = data[1]
        return 1.0*(val_high*256 + val_low)/self.divisor #force float, although always returns integer temps.

    def format_data_from_value(self, value):
        """Convert field to byte form for writting to device"""
        pay_lo = (value & BYTEMASK)
        pay_hi = (value >> 8) & BYTEMASK
        return [pay_lo, pay_hi]
        
class HeatmiserFieldDoubleReadOnly(HeatmiserFieldDouble):
    """Class for read only 2 byte field"""
    def __init__(self, name, address, validrange, max_age):
        super(HeatmiserFieldDoubleReadOnly, self).__init__(name, address, validrange, max_age)
        self.writeable = False

class HeatmiserFieldDoubleReadOnlyTenths(HeatmiserFieldDoubleReadOnly):
    """Class for read only 2 byte field"""
    def __init__(self, name, address, validrange, max_age):
        super(HeatmiserFieldDoubleReadOnlyTenths, self).__init__(name, address, validrange, max_age)
        self.divisor = 10
        
class HeatmiserFieldMulti(HeatmiserField):
    """Base class for writable multi byte field"""
    def __init__(self, name, address, validrange, max_age):
        self.maxdatavalue = None
        super(HeatmiserFieldMulti, self).__init__(name, address, validrange, max_age)
        
    def _validate_range(self, values, errortype=HeatmiserResponseError):
        """validate the value is within range."""
        for i, item in enumerate(values):
            rangepair = self.validrange[i % len(self.validrange)]
            if item < rangepair[0] or item > rangepair[1]:
                raise errortype("Value %i outside expected range for %s"%(item, self.name))
        
    def _calculate_value(self, data):
        """Calculate value from payload bytes"""
        return data

    def format_data_from_value(self, value):
        """Convert field to byte form for writting to device"""
        return list(value) #force a copy
    
    def check_values(self, values):
        """check a values matches field spec"""
        if len(values) != self.fieldlength:
            #greater than two byte field, values length must match field length
            raise ValueError("set_field: invalid payload length")

        #checks the values matches the ranges if ranges are defined
        self._validate_range(values, ValueError)

class HeatmiserFieldTime(HeatmiserFieldMulti):
    """Class for time field"""
    def __init__(self, name, address, validrange, max_age):
        self.fieldlength = 4
        self.timeerr = None
        super(HeatmiserFieldTime, self).__init__(name, address, validrange, max_age)
        
    def comparecontrollertime(self):
        """Compare device and local time difference against threshold"""
        # Now do same sanity checking
        # Check the time is within range
        # currentday is numbered 1-7 for M-S
        # localday (python) is numbered 0-6 for Sun-Sat
        
        if not self.check_data_valid():
            raise HeatmiserResponseError("Time not read before check")

        localtimearray = self.localtimearray(self.lastreadtime) #time that time field was read
        localweeksecs = self._weeksecs(localtimearray)
        remoteweeksecs = self._weeksecs(self.value)
        directdifference = abs(localweeksecs - remoteweeksecs)
        wrappeddifference = abs(self.DAYSECS * 7 - directdifference) #compute the difference on rollover
        self.timeerr = min(directdifference, wrappeddifference)
        logging.debug("Local time %i, remote time %i, error %i"%(localweeksecs, remoteweeksecs, self.timeerr))

        if self.timeerr > self.DAYSECS:
            raise HeatmiserControllerTimeError("C%2d Incorrect day : local is %s, sensor is %s" % (self.address, localtimearray[CURRENT_TIME_DAY], self.value[CURRENT_TIME_DAY]))

        if self.timeerr > TIME_ERR_LIMIT:
            raise HeatmiserControllerTimeError("C%2d Time Error %d greater than %d: local is %s, sensor is %s" % (self.address, self.timeerr, TIME_ERR_LIMIT, localweeksecs, remoteweeksecs))

    @staticmethod
    def localtimearray(timenow=time.time()):
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

class HeatmiserFieldHeat(HeatmiserFieldMulti):
    """Class for heating schedule field"""
    def __init__(self, name, address, validrange, max_age):
        self.fieldlength = 12
        super(HeatmiserFieldHeat, self).__init__(name, address, validrange, max_age)

class HeatmiserFieldWater(HeatmiserFieldMulti):
    """Class for hotwater schedule field"""
    def __init__(self, name, address, validrange, max_age):
        self.fieldlength = 16
        super(HeatmiserFieldWater, self).__init__(name, address, validrange, max_age)
