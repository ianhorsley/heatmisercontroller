"""Heatmiser Device Classes

PRT-E Thermostat classes on the Heatmiser network

Ian Horsley 2018
"""
import logging
import time

from .genericdevice import HeatmiserDevice, DEVICETYPES
from .fields import HeatmiserFieldSingle, HeatmiserFieldSingleReadOnly, HeatmiserFieldDouble, HeatmiserFieldDoubleReadOnly, HeatmiserFieldDoubleReadOnlyTenths
from .fields_special import HeatmiserFieldTime, HeatmiserFieldHeat
from .fields import VALUES_ON_OFF, VALUES_OFF_ON, VALUES_OFF
from .hm_constants import MAX_AGE_LONG, MAX_AGE_MEDIUM, MAX_AGE_SHORT, MAX_AGE_USHORT
from .exceptions import HeatmiserControllerTimeError, HeatmiserControllerSensorError
from .schedule_functions import SchedulerDayHeat, SchedulerWeekHeat
from .thermostatstate import Thermostat

class ThermoStatWeek(HeatmiserDevice):
    """Device class for thermostats operating weekly programmode
    Heatmiser prt_e_model."""
    is_hot_water = False #returns True if stat is a model with hotwater control, False otherwise
    
    def __init__(self, adaptor, devicesettings, generalsettings=None):
        self.heat_schedule = None #placeholder for heating schedule object
        self.thermostat = None #placeholder for thermostat object
        super(ThermoStatWeek, self).__init__(adaptor, devicesettings, generalsettings)
        #thermostat specific

    def _buildfields(self):
        """add to list of fields"""
        super(ThermoStatWeek, self)._buildfields()
        # list of fields can be sorted by key
        # dcb addresses could be computed from the completed field list and added to field.
        # all should have the first 4 fields, so put these in generic
        self.fields.extend([
            HeatmiserFieldSingleReadOnly('tempformat', 5, [0, 1], MAX_AGE_LONG),  # 00 C,  01 F
            HeatmiserFieldSingleReadOnly('switchdiff', 6, [1, 3], MAX_AGE_LONG),
            HeatmiserFieldSingleReadOnly('frostprotdisable', 7, [0, 1], MAX_AGE_LONG, VALUES_OFF_ON),  #0=enable frost prot when display off,  (opposite in protocol manual,  but tested and user guide is correct)  (default should be enabled)
            HeatmiserFieldDoubleReadOnly('caloffset', 8, [], MAX_AGE_LONG),
            HeatmiserFieldSingleReadOnly('outputdelay', 10, [0, 15], MAX_AGE_LONG),  # minutes (to prevent rapid switching)
            HeatmiserFieldSingleReadOnly('updwnkeylimit', 12, [0, 10], MAX_AGE_LONG),   #limits use of up and down keys
            HeatmiserFieldSingleReadOnly('sensorsavaliable', 13, [0, 4], MAX_AGE_LONG, {'INT_ONLY': 0, 'EXT_ONLY': 1, 'FLOOR_ONLY': 2, 'INT_FLOOR': 3, 'EXT_FLOOR': 4}),  #00 built in only,  01 remote air only,  02 floor only,  03 built in + floor,  04 remote + floor
            HeatmiserFieldSingleReadOnly('optimstart', 14, [0, 3], MAX_AGE_LONG),  # 0 to 3 hours,  default 0
            HeatmiserFieldSingleReadOnly('rateofchange', 15, [], MAX_AGE_LONG),  #number of minutes per degree to raise the temperature,  default 20. Applies to the Wake and Return comfort levels (1st and 3rd)
            HeatmiserFieldSingleReadOnly('programmode', 16, [0, 1], MAX_AGE_LONG, {'day':1, 'week':0}),  #0=5/2,  1= 7day
            HeatmiserFieldSingle('frosttemp', 17, [7, 17], MAX_AGE_LONG),  #default is 12,  frost protection temperature
            HeatmiserFieldSingle('setroomtemp', 18, [5, 35], MAX_AGE_USHORT),
            HeatmiserFieldSingle('floormaxlimit', 19, [20, 45], MAX_AGE_LONG),
            HeatmiserFieldSingleReadOnly('floormaxlimitenable', 20, [0, 1], MAX_AGE_LONG),  #1 is enable, 0 is disable
            HeatmiserFieldSingle('onoff', 21, [0, 1], MAX_AGE_SHORT, VALUES_ON_OFF),  #1 is on, 0 is off
            HeatmiserFieldSingle('keylock', 22, [0, 1], MAX_AGE_SHORT, VALUES_ON_OFF),  #1 is on, 0 is off
            HeatmiserFieldSingle('runmode', 23, [0, 1], MAX_AGE_SHORT, {'HEAT': 0, 'FROST': 1}),   #0 = heating mode,  1 = frost protection mode
            HeatmiserFieldDouble('holidayhours', 24, [0, 720], MAX_AGE_SHORT, VALUES_OFF),  #range guessed and tested,  setting to 0 cancels hold and puts back to program
            #HeatmiserFieldUnknown('unknown', 26, 1, [], MAX_AGE_LONG, 6),  # gap from 26 to 31
            HeatmiserFieldDouble('tempholdmins', 32, [0, 5760], MAX_AGE_SHORT, VALUES_OFF),  #range guessed and tested,  setting to 0 cancels hold and puts setroomtemp back to program
            HeatmiserFieldDoubleReadOnlyTenths('remoteairtemp', 34, [], MAX_AGE_USHORT),  #ffff if no sensor
            HeatmiserFieldDoubleReadOnlyTenths('floortemp', 36, [], MAX_AGE_USHORT),  #ffff if no sensor
            HeatmiserFieldDoubleReadOnlyTenths('airtemp', 38, [], MAX_AGE_USHORT),  #ffff if no sensor
            HeatmiserFieldSingleReadOnly('errorcode', 40, [0, 224, 225, 226], MAX_AGE_SHORT),  # 0 is no error # errors,  0 built in,  1,  floor,  2 remote
            HeatmiserFieldSingleReadOnly('heatingdemand', 41, [0, 1], MAX_AGE_USHORT),  #0 none,  1 heating currently
            HeatmiserFieldTime('currenttime', 43, MAX_AGE_LONG),  #day (Mon - Sun),  hour,  min,  sec. # local estimate should be good, so update once a day
            #5/2 progamming #if hour = 24 entry not used
            HeatmiserFieldHeat('wday_heat', 47, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM),  #hour,  min,  temp  (should minutes be only 0 and 30?)
            HeatmiserFieldHeat('wend_heat', 59, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM)
            ])

        self.heat_schedule = SchedulerWeekHeat()
        self.thermostat = Thermostat('Heating', self)

    def _connect_observers(self):
        """connect obersers to fields"""
        super(ThermoStatWeek, self)._connect_observers()
        self.wday_heat.add_notifable_changed(self.heat_schedule.set_raw_field)
        self.wend_heat.add_notifable_changed(self.heat_schedule.set_raw_field)
        
        #on and off
        self.frostprotdisable.add_notifable_is(self.frostprotdisable.readvalues['ON'], self.thermostat.switch_off)
        self.frostprotdisable.add_notifable_is(self.frostprotdisable.readvalues['OFF'], self.thermostat.switch_off)
        self.onoff.add_notifable_is(self.onoff.readvalues['OFF'], self.thermostat.switch_off)
        self.onoff.add_notifable_is(self.onoff.readvalues['ON'], self.thermostat.switch_swap)
        #change within on
        self.setroomtemp.add_notifable_changed(self.thermostat.switch_swap)
        ###don't need the following if not modelling override holds or program events internally
        ###program change event
        self.tempholdmins.add_notifable_is(self.tempholdmins.readvalues['OFF'], self.thermostat.switch_swap) #check triggered by value force change and data change
        self.tempholdmins.add_notifable_is_not(self.thermostat.switch_swap)
        #between frost and setpoint
        self.runmode.add_notifable_is(self.runmode.readvalues['HEAT'], self.thermostat.switch_swap)
        self.runmode.add_notifable_is(self.runmode.readvalues['FROST'], self.thermostat.switch_swap)
        self.holidayhours.add_notifable_is(self.holidayhours.readvalues['OFF'], self.thermostat.switch_swap)
        self.holidayhours.add_notifable_is_not(self.thermostat.switch_swap)

    def _set_expected_field_values(self):
        """set the expected values for fields that should be fixed"""
        super(ThermoStatWeek, self)._set_expected_field_values()
        self.programmode.expectedvalue = self.programmode.readvalues[self.set_expected_prog_mode]

    def _procfield(self, data, fieldinfo):
        """Process data for a single field storing in relevant."""
        super(ThermoStatWeek, self)._procfield(data, fieldinfo)

        if fieldinfo.name == 'currenttime':
            self._checkcontrollertime()

    def _checkcontrollertime(self):
        """run check of device time against local read time, and try to fix if _autocorrectime"""
        try:
            self.currenttime.comparecontrollertime()
        except HeatmiserControllerTimeError as errstr:
            if self.set_autocorrectime is True:
                logging.warn("C%i %s"%(self.set_address, errstr))
                self.set_time()
            else:
                raise

    def get_variables(self):
        """Gets setroomtemp to hotwaterdemand fields from device"""
        self.get_field_range('setroomtemp', 'hotwaterdemand')

    def get_temps_and_demand(self):
        """Gets remoteairtemp to hotwaterdemand fields from device"""
        self.get_field_range('remoteairtemp', 'hotwaterdemand')

    ## External functions for printing data
    def display_heating_schedule(self):
        """Prints heating schedule to stdout"""
        self.heat_schedule.display()

    def nexttarget(self):
        """get next heat target"""
        return self.heat_schedule.get_next_schedule_item(self.currenttime.localtimearray())

    def print_target(self):
        """Returns text describing current heating state"""
        self.read_temp_state()
        return self.thermostat.get_state_text()
            
    ## External functions for reading data

    def read_temp_state(self):
        """Returns the current temperature control state from off to following program"""
        self.read_fields(['mon_heat', 'tues_heat', 'wed_heat', 'thurs_heat', 'fri_heat', 'wday_heat', 'wend_heat'], -1)
        self.read_fields(['onoff', 'frostprotdisable', 'holidayhours', 'runmode', 'tempholdmins', 'setroomtemp'])

        return self.thermostat.state

    def read_air_sensor_type(self):
        """Reports airsensor type"""
        #1 local, 2 remote
        self.read_field('sensorsavaliable')

        if self.sensorsavaliable.is_value('INT_ONLY') or self.sensorsavaliable.is_value('INT_FLOOR'):
            return 1
        elif self.sensorsavaliable.is_value('EXT_ONLY') or self.sensorsavaliable.is_value('EXT_FLOOR'):
            return 2
        raise ValueError("sensorsavaliable field invalid")

    def read_air_temp(self):
        """Read the air temperature getting data from device if too old"""
        if self.read_air_sensor_type() == 1:
            self.read_fields(['airtemp', 'errorcode'], self.set_max_age_temp)
            if self.errorcode == 224:
                raise HeatmiserControllerSensorError("airtemp sensor error")
            return self.airtemp.value
        else:
            self.read_fields(['remoteairtemp', 'errorcode'], self.set_max_age_temp)
            if self.errorcode == 226:
                raise HeatmiserControllerSensorError("remote airtemp sensor error")
            return self.remoteairtemp.value

    def read_time(self, maxage=0):
        """Readtime, getting from device if required"""
        return self.read_field('currenttime', maxage)

    ## External functions for setting data

    def set_heating_schedule(self, day, schedule):
        """Set heating schedule for a single day"""
        padschedule = self.heat_schedule.pad_schedule(schedule)
        for fieldname in self.heat_schedule.get_entry_names(day):
            self.set_field(fieldname, padschedule)

    def set_time(self):
        """set time on device to match current localtime on server"""
        timenow = time.time() + 0.5 #allow a little time for any delay in setting
        return self.set_field('currenttime', self.currenttime.localtimearray(timenow))

    #overriding

    def set_temp(self, temp):
        """sets the temperature demand overriding the program."""
        #Believe it returns at next prog change.
        if self.read_field('tempholdmins') == 0: #check hold temp not applied
            return self.set_field('setroomtemp', temp)
        else:
            logging.warn("%i address, temp hold applied so won't set temp"%(self.set_address))

    def release_temp(self):
        """release setTemp back to the program, but only if temp isn't held for a time (holdTemp)."""
        if self.read_field('tempholdmins') == 0: #check hold temp not applied
            return self.set_field('tempholdmins', 0)
        else:
            logging.warn("%i address, temp hold applied so won't remove set temp"%(self.set_address))

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

class ThermoStatDay(ThermoStatWeek):
    """Device class for thermostats operating daily programmode
    Heatmiser prt_e_model."""

    def _buildfields(self):
        """add to list of fields"""
        super(ThermoStatDay, self)._buildfields()
        self.fields.extend([
            HeatmiserFieldHeat('mon_heat', 103, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM),
            HeatmiserFieldHeat('tues_heat', 115, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM),
            HeatmiserFieldHeat('wed_heat', 127, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM),
            HeatmiserFieldHeat('thurs_heat', 139, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM),
            HeatmiserFieldHeat('fri_heat', 151, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM),
            HeatmiserFieldHeat('sat_heat', 163, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM),
            HeatmiserFieldHeat('sun_heat', 175, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM)
        ])

        self.heat_schedule = SchedulerDayHeat()

    def _connect_observers(self):
        """connect obersers to fields"""
        super(ThermoStatDay, self)._connect_observers()
        fieldnames = ['mon_heat', 'tues_heat', 'wed_heat', 'thurs_heat', 'fri_heat', 'sat_heat', 'sun_heat']
        for fieldname in fieldnames:
            getattr(self, fieldname).add_notifable_changed(self.heat_schedule.set_raw_field)

DEVICETYPES.setdefault('prt_e_model', {'week': ThermoStatWeek, 'day': ThermoStatDay})
