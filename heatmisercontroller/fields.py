"""generic field definitions for Heatmiser protocol"""
import logging
import time

from .hm_constants import BYTEMASK
from .exceptions import HeatmiserResponseError
from .observer import Notifier

VALUES_ON_OFF = {'ON': 1, 'OFF': 0} #assusme that default comes first, need to swtich to ordered dictionary to make it possible to get default value
VALUES_OFF_ON = {'OFF': 0, 'ON': 1}
VALUES_OFF = {'OFF': 0}

class HeatmiserFieldUnknown(Notifier):
    """Class for variable length unknown read only field"""
    writeable = False
    divisor = 1

    def __init__(self, name, address, max_age, length):
        super(HeatmiserFieldUnknown, self).__init__()
        self.name = name
        self.address = address
        self.dcbaddress = address
        self.max_age = max_age
        self.fieldlength = length
        self._reset()

    def __int__(self):
        return self.value

    def __eq__(self, other):
        return self.value == other

    def __repr__(self):
        return str(self.value)

    def __lt__(self, value):
        return self.value < value

    def __le__(self, value):
        return self.value <= value

    def __gt__(self, value):
        return self.value > value

    def __ge__(self, value):
        return self.value >= value

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

    def update_value(self, value, writetime):
        """Don't update because don't know how to map to data."""
        raise NotImplementedError

    def get_value(self):
        """Return value."""
        return self.value
        
    def is_writable(self):
        """Checks if field is writable"""
        if not self.writeable:
            raise ValueError("set_field: field isn't writeable")

    def check_values(self, values):
        """check a payload matches field spec"""
        raise NotImplementedError

    def check_data_valid(self):
        """check whether data has been set"""
        data_not_valid = self.lastreadtime is None
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
        elif maxagein is None: #if none use field defaults
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
    writeable = True
    fieldlength = 0

    def __init__(self, name, address, validrange, max_age, readvalues=None):
        ###valid range list can be [], [min, max], [list of valid values]
        super(HeatmiserField, self).__init__(name, address, max_age, self.fieldlength)
        self.validrange = validrange
        self.value = None
        self.expectedvalue = None
        self.writevalues = self.readvalues = readvalues
        #check isinstance(fieldrange[0], (int, long)) and isinstance(fieldrange[1], (int, long))
        if len(validrange) < 2:
            self.validrange = [0, self.maxdatavalue / self.divisor]

    def is_value(self, name):
        """Returns true if value matches read value."""
        return self.value == self.readvalues[name]

    def is_unknown(self):
        """Returns true if value isn't set."""
        return self.value is None

    def read_value_text(self):
        """returns value converting to label if known"""
        if self.readvalues is None:
            return self.value
        else:
            return list(self.readvalues.keys())[list(self.readvalues.values()).index(self.value)]

    def write_value_from_text(self, value):
        """maps text to value, otherwise returns input"""
        if self.writevalues is None:
            return value
        else:
            return self.writevalues.get(value, value)

    def update_data(self, data, readtime):
        """update stored data and readtime if data valid. Compute and store value from data."""
        value = self._calculate_value(data)
        if self.expectedvalue is not None and value != self.expectedvalue:
            raise HeatmiserResponseError('Value %i is unexpected for %s, expected %i'%(value, self.name, self.expectedvalue))
        self._validate_range(value)
        self.data = data
        self.value = value
        self.lastreadtime = readtime
        self.notify_value_change(value)

    def update_value(self, value, writetime):
        """Update the field value once successfully written to network"""
        self._validate_range(value, ValueError)
        data = self.format_data_from_value(value)
        self.data = data
        self.value = value
        self.lastreadtime = writetime
        self.notify_value_change(value)

    def _validate_range(self, values, errortype=HeatmiserResponseError, expectedrange=None):
        """validate the value is within range or in list."""
        if expectedrange is None:
            expectedrange = self.validrange

        if len(expectedrange) == 2:
            if values < expectedrange[0] or values > expectedrange[1]:
                raise errortype("Value %.1f  outside expected range (%.1f, %.1f) for %s"%(values, expectedrange[0], expectedrange[1], self.name))
        elif len(expectedrange) > 2:
            if values not in expectedrange:
                raise errortype("Value %.1f  outside expected range %s for %s"%(values, ','.join(map(str, expectedrange)), self.name))
        else:
            raise errortype("Expected range not defined for %s"%(self.name))

    def _calculate_value(self, data):
        """Calculate value from payload bytes"""
        raise NotImplementedError

    def format_data_from_value(self, value):
        """Convert field to byte form for writting to device"""
        raise NotImplementedError

    def check_values(self, values):
        """check a single or double byte field value matches field spec"""
        if not isinstance(values, int):
            #one or two byte field, not single length values
            raise TypeError("set_field: invalid requested value")

        #checks the values matches the ranges if ranges are defined
        self._validate_range(values, ValueError)

class HeatmiserFieldSingle(HeatmiserField):
    """Class for writable 1 byte field"""
    maxdatavalue = 255
    fieldlength = 1

    def _calculate_value(self, data):
        """Calculate value from payload bytes"""
        return data[0]/self.divisor

    def format_data_from_value(self, value):
        """Convert field to byte form for writting to device"""
        return [value]

class HeatmiserFieldSingleReadOnly(HeatmiserFieldSingle):
    """Class for read only 1 byte field"""
    writeable = False

class HeatmiserFieldDouble(HeatmiserField):
    """Class for writable 2 byte field"""
    maxdatavalue = 65535
    fieldlength = 2

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
    writeable = False

class HeatmiserFieldDoubleReadOnlyTenths(HeatmiserFieldDoubleReadOnly):
    """Class for read only 2 byte field"""
    divisor = 10.0

class HeatmiserFieldMulti(HeatmiserField):
    """Base class for writable multi byte field"""
    maxdatavalue = None

    def _validate_range(self, values, errortype=HeatmiserResponseError, expectedrange=None):
        """validate the value is within range or in list. cyles through list of ranges"""
        for i, item in enumerate(values):
            expectedrange = self.validrange[i % len(self.validrange)]
            super(HeatmiserFieldMulti, self)._validate_range(item, errortype, expectedrange)

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
