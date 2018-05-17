#!/usr/bin/python
#
# Ian Horsley 2018

#
# Gets data for all stats repeatedly and displays
#
import time
import logging

from stats_defn import *
from hm_constants import *
from hm_utils import *

#start logging
initialize_logger('logs', logging.WARN)

hmn1 = hmNetwork()
hmn1.connect()
hmn1.setStatList(StatList)

# CYCLE THROUGH ALL CONTROLLERS
for current_controller in hmn1.controllers:
  print "\r\nGetting all data control %2d in %s *****************************" % (current_controller.address, current_controller.long_name)

  try:
    current_controller.hmReadAll()
  except Exception as e:
    print "C%d in %s Failed to Read due to %e" % (current_controller.address,  current_controller.name.ljust(4), str(e))
  else:
    disptext = "C%d Air Temp is %.1f from type %.f and Target set to %d  Boiler Demand %d" % (current_controller.address, current_controller.getAirTemp(), current_controller.getAirSensorType(), current_controller.setroomtemp, current_controller.heatingstate)
    if current_controller.model == PRT_HW_MODEL:
      print "%s Hot Water Demand %d" % (disptext, current_controller.hotwaterstate)
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
    except (request_exceptions, hmProtocolError) as e:
      print "C%d in %s Failed to Read due to %s" % (current_controller.address,  current_controller.name.ljust(4),str(e))
    else: 
      targettext = current_controller.printTarget()
      disptext = "C%d in %s Air Temp is %.1f from type %.f, %s, Heat %d" % (current_controller.address,  current_controller.name.ljust(4), current_controller.getAirTemp(), current_controller.getAirSensorType(), targettext, current_controller.heatingstate)
      
      if current_controller.model == PRT_HW_MODEL:
        print "%s Water %d" % (disptext, current_controller.hotwaterstate)
      else:
        print disptext

  time.sleep(5) # sleep before next cycle

hmn1.disconnect()