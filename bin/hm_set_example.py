#!/usr/bin/env python
"""Example of setting configurations on Heatmiser stats
Ian Horsley 2018
"""

import logging

from heatmisercontroller.logging_setup import initialize_logger_full
from heatmisercontroller.network import HeatmiserNetwork

initialize_logger_full('logs', logging.INFO)

HMN = HeatmiserNetwork()

### New observations
# Setting holiday replaces overide and on exit returns to prog (not override)

#HMN.Kit.holdTemp(30,21) #mins, temp
#HMN.All.release_hold_temp()

#HMN.release_temp("Cons")
#HMN.All.set_field('holidayhours', 230)
#HMN.All.release_holiday()

#HMN.Kit.set_field('hotwaterdemand', 'PROG')
#quit()
#HMN.All.set_field('onoff', 'ON')
#HMN.All.set_field('runmode', 'FROST')
#HMN.hmUpdateTime(2)

HMN.B1.set_field('runmode', 'HEAT')
HMN.B2.set_field('runmode', 'HEAT')
HMN.Kit.set_field('runmode', 'HEAT')
HMN.Cons.set_field('runmode', 'FROST')
HMN.Sit.set_field('runmode', 'HEAT')

HMN.All.set_field('frosttemp', 10)
HMN.Cons.set_field('frosttemp', 7)

print(HMN.Cons.read_field('frostprotdisable'))
HMN.Cons.set_field('onoff', 'OFF')

#print HMN.All.read_field('holidayhours', 0)
#exit()

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

SPECIAL = [6, 00, 22, 15, 00, DOWNINACTIVE, 21, 00, SLEEP]
WKDAY_ZEARLY = [5, 00, DOWNACTIVE, 8, 30, FROST, 15, 00, DOWNINACTIVE, 21, 00, SLEEP]
WKDAY_ZLATE = [7, 00, DOWNINACTIVE, 12, 00, FROST, 17, 00, DOWNINACTIVE, 21, 30, SLEEP]
WKDAY_ZTRAINING = [6, 30, DOWNACTIVE, 8, 30, FROST, 16, 30, DOWNINACTIVE, 21, 00, SLEEP]
WKEND_ZEARLY = [5, 00, DOWNINACTIVE, 21, 30, SLEEP]
WKEND_ZLATE = [7, 00, DOWNINACTIVE, 21, 30, SLEEP]
WKEND_ZOFF = [6, 00, DOWNINACTIVE, 21, 00, SLEEP]
WKDAY_ZAWAY = [7, 00, DOWNACTIVE, 8, 30, FROST, 17, 30, DOWNINACTIVE, 21, 00, SLEEP]
WKDAY_ZSTARTNIGHT = WKEND_ZOFF

HMN.Kit.set_heating_schedule('mon', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('tues', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('wed', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('thurs', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('fri', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('sat', WKEND_ZOFF)
HMN.Kit.set_heating_schedule('sun', WKEND_ZOFF)

#HMN.Sit.set_heating_schedule('wday', DAYFROST)
#HMN.Sit.set_heating_schedule('wend', DAYFROST)

HMN.Sit.set_heating_schedule('mon', WKEND_ZOFF)
HMN.Sit.set_heating_schedule('tues', WKEND_ZOFF)
HMN.Sit.set_heating_schedule('wed', WKEND_ZOFF)
HMN.Sit.set_heating_schedule('thurs', WKEND_ZOFF)
HMN.Sit.set_heating_schedule('fri', WKEND_ZOFF)
HMN.Sit.set_heating_schedule('sat', WKEND_ZOFF)
HMN.Sit.set_heating_schedule('sun', WKEND_ZOFF)

EVENINGWATER = [17, 30, 18, 30]
NOWATER = [24, 00, 21, 30]
HMN.Kit.set_water_schedule('all', NOWATER)
HMN.Kit.set_water_schedule('tues', EVENINGWATER)
HMN.Kit.set_water_schedule('fri', EVENINGWATER)

UPSLEEP = 16
UPAWAKE = 19
UPWKDAY_ZEARLY = [5, 0, UPAWAKE, 7, 00, FROST, 15, 00, UPAWAKE, 19, 30, UPSLEEP]
UPWKDAY_ZLATE = [6, 0, UPAWAKE, 8, 00, FROST, 17, 00, UPAWAKE, 20, 30, UPSLEEP]
UPWKDAY = [7, 0, UPAWAKE, 8, 30, FROST, 21, 00, UPAWAKE, 21, 30, UPSLEEP]
UPWKEND_ZEARLY = [5, 0, UPAWAKE, 8, 00, FROST, 15, 00, UPAWAKE, 19, 30, UPSLEEP]
UPWKEND_ZLATE = [7, 0, UPAWAKE, 9, 30, FROST, 17, 00, UPAWAKE, 20, 30, UPSLEEP]
UPWKEND = [7, 0, UPAWAKE, 9, 30, FROST, 17, 00, UPAWAKE, 19, 00, UPSLEEP]
UPWKDAY_OLIN = [6, 0, UPAWAKE, 9, 00, FROST, 18, 00, UPAWAKE, 19, 00, UPSLEEP]
DAYFROST = [7, 0, FROST]

HMN.B1.set_heating_schedule('mon', UPWKDAY_ZLATE)
HMN.B1.set_heating_schedule('tues', UPWKDAY_ZLATE)
HMN.B1.set_heating_schedule('wed', UPWKDAY_ZLATE)
HMN.B1.set_heating_schedule('thurs', UPWKDAY_ZLATE)
HMN.B1.set_heating_schedule('fri', UPWKDAY_ZLATE)
HMN.B1.set_heating_schedule('sat', UPWKDAY_ZLATE)
HMN.B1.set_heating_schedule('sun', UPWKDAY_ZLATE)

HMN.B2.set_heating_schedule('mon', UPWKDAY_OLIN)
HMN.B2.set_heating_schedule('tues', UPWKDAY_OLIN)
HMN.B2.set_heating_schedule('wed', UPWKDAY_OLIN)
HMN.B2.set_heating_schedule('thurs', UPWKDAY_OLIN)
HMN.B2.set_heating_schedule('fri', UPWKDAY_OLIN)
HMN.B2.set_heating_schedule('sat', UPWKDAY_OLIN)
HMN.B2.set_heating_schedule('sun', UPWKDAY_OLIN)

HMN.get_controller_by_name('Cons').set_field('wday_heat', [9, 0, 12, 21, 30, 10, 24, 0, 5, 24, 0, 5])
HMN.get_controller_by_name('Cons').set_field('wend_heat', [9, 0, 12, 21, 30, 10, 24, 0, 5, 24, 0, 5])
