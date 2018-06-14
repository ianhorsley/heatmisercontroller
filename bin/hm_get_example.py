#!/usr/bin/env python
#
# Ian Horsley 2018

#
# Gets data for all stats repeatedly and displays
#
import time
import logging

from heatmisercontroller.logging_setup import initialize_logger
from heatmisercontroller.hm_constants import *
from heatmisercontroller.network import *
from heatmisercontroller.exceptions import hmResponseError

#start logging
initialize_logger('logs', logging.WARN, True)

hmn1 = HeatmiserNetwork()

# CYCLE THROUGH ALL CONTROLLERS
for current_controller in hmn1.controllers:
  print "\r\nGetting all data control %2d in %s *****************************" % (current_controller._address, current_controller._long_name)
  
  try:
    current_controller.hmReadAll()
  except hmResponseError as e:
    print "C%d in %s Failed to Read due to %s" % (current_controller._address,  current_controller._name.ljust(4), str(e))
  else:
    disptext = "C%d Air Temp is %.1f from type %.f and Target set to %d  Boiler Demand %d" % (current_controller._address, current_controller.getAirTemp(), current_controller.getAirSensorType(), current_controller.setroomtemp, current_controller.heatingdemand)
    if current_controller.isHotWater():
      print "%s Hot Water Demand %d" % (disptext, current_controller.hotwaterdemand)
    else:
      print disptext
    current_controller.display_heating_schedule()
    current_controller.display_water_schedule()

time.sleep(5) # sleep before next cycle

while True:
  print
  # CYCLE THROUGH ALL CONTROLLERS repeatedly
  for current_controller in hmn1.controllers:
    
    try:
      current_controller.hmReadTempsandDemand()
    except hmResponseError as e:
      print "C%d in %s Failed to Read due to %s" % (current_controller._address,  current_controller._name.ljust(4),str(e))
    else: 
      targettext = current_controller.printTarget()
      disptext = "C%d in %s Air Temp is %.1f from type %.f, %s, Heat %d" % (current_controller._address,  current_controller._name.ljust(4), current_controller.getAirTemp(), current_controller.getAirSensorType(), targettext, current_controller.heatingdemand)
      
      if current_controller.isHotWater():
        print "%s Water %d" % (disptext, current_controller.hotwaterdemand)
      else:
        print disptext

  time.sleep(5) # sleep before next cycle
