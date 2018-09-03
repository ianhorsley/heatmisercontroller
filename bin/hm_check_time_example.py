#!/usr/bin/env python
"""Gets data from Heatmiser stats repeatedly and displays
Ian Horsley 2018
"""

import time
import logging

from heatmisercontroller.logging_setup import initialize_logger
from heatmisercontroller.network import HeatmiserNetwork
from heatmisercontroller.exceptions import HeatmiserError

#start logging
initialize_logger('logs', logging.INFO, True)

HMN = HeatmiserNetwork()

# CYCLE THROUGH ALL CONTROLLERS
for current_controller in HMN.controllers:
    print "\r\nGetting time for %2d in %s *****************************" %(current_controller.address, current_controller.long_name)

    try:
        current_controller.autocorrectime = False
        current_time = current_controller.read_time()
    except HeatmiserError as err:
        print "C%d in %s Failed to Read due to %s" %(current_controller.address, current_controller.name.ljust(4), str(err))
    else:
        print "C%d in %s time is %s" %(current_controller.address, current_controller.name.ljust(4), str(current_time))

print "waiting for 30 seconds before fixing any errors"
time.sleep(30) # sleep before next cycle, which will fix any errors

for current_controller in HMN.controllers:
    print "\r\nGetting time for %2d in %s *****************************" %(current_controller.address, current_controller.long_name)

    try:
        current_controller.autocorrectime = True
        current_time = current_controller.read_time()
    except HeatmiserError as err:
        print "C%d in %s Failed to Read due to %s" %(current_controller.address, current_controller.name.ljust(4), str(err))
    else:
        print "C%d in %s time is %s" %(current_controller.address, current_controller.name.ljust(4), str(current_time))
        