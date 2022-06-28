"""special field definitions for Heatmiser protocol"""
import logging
import time

from .fields import HeatmiserFieldSingle, HeatmiserFieldSingleReadOnly, HeatmiserFieldMulti
from .fields import VALUES_ON_OFF
from .hm_constants import CURRENT_TIME_DAY, CURRENT_TIME_HOUR, CURRENT_TIME_MIN, CURRENT_TIME_SEC, TIME_ERR_LIMIT
from .exceptions import HeatmiserResponseError, HeatmiserControllerTimeError

class HeatmiserFieldHotWaterVersion(HeatmiserFieldSingleReadOnly):
    """Class for version on hotwater models."""
    floorlimiting = None

    def _calculate_value(self, data):
        """Calculate value from payload bytes"""
        self.floorlimiting = data[0] >> 7
        return data[0] & 0x7f

class HeatmiserFieldHotWaterDemand(HeatmiserFieldSingle):
    """Class to impliment read and write differences for hotwater demand field."""
    def __init__(self, name, address, validrange, max_age):
        super(HeatmiserFieldHotWaterDemand, self).__init__(name, address, validrange, max_age, VALUES_ON_OFF)
        self.writevalues = {'PROG': 0, 'OVER_ON': 1, 'OVER_OFF': 2}

    def update_value(self, value, writetime):
        """Update the field value once successfully written to network if known. Otherwise reset"""
        #handle odd effect on WRITE_hotwaterdemand_PROG

        if value == self.writevalues['PROG']: #returned to program so outcome is unknown
            self._reset()
        elif value == self.writevalues['OVER_OFF']: #if overridden off store the off read value
            super(HeatmiserFieldHotWaterDemand, self).update_value(self.readvalues['OFF'], writetime)
        else:
            super(HeatmiserFieldHotWaterDemand, self).update_value(value, writetime)

class HeatmiserFieldTime(HeatmiserFieldMulti):
    """Class for time field"""
    fieldlength = 4

    def __init__(self, name, address, max_age):
        self.timeerr = None
        validrange = [[1, 7], [0, 23], [0, 59], [0, 59]] #fixed because functions depend on this range.
        super(HeatmiserFieldTime, self).__init__(name, address, validrange, max_age)

    def get_value(self):
        """Return estimated remote time."""
        estimate = time.time() + self.timeerr
        return self.localtimearray(estimate)

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
        directdifference = remoteweeksecs - localweeksecs #absolute remote time relative to local time
        wrappeddifferenceup = directdifference - self.DAYSECS * 7 #compute the absolute difference on rollover
        wrappeddifferencedown = directdifference + self.DAYSECS * 7 #compute the absolute difference on rollover
        self.timeerr = min([directdifference, wrappeddifferenceup, wrappeddifferencedown], key=abs)
        logging.debug("Local time %i, remote time %i, error %i"%(localweeksecs, remoteweeksecs, self.timeerr))

        if abs(self.timeerr) > self.DAYSECS:
            raise HeatmiserControllerTimeError("Incorrect day : local is %s, sensor is %s" % (localtimearray[CURRENT_TIME_DAY], self.value[CURRENT_TIME_DAY]))

        if abs(self.timeerr) > TIME_ERR_LIMIT:
            raise HeatmiserControllerTimeError("Time Error %d greater than %d: local is %s, sensor is %s" % (self.timeerr, TIME_ERR_LIMIT, localweeksecs, remoteweeksecs))

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
    fieldlength = 12

class HeatmiserFieldWater(HeatmiserFieldMulti):
    """Class for hotwater schedule field"""
    fieldlength = 16
