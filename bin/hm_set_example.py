#!/usr/bin/env python
"""Example of setting configurations on Heatmiser stats
Ian Horsley 2018
"""

import logging

from heatmisercontroller.logging_setup import initialize_logger
from heatmisercontroller.hm_constants import *
from heatmisercontroller.network import *

initialize_logger('logs', logging.INFO, True)

HMN = HeatmiserNetwork()

#HMN.hmSetTemp("Kit", 25)
#HMN.Kit.holdTemp(30,21) #mins, temp
#HMN.Kit.releaseHoldTemp()

#HMN.hmSetTemp("Cons", 25)
#HMN.hmReleaseTemp("Cons")
#HMN.All.set_field('holidayhours', 96)
HMN.All.releaseHoliday()

HMN.Kit.set_field('hotwaterdemand', WRITE_HOTWATERDEMAND_PROG)

HMN.All.setOn()
#HMN.hmUpdateTime(2)
#HMN.controllerByName('B1').setOff()

HMN.All.set_field('runmode', WRITE_RUNMODE_HEATING)
HMN.Sit.set_field('runmode', WRITE_RUNMODE_FROST)

#HMN.B2.setTemp(24)
#HMN.Kit.setTemp(24)
#HMN.B1.setTemp(24)
#HMN.Cons.setTemp(24)
#HMN.All.setTemp(24)

HMN.Kit.releaseTemp()
HMN.B1.releaseTemp()
HMN.B2.releaseTemp()
HMN.Cons.releaseTemp()

DOWNINACTIVE = 20
DOWNACTIVE = 19
FROST = 12
DAYFROST = [7, 0, FROST]

WKDAY_ZEARLY = [5, 00, DOWNACTIVE, 8, 30, FROST, 15, 00, DOWNINACTIVE, 21, 00, FROST]
WKDAY_ZLATE = [7, 00, DOWNINACTIVE, 12, 00, FROST, 17, 00, DOWNINACTIVE, 21, 30, FROST]
WKDAY_ZTRAINING = [7, 00, DOWNACTIVE, 8, 30, FROST, 16, 30, DOWNINACTIVE, 21, 00, FROST]
WKEND_ZEARLY = [5, 00, DOWNINACTIVE, 21, 30, FROST]
WKEND_ZLATE = [7, 00, DOWNINACTIVE, 21, 30, FROST]
WKEND_ZOFF = [7, 00, DOWNINACTIVE, 21, 30, FROST]
HMN.Kit.setHeatingSchedule('mon_heat', WKEND_ZEARLY)
HMN.Kit.setHeatingSchedule('tues_heat', WKEND_ZEARLY)
HMN.Kit.setHeatingSchedule('wed_heat', WKDAY_ZTRAINING)
HMN.Kit.setHeatingSchedule('thurs_heat', WKEND_ZEARLY)
HMN.Kit.setHeatingSchedule('fri_heat', WKEND_ZEARLY)
HMN.Kit.setHeatingSchedule('sat_heat', WKEND_ZOFF)
HMN.Kit.setHeatingSchedule('sun_heat', WKEND_ZOFF)

eveningwater = [17, 30, 18, 0]
nowater = []
HMN.Kit.setWaterSchedule('all', eveningwater)

UPSLEEP = 16
UPAWAKE = 18
upwkday_zearly = [5, 0, UPAWAKE, 7, 00, FROST, 20, 30, UPAWAKE, 21, 30, UPSLEEP]
upwkday_zlate = [7, 0, UPAWAKE, 8, 00, FROST, 21, 30, UPAWAKE, 22, 30, UPSLEEP]
upwkday = [7, 0, UPAWAKE, 8, 30, FROST, 21, 00, UPAWAKE, 21, 30, UPSLEEP]
upwkend_zearly = [5, 0, UPAWAKE, 8, 00, FROST, 20, 30, UPAWAKE, 21, 30, UPSLEEP]
upwkend_zlate = [7, 0, UPAWAKE, 9, 30, FROST, 21, 30, UPAWAKE, 22, 30, UPSLEEP]
upwkend = [7, 0, UPAWAKE, 9, 30, FROST, 21, 00, UPAWAKE, 22, 00, UPSLEEP]
DAYFROST = [7, 0, FROST]

HMN.B1.setHeatingSchedule('mon_heat', DAYFROST)
HMN.B1.setHeatingSchedule('tues_heat', DAYFROST)
HMN.B1.setHeatingSchedule('wed_heat', DAYFROST)
HMN.B1.setHeatingSchedule('thurs_heat', DAYFROST)
HMN.B1.setHeatingSchedule('fri_heat', DAYFROST)
HMN.B1.setHeatingSchedule('sat_heat', DAYFROST)
HMN.B1.setHeatingSchedule('sun_heat', DAYFROST)

HMN.B2.setHeatingSchedule('mon_heat', DAYFROST)
HMN.B2.setHeatingSchedule('tues_heat', DAYFROST)
HMN.B2.setHeatingSchedule('wed_heat', DAYFROST)
HMN.B2.setHeatingSchedule('thurs_heat', DAYFROST)
HMN.B2.setHeatingSchedule('fri_heat', DAYFROST)
HMN.B2.setHeatingSchedule('sat_heat', DAYFROST)
HMN.B2.setHeatingSchedule('sun_heat', DAYFROST)

#HMN.hmSetFields('Kit', 'wday_heat', [7, 0, 19, 9, 30, 10, 17, 0, 19, 21, 30, 10])
#HMN.hmSetFields('B1', HMV3_ID,'wday_heat', [7, 0, 18, 8, 30, 10, 20, 30, 18, 22, 0, 16])
#HMN.hmSetFields('B2', HMV3_ID,'wday_heat', [7, 0, 19, 8, 30, 10, 20, 30, 19, 22, 0, 16])
HMN.controllerByName('Cons').set_field('wday_heat', [9, 0, 12, 21, 30, 10, 24, 0, 5, 24, 0, 5])

#HMN.hmSetFields('Kit', 'wend_heat', [7, 0, 19, 21, 30, 10, 24, 0, 5, 24, 0, 5])
#HMN.hmSetFields('B1', HMV3_ID,'wend_heat', [7, 0, 18, 9, 30, 10, 20, 30, 18, 22, 0, 16])
#HMN.hmSetFields('B2', HMV3_ID,'wend_heat', [7, 0, 19, 9, 30, 10, 20, 30, 19, 22, 0, 16])
HMN.controllerByName('Cons').set_field('wend_heat', [9, 0, 12, 21, 30, 10, 24, 0, 5, 24, 0, 5])

HMN.Sit.setHeatingSchedule('wday_heat', DAYFROST)
HMN.Sit.setHeatingSchedule('wend_heat', DAYFROST)

#HMN.hmSetFields("Kit", 'wday_water', [7, 0, 8, 0, 16, 0, 17, 0, 24, 0, 24, 0, 24, 0, 24, 0])
#HMN.hmSetFields("Kit", 'wday_water', [24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0])
#HMN.hmSetFields("Kit", 'wend_water', [8, 0, 9, 0, 18, 0, 19, 0, 24, 0, 24, 0, 24, 0, 24, 0])

#HMN.hmSetField("Kit", 'frosttemp', 9)
#HMN.hmSetField("B1", 'frosttemp', 9)
#HMN.hmSetField("B2", 'frosttemp', 9)
#HMN.hmSetField("Cons", 'frosttemp', 9)


