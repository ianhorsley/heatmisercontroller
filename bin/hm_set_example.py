#!/usr/bin/env python
"""Example of setting configurations on Heatmiser stats
Ian Horsley 2018
"""

import logging

from heatmisercontroller.logging_setup import initialize_logger
from heatmisercontroller.hm_constants import *
from heatmisercontroller.network import HeatmiserNetwork

initialize_logger('logs', logging.INFO, True)

HMN = HeatmiserNetwork()

#HMN.Kit.holdTemp(30,21) #mins, temp
#HMN.Kit.releaseHoldTemp()

#HMN.release_temp("Cons")
#HMN.All.set_field('holidayhours', 96)
HMN.All.release_holiday()

HMN.Kit.set_field('hotwaterdemand', WRITE_HOTWATERDEMAND_PROG)

HMN.All.set_on()
HMN.All.set_frost()
#HMN.hmUpdateTime(2)

HMN.All.set_field('runmode', WRITE_RUNMODE_HEATING)
HMN.Cons.set_field('runmode', WRITE_RUNMODE_FROST)

#HMN.B2.set_temp(24)
#HMN.Kit.set_temp(24)
#HMN.B1.set_temp(24)
#HMN.Cons.set_temp(24)
#HMN.All.set_temp(24)

#HMN.Kit.release_temp()
#HMN.B1.release_temp()
#HMN.B2.release_temp()
#HMN.Cons.release_temp()

DOWNINACTIVE = 20
DOWNACTIVE = 19
FROST = 12
SLEEP = 16
DAYFROST = [7, 0, FROST]

WKDAY_ZEARLY = [5, 00, DOWNACTIVE, 8, 30, FROST, 15, 00, DOWNINACTIVE, 21, 00, SLEEP]
WKDAY_ZLATE = [6, 30, DOWNINACTIVE, 12, 00, FROST, 17, 00, DOWNINACTIVE, 21, 30, SLEEP]
WKDAY_ZTRAINING = [6, 30, DOWNACTIVE, 8, 30, FROST, 16, 30, DOWNINACTIVE, 21, 00, SLEEP]
WKEND_ZEARLY = [5, 00, DOWNINACTIVE, 21, 30, SLEEP]
WKEND_ZLATE = [6, 30, DOWNINACTIVE, 21, 30, SLEEP]
WKEND_ZOFF = [6, 30, DOWNINACTIVE, 21, 30, SLEEP]
WKDAY_ZSTARTNIGHT = WKEND_ZOFF

HMN.Kit.set_heating_schedule('mon_heat', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('tues_heat', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('wed_heat', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('thurs_heat', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('fri_heat', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('sat_heat', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('sun_heat', WKEND_ZOFF)

EVENINGWATER = [17, 30, 18, 30]
NOWATER = []
HMN.Kit.set_water_schedule('all', NOWATER)

UPSLEEP = 16
UPAWAKE = 18
UPWKDAY_ZEARLY = [5, 0, UPAWAKE, 7, 00, FROST, 20, 30, UPAWAKE, 21, 30, UPSLEEP]
UPWKDAY_ZLATE = [7, 0, UPAWAKE, 8, 00, FROST, 21, 30, UPAWAKE, 22, 30, UPSLEEP]
UPWKDAY = [7, 0, UPAWAKE, 8, 30, FROST, 21, 00, UPAWAKE, 21, 30, UPSLEEP]
UPWKEND_ZEARLY = [5, 0, UPAWAKE, 8, 00, FROST, 20, 30, UPAWAKE, 21, 30, UPSLEEP]
UPWKEND_ZLATE = [7, 0, UPAWAKE, 9, 30, FROST, 21, 30, UPAWAKE, 22, 30, UPSLEEP]
UPWKEND = [7, 0, UPAWAKE, 9, 30, FROST, 21, 00, UPAWAKE, 22, 00, UPSLEEP]
DAYFROST = [7, 0, FROST]

HMN.B1.set_heating_schedule('mon_heat', DAYFROST)
HMN.B1.set_heating_schedule('tues_heat', DAYFROST)
HMN.B1.set_heating_schedule('wed_heat', DAYFROST)
HMN.B1.set_heating_schedule('thurs_heat', DAYFROST)
HMN.B1.set_heating_schedule('fri_heat', DAYFROST)
HMN.B1.set_heating_schedule('sat_heat', DAYFROST)
HMN.B1.set_heating_schedule('sun_heat', DAYFROST)

HMN.B2.set_heating_schedule('mon_heat', DAYFROST)
HMN.B2.set_heating_schedule('tues_heat', DAYFROST)
HMN.B2.set_heating_schedule('wed_heat', DAYFROST)
HMN.B2.set_heating_schedule('thurs_heat', DAYFROST)
HMN.B2.set_heating_schedule('fri_heat', DAYFROST)
HMN.B2.set_heating_schedule('sat_heat', DAYFROST)
HMN.B2.set_heating_schedule('sun_heat', DAYFROST)

HMN.get_controller_by_name('Cons').set_field('wday_heat', [9, 0, 12, 21, 30, 10, 24, 0, 5, 24, 0, 5])
HMN.get_controller_by_name('Cons').set_field('wend_heat', [9, 0, 12, 21, 30, 10, 24, 0, 5, 24, 0, 5])

HMN.Sit.set_heating_schedule('wday_heat', DAYFROST)
HMN.Sit.set_heating_schedule('wend_heat', DAYFROST)

#HMN.hmSetFields("Kit", 'wday_water', [7, 0, 8, 0, 16, 0, 17, 0, 24, 0, 24, 0, 24, 0, 24, 0])
#HMN.hmSetFields("Kit", 'wday_water', [24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0])
#HMN.hmSetFields("Kit", 'wend_water', [8, 0, 9, 0, 18, 0, 19, 0, 24, 0, 24, 0, 24, 0, 24, 0])

#HMN.hmSetField("Kit", 'frosttemp', 9)
#HMN.hmSetField("B1", 'frosttemp', 9)
#HMN.hmSetField("B2", 'frosttemp', 9)
#HMN.hmSetField("Cons", 'frosttemp', 9)


