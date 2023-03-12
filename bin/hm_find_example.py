#!/usr/bin/env python
"""Gets data from Heatmiser stats repeatedly and displays
Ian Horsley 2018
"""
from __future__ import absolute_import
import os
import logging

from heatmisercontroller.network import HeatmiserNetwork
from heatmisercontroller.exceptions import HeatmiserResponseError

#start logging
logging.basicConfig(level=logging.INFO)

MODULE_PATH = os.path.abspath(os.path.dirname(__file__))
CONFIGFILE = os.path.join(MODULE_PATH, "nocontrollers.conf")

HMN = HeatmiserNetwork(CONFIGFILE)
HMN.find_devices(10)

# CYCLE THROUGH ALL CONTROLLERS
for current_controller in HMN.controllers:
    print("\r\nGetting all data control %2d in %s *****************************" %(
                current_controller.set_address, current_controller.set_long_name))

    try:
        current_controller.read_all()
        disptext = "C%d Air Temp is %.1f from type %.f and Target set to %d   Boiler Demand %d" % (
                        current_controller.address, current_controller.read_air_temp(),
                        current_controller.read_air_sensor_type(), current_controller.setroomtemp,
                        current_controller.heatingdemand)
    except HeatmiserResponseError as err:
        print("C%d in %s Failed to Read due to %s" %(current_controller.set_address,
                    current_controller.name.ljust(4), str(err)))
    else:
        if current_controller.is_hot_water:
            print("%s Hot Water Demand %d" %(disptext, current_controller.hotwaterdemand))
            current_controller.display_water_schedule()
        else:
            print(disptext)
        current_controller.display_heating_schedule()
