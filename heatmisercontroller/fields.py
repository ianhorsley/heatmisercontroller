"""field definitions for Heatmiser protocol"""
import logging
import time

from .hm_constants import WRITE_HOTWATERDEMAND_PROG, WRITE_HOTWATERDEMAND_OVER_OFF, READ_HOTWATERDEMAND_OFF
from .exceptions import HeatmiserResponseError

class HeatmiserFieldUnknown(object):
    """Class for variable length unknown read only field"""
    def __init__(self, name, address, divisor, validrange, max_age, length):
        self.name = name
        self.address = address
        self.dcbaddress = address
        self.divisor = divisor
        self.validrange = validrange
        self.max_age = max_age
        self.writeable = False
        self.fieldlength = length
        self._reset()
    
    def __eq__(self, other):
        return self.value == other
        
    def __int__(self):
        return self.value
        
    #def __repr__(self):
    #    return str(self.value)
     
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

    def check_payload_values(self, payload):
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
    def __init__(self, name, address, divisor, validrange, max_age):
        super(HeatmiserField, self).__init__(name, address, divisor, validrange, max_age, self.fieldlength)
        self.writeable = True
        self.value = None
        self.expectedvalue = None
        #check isinstance(fieldrange[0], (int, long)) and isinstance(fieldrange[1], (int, long))
        if len(validrange) < 2:
            self.validrange = [0, self.maxdatavalue * divisor]
    
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
        self._validate_range(value)
        data = self.format_data_from_value(value)
        self.data = data
        self.value = value
        self.lastreadtime = writetime
        return value
        
    def _validate_range(self, values):
        """validate the value is within range."""
        if values < self.validrange[0] or values > self.validrange[1]:
            raise HeatmiserResponseError("Value %i outside expected range for %s"%(values, self.name))

    def _calculate_value(self, data):
        """Calculate value from payload bytes"""
        raise NotImplementedError
        
    def format_data_from_value(self, value):
        """Convert field to byte form for writting to device"""
        raise NotImplementedError
        
    def check_payload_values(self, payload):
        """check a single field payload matches field spec"""
        if not isinstance(payload, (int, long)):
            #one or two byte field, not single length payload
            raise TypeError("set_field: invalid requested value")

        #checks the payload matches the ranges if ranges are defined
        if payload < self.validrange[0] or payload > self.validrange[1]:
            raise ValueError("Value %i outside expected range for %s"%(payload, self.name))

class HeatmiserFieldSingle(HeatmiserField):
    """Class for writable 1 byte field"""
    def __init__(self, name, address, divisor, validrange, max_age):
        self.maxdatavalue = 255
        self.fieldlength = 1
        super(HeatmiserFieldSingle, self).__init__(name, address, divisor, validrange, max_age)

    def _calculate_value(self, data):
        """Calculate value from payload bytes"""
        return data[0]/self.divisor
    
    def format_data_from_value(self, value):
        """Convert field to byte form for writting to device"""
        return [value]

class HeatmiserFieldSingleReadOnly(HeatmiserFieldSingle):
    """Class for read only 1 byte field"""
    def __init__(self, name, address, divisor, validrange, max_age):
        super(HeatmiserFieldSingleReadOnly, self).__init__(name, address, divisor, validrange, max_age)
        self.writeable = False

class HeatmiserFieldHotWaterDemand(HeatmiserFieldSingle):
    """Class to impliment read and write differences for hotwater demand field."""
    def __init__(self, name, address, divisor, validrange, max_age):
        super(HeatmiserFieldHotWaterDemand, self).__init__(name, address, divisor, validrange, max_age)

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
    def __init__(self, name, address, divisor, validrange, max_age):
        self.maxdatavalue = 65536
        self.fieldlength = 2
        super(HeatmiserFieldDouble, self).__init__(name, address, divisor, validrange, max_age)
        
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
    def __init__(self, name, address, divisor, validrange, max_age):
        super(HeatmiserFieldDoubleReadOnly, self).__init__(name, address, divisor, validrange, max_age)
        self.writeable = False
        
class HeatmiserFieldMulti(HeatmiserField):
    """Base class for writable multi byte field"""
    def __init__(self, name, address, divisor, validrange, max_age):
        self.maxdatavalue = None
        super(HeatmiserFieldMulti, self).__init__(name, address, divisor, validrange, max_age)
        
    def _validate_range(self, values):
        """validate the value is within range."""
        for i, item in enumerate(values):
            rangepair = self.validrange[i % len(self.validrange)]
            if item < rangepair[0] or item > rangepair[1]:
                raise HeatmiserResponseError("Value %i outside expected range for %s"%(item, self.name))
        
    def _calculate_value(self, data):
        """Calculate value from payload bytes"""
        return data

    def format_data_from_value(self, value):
        """Convert field to byte form for writting to device"""
        return list(value) #force a copy
    
    def check_payload_values(self, payload):
        """check a payload matches field spec"""
        if len(payload) != self.fieldlength:
            #greater than two byte field, payload length must match field length
            raise ValueError("set_field: invalid payload length")

        #checks the payload matches the ranges if ranges are defined
        for i, item in enumerate(payload):
            rangepair = self.validrange[i % len(self.validrange)]
            if item < rangepair[0] or item > rangepair[1]:
                raise ValueError("Value %i outside expected range for %s"%(item, self.name))

class HeatmiserFieldTime(HeatmiserFieldMulti):
    """Class for time field"""
    def __init__(self, name, address, divisor, validrange, max_age):
        self.fieldlength = 4
        super(HeatmiserFieldTime, self).__init__(name, address, divisor, validrange, max_age)

class HeatmiserFieldHeat(HeatmiserFieldMulti):
    """Class for heating schedule field"""
    def __init__(self, name, address, divisor, validrange, max_age):
        self.fieldlength = 12
        super(HeatmiserFieldHeat, self).__init__(name, address, divisor, validrange, max_age)

class HeatmiserFieldWater(HeatmiserFieldMulti):
    """Class for hotwater schedule field"""
    def __init__(self, name, address, divisor, validrange, max_age):
        self.fieldlength = 16
        super(HeatmiserFieldWater, self).__init__(name, address, divisor, validrange, max_age)
