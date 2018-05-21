#
# Ian Horsley 2018

#
# hmNetwork Class and helper functions
# also loads adaptor and keeps track of heatmiser devices

# Assume Python 2.7.x
#
import serial
import time
from datetime import datetime
import logging

# Import our own stuff
from devices import *
from stats_defn import *
from adaptor import *

class HeatmiserNetwork:
### stat list setup

  def __init__(self):
    self.adaptor = Heatmiser_Adaptor()
    self.adaptor.connect()
    
    #create a broadcast device
    setattr(self,"All",hmBroadcastController(self.adaptor,"All","Broadcast to All"))
    self.current = self.All
    
      
  def setStatList(self, list):
    self.statlist = list
    self.statnum = len(self.statlist)

    self.controllers = []
    for stat in list:
      if hasattr(self,stat[SL_SHORT_NAME]):
        print "error duplicate stat short name"
      else:
        setattr(self,stat[SL_SHORT_NAME],hmController(self.adaptor,stat[SL_ADDR],stat[SL_PROTOCOL],stat[SL_SHORT_NAME],stat[SL_LONG_NAME],stat[SL_EXPECTED_TYPE],stat[SL_MODE]))
        self.controllers.append(getattr(self,stat[SL_SHORT_NAME]))

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
