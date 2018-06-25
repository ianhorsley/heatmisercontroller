"""Handles Heatmiser network of devices and adaptor

also loads adaptor and keeps track of Heatmiser devices

Ian Horsley 2018
"""

import os
import logging
import sys

# Import our own stuff
from devices import HeatmiserDevice, HeatmiserBroadcastDevice
from adaptor import HeatmiserAdaptor
import setup as hms

class HeatmiserNetwork(object):
    """Class that connects a set of devices (from configuration) and an adpator."""
    ### stat list setup

    def __init__(self, configfile = None):
        
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
            sys.exit("Unable to load configuration file: " + configfile)
        
        # Initialize and connect to heatmiser network, probably through serial port
        self.adaptor = HeatmiserAdaptor(self._setup)
        self.adaptor.connect()
        
        self._set_stat_list(settings['devices'], settings['devicesgeneral'])
        
        # Create a broadcast device
        setattr(self,"All",HeatmiserBroadcastDevice(self.adaptor,"Broadcast to All", self.controllers))
        self._current = self.All
      
    def _set_stat_list(self, statlist, generalsettings):
        """Store list of devives and create objects for each"""
        self._statlist = statlist
        self._statnum = len(self._statlist)

        self.controllers = range(self._statnum)
        for name, controllersettings in statlist.iteritems():
            if hasattr(self, name):
                print "error duplicate stat name"
            else:
                setattr(self, name, HeatmiserDevice(self.adaptor, controllersettings, generalsettings))
                setattr(getattr(self, name), 'name', name) #make name avaliable when accessing by id
                self.controllers[controllersettings['display_order']-1] = getattr(self, name)

        self._current = self.controllers[0]
      
    def get_stat_address(self, shortname):
        """Get network address from device name."""
        if isinstance(shortname, basestring):
            shorts = [row[SL_SHORT_NAME] for row in self._statlist]
            return self.statlist[shorts.index(shortname)]['address']
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
