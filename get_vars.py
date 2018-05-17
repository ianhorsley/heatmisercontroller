#!/usr/bin/python
#
# Ian Horsley 2018

#
# Sets all controllers to on
#
import serial
from struct import pack
import time
import sys
import os
import logging

from stats_defn import *
from hm_constants import *
from hm_utils import *

# CODE STARTS HERE

# Generate a RFC2822 format date
# This works with both Excel and Timeline
localtime = time.asctime( time.localtime(time.time()))
polltime = time.time()
polltimet = time.localtime(polltime)

#### Add logging
#logging.basicConfig(filename='example.log',level=logging.DEBUG)
#FORMAT = '%(asctime)-15s %(message)s'
#logging.basicConfig(level=logging.INFO, format=FORMAT)
initialize_logger('logs', logging.INFO)

hmn1 = hmNetwork()
hmn1.connect()
hmn1.setStatList(StatList)
hmn1.printdiagnostic = False

# CYCLE THROUGH ALL CONTROLLERS
for current_controller in hmn1.controllers:
  print
  print "Getting all data control %2d in %s *****************************" % (current_controller.address, current_controller.long_name)

  try:
    current_controller.hmReadAll()
  except:
    print "C%d in %s Failed to Read" % (current_controller.address,  current_controller.name.ljust(4))
  else:
    disptext = "C%d Air Temp is %.1f from type %.f and Target set to %d  Boiler Demand %d" % (current_controller.address, current_controller.getAirTemp(), current_controller.getAirSensorType(), current_controller.setroomtemp, current_controller.heatingstate)
    if current_controller.model == PRT_HW_MODEL:
      print "%s Hot Water Demand %d" % (disptext, current_controller.hotwaterstate)
    else:
      print disptext
    current_controller.display_heating_schedule()
    current_controller.display_water_schedule()

time.sleep(5) # sleep before next cycle
#END OF CYCLE THROUGH CONTROLLERS

while True:
  print
  # CYCLE THROUGH ALL CONTROLLERS
  for current_controller in hmn1.controllers:
    
    try:
      current_controller.hmReadTempsandDemand()
    except request_exceptions as e:
      print "C%d in %s Failed to Read due to %s" % (current_controller.address,  current_controller.name.ljust(4),str(e))
    else: 
      targettext = current_controller.printTarget()
      disptext = "C%d in %s Air Temp is %.1f from type %.f, %s, Heat %d" % (current_controller.address,  current_controller.name.ljust(4), current_controller.getAirTemp(), current_controller.getAirSensorType(), targettext, current_controller.heatingstate)
      
      if current_controller.model == PRT_HW_MODEL:
        print "%s Water %d" % (disptext, current_controller.hotwaterstate)
      else:
        print disptext
  
  #END OF CYCLE THROUGH CONTROLLERS  

  time.sleep(5) # sleep before next cycle


hmn1.disconnect()

#if (problem > 0):
	#mail(you, "Heatmiser TimeSet Error ", "A Problem has occurred", "errorlog.txt")
