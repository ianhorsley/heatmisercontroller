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

# Import our own stuff
from devices import *
from stats_defn import *
from adaptor import *
import setup as hms

class HeatmiserNetwork:
### stat list setup

  def __init__(self, configfile = None):
    
    # Initialize controller setup
    if configfile is None:
      self._module_path = os.path.abspath(os.path.dirname(__file__))
      configfile = os.path.join(self._module_path, "hmcontroller.conf")
    try:
        self._setup = hms.HeatmiserControllerFileSetup(configfile)
        settings = self._setup.settings
    except hms.HeatmiserControllerSetupInitError as e:
        logger.critical(e)
        sys.exit("Unable to load configuration file: " + configfile)
    
    # Initialize and connect to heatmiser network, probably through serial port
    self.adaptor = Heatmiser_Adaptor(self._setup)
    self.adaptor.connect()
    
    #create a broadcast device
    setattr(self,"All",hmBroadcastController(self.adaptor,"All","Broadcast to All"))
    self.current = self.All
    
    self.setStatList(settings['devices'])
      
  def setStatList(self, list):
    self._statlist = list
    self._statnum = len(self._statlist)

    self._controllers = range(self._statnum)
    for name, controllersettings in list.iteritems():
      if hasattr(self,name):
        print "error duplicate stat name"
      else:
        setattr(self,name,hmController(self.adaptor,controllersettings))
        self._controllers[controllersettings['displayorder']] = getattr(self,name)

    self.current = self.controllers[0]
  
  def getStatAddress(self,shortname):
    if isinstance(shortname,basestring):
      #matches = [x for x in self.statlist if x[SL_SHORT_NAME] == shortname]
      shorts = [row[SL_SHORT_NAME] for row in self.statlist]
      
      return self.statlist[shorts.index(shortname)][SL_ADDR]
    else:
      return shortname

  def setCurrentControllerByName(self,name):
    self.current = getattr(self,name)
    
  def setCurrentControllerByIndex(self,index):
    self.current = self.controllers[index]
    
  def controllerByName(self,name):
    return getattr(self,name)
