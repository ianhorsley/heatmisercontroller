"""Handles Heatmiser network of devices and adaptor

also loads adaptor and keeps track of Heatmiser devices

Ian Horsley 2018
"""

import os
import logging

# Import our own stuff
from .genericdevice import DEVICETYPES
from .generaldevices import HeatmiserBroadcastDevice, ThermoStatUnknown
from .adaptor import HeatmiserAdaptor
from .hm_constants import SLAVE_ADDR_MIN, SLAVE_ADDR_MAX
from .exceptions import HeatmiserResponseError
from . import setup as hms

class HeatmiserNetwork(object):
    """Class that connects a set of devices (from configuration) and an adpator."""
    ### stat list setup

    def __init__(self, configfile=None):
        
        # Select default configuration file if none provided
        if configfile is None:
            self._module_path = os.path.abspath(os.path.dirname(__file__))
            configfile = os.path.join(self._module_path, "hmcontroller.conf")
          
        # Initialize controller setup
        try:
            self._setup = hms.HeatmiserControllerFileSetup(configfile)
            settings = self._setup.settings
        except hms.HeatmiserControllerSetupInitError as err:
            logging.error(err)
            raise
        
        # Initialize and connect to heatmiser network, probably through serial port
        self.adaptor = HeatmiserAdaptor(self._setup)
        
        # Load device list from settings or find devices if none listed
        self.controllers = []
        self._addresses_in_use = []
        if 'devices' in settings:
            if len(settings['devices']):
                self._set_stat_list(settings['devices'], settings['devicesgeneral'])
        else: #if devices not defined then auto run find devices.
            self.find_devices()
        
        # Create a broadcast device
        setattr(self, "All", HeatmiserBroadcastDevice(self.adaptor, "Broadcast to All", self.controllers))
        self._current = self.All
      
    def _set_stat_list(self, statlist, generalsettings):
        """Store list of devives and create objects for each"""
        self._statlist = statlist
        self._statnum = len(self._statlist)

        self.controllers = list(range(self._statnum))
        for name, controllersettings in statlist.iteritems():
            if hasattr(self, name):
                logging.warn("error duplicate stat name")
            else:
                new_device = self.add_device(name, controllersettings, generalsettings)
                self.controllers[controllersettings['display_order'] - 1] = new_device
        self._current = self.controllers[0]
    
    def add_device(self, name, controllersettings, generalsettings=None):
        """Add device to network"""
        expected_model = controllersettings['expected_model']
        expected_prog_mode = controllersettings['expected_prog_mode']
        new_device = DEVICETYPES[expected_model][expected_prog_mode](self.adaptor, controllersettings, generalsettings)
        setattr(self, name, new_device)
        setattr(new_device, 'name', name) #make name avaliable when accessing by id
        self._addresses_in_use.append(controllersettings['address'])
        return new_device
    
    def find_devices(self, max_address=SLAVE_ADDR_MAX):
        """Find devices on the network not in the configuration file"""
        unused_addresses = [address for address in range(SLAVE_ADDR_MIN, max_address + 1) if address not in self._addresses_in_use]
        for address in unused_addresses:
            try:
                controllersettings = {'address': address}
                test_device = ThermoStatUnknown(self.adaptor, controllersettings, self._setup.settings['devicesgeneral'])
                # use fields from device rather to set the expected mode and type
                test_device.read_fields(['model', 'programmode'], 0)
            except HeatmiserResponseError as err:
                logging.info("C%i device not found, library error %s"%(address, err))
            else:
                model = test_device.model.read_value_text()
                prog_mode = test_device.programmode.read_value_text()
                logging.info("C%i device %s found, with program %s"%(address, model, prog_mode))
                controllersettings = {
                    'address': address,
                    'expected_model': model,
                    'expected_prog_mode': prog_mode
                }
                new_device = self.add_device("C%i"%address, controllersettings, self._setup.settings['devicesgeneral'])
                self.controllers.append(new_device)
                self._addresses_in_use.append(address)
    
    def get_stat_address(self, shortname):
        """Get network address from device name."""
        if isinstance(shortname, str):
            return self._statlist[shortname]['address']
        else:
            return shortname

    def set_current_controller_by_name(self, name):
        """Set the current device by name"""
        self._current = getattr(self, name)
        
    def set_current_controller_by_index(self, index):
        """Set the current device by id"""
        self._current = self.controllers[index]
        
    def get_controller_by_name(self, name):
        """Get device if from name"""
        return getattr(self, name)

    def run_method_on_all(self, method, *args, **kwargs):
        """Run a method on all devices"""
        results = []
        for obj in self.controllers:
            results.append(getattr(obj, method)(*args, **kwargs))
        return results
