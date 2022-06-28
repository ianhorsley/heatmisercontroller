"""Heatmiser Device Classes

Broadcast to all devices on the Heatmiser network
UnknownThermoStat

Ian Horsley 2018
"""
import logging

from .genericdevice import HeatmiserDevice
from .devices_prt_hw import ThermoStatHotWaterDay
from .fields import HeatmiserFieldUnknown, HeatmiserFieldSingleReadOnly
from .decorators import ListWrapperClass, run_function_on_all
from .hm_constants import DEFAULT_PROTOCOL, DEFAULT_PROG_MODE, BROADCAST_ADDR
from .hm_constants import MAX_AGE_LONG
from .logging_setup import csvlist

class ThermoStatUnknown(HeatmiserDevice):
    """Device class for unknown thermostats operating unknown programmode"""

    def _configure_fields(self):
        """build dict to map field name to index, map fields tables to properties and set dcb addresses."""
        super(ThermoStatUnknown, self)._configure_fields()
        self.dcb_length = 65536 #override dcb_length to prevent readall, given unknown full length # initialised in base class.
    
    def _buildfields(self):
        """add to list of fields"""
        super(ThermoStatUnknown, self)._buildfields()
        self.fields.extend([
            HeatmiserFieldUnknown('unknown', 5, MAX_AGE_LONG, 6),  # gap allows single read
            HeatmiserFieldUnknown('unknown', 12, MAX_AGE_LONG, 4),  # gap allows single read
            HeatmiserFieldSingleReadOnly('programmode', 16, [0, 1], MAX_AGE_LONG, {'day':1, 'week':0})  #0=5/2,  1= 7day
        ])
        
    def _set_expected_field_values(self):
        """set the expected values for fields that should be fixed. Overriding prevents expected model being setup."""
        self.address.expectedvalue = self.set_address
        self.DCBlen.expectedvalue = self.dcb_length

class HeatmiserBroadcastDevice(ThermoStatHotWaterDay):
    """Broadcast device class for broadcast set functions and managing reading on all devices
    Based class with most complete field list"""
    
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
        logging.info("All reading %s from %i controllers"%(csvlist(fieldnames), len(self._controllerlist.list)))
        
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
 