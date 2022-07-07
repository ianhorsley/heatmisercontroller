#!/usr/bin/env python
"""Gets data from Heatmiser stats repeatedly and displays
Ian Horsley 2018
"""
from __future__ import absolute_import
import time
import logging

from heatmisercontroller.logging_setup import initialize_logger_full
from heatmisercontroller.network import HeatmiserNetwork
from heatmisercontroller.exceptions import HeatmiserError

#start logging
initialize_logger_full('logs', logging.INFO)

HMN = HeatmiserNetwork()

def readanddisplay():
    """Read all data from all controllers and print current time"""
    print("\r\nGetting time for %2d in %s *****************************" %(current_controller.set_address, current_controller.set_long_name))
    try:
        current_time = current_controller.read_time()
    except HeatmiserError as err:
        print("C%d in %s Failed to Read due to %s" %(current_controller.set_address, current_controller.name.ljust(4), str(err)))
    else:
        print("C%d in %s time is %s" %(current_controller.set_address, current_controller.name.ljust(4), str(current_time)))

# read and display, without any corrections
for current_controller in HMN.controllers:
    current_controller.set_autocorrectime = False
    readanddisplay()

print("waiting for 30 seconds before fixing any errors")
time.sleep(30) # sleep before next cycle, which will fix any errors

# read and display, and try to correct if wrong
for current_controller in HMN.controllers:
    current_controller.set_autocorrectime = True
    readanddisplay()
        