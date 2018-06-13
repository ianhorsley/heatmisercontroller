#
# Ian Horsley 2018

#
# hmNetwork Class and helper functions
# also loads adaptor and keeps track of heatmiser devices

# Assume Python 2.7.x
#
import os
import serial
import time
import logging
import sys

# Import our own stuff
from devices import *
from adaptor import *
import setup as hms

class HeatmiserNetwork:
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
    except hms.HeatmiserControllerSetupInitError as e:
        logging.error(e)
        sys.exit("Unable to load configuration file: " + configfile)
    
    # Initialize and connect to heatmiser network, probably through serial port
    self.adaptor = Heatmiser_Adaptor(self._setup)
    self.adaptor.connect()
    
    # Create a broadcast device
    setattr(self,"All",hmBroadcastController(self.adaptor,"Broadcast to All"))
    self._current = self.All
    
    self.setStatList(settings['devices'])
      
  def setStatList(self, list):
    # Store list of stats
    self._statlist = list
    self._statnum = len(self._statlist)

    self.controllers = range(self._statnum)
    for name, controllersettings in list.iteritems():
      controllersettings['name'] = name
      if hasattr(self,name):
        print "error duplicate stat name"
      else:
        setattr(self,name,hmController(self.adaptor,controllersettings))
        self.controllers[controllersettings['display_order']-1] = getattr(self,name)

    self._current = self.controllers[0]
  
  def getStatAddress(self,shortname):
    if isinstance(shortname,basestring):
      #matches = [x for x in self.statlist if x[SL_SHORT_NAME] == shortname]
      shorts = [row[SL_SHORT_NAME] for row in self._statlist]
      
      return self.statlist[shorts.index(shortname)]['address']
    else:
      return shortname

  def setCurrentControllerByName(self,name):
    self._current = getattr(self,name)
    
  def setCurrentControllerByIndex(self,index):
    self._current = self.controllers[index]
    
  def controllerByName(self,name):
    return getattr(self,name)
