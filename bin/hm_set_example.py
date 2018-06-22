#!/usr/bin/env python
#
# Ian Horsley 2018

#
# Sets a bunch of different configurations on stats
#
import logging

from heatmisercontroller.logging_setup import initialize_logger
from heatmisercontroller.hm_constants import *
from heatmisercontroller.network import *

initialize_logger('logs', logging.INFO, True)

hmn1 = HeatmiserNetwork()

#hmn1.hmSetTemp("Kit",25)
#hmn1.Kit.holdTemp(30,21) #mins, temp
#hmn1.Kit.releaseHoldTemp()

#hmn1.hmSetTemp("Cons",25)
#hmn1.hmReleaseTemp("Cons")
#hmn1.All.setField('holidayhours',96)
hmn1.All.releaseHoliday()

hmn1.Kit.setField('hotwaterdemand',WRITE_HOTWATERDEMAND_PROG)

#hmn1.hmSetField(BROADCAST_ADDR,'runmode',WRITE_RUNMODE_HEATING)
hmn1.All.setOn()
#hmn1.hmUpdateTime(2)
#hmn1.controllerByName('B1').setOff()
#hmn1.hmSetField(BROADCAST_ADDR,HMV3_ID,'onoff',WRITE_ONOFF_ON)  
#hmn1.hmSetField('Cons',HMV3_ID,'onoff',WRITE_ONOFF_OFF)

hmn1.All.setField('runmode',WRITE_RUNMODE_HEATING)

#hmn1.B2.setTemp(24)
#hmn1.Kit.setTemp(24)
#hmn1.B1.setTemp(24)
#hmn1.B2.setTemp(24)
#hmn1.Cons.setTemp(24)

#hmn1.All.setTemp(24)

hmn1.Kit.releaseTemp()
hmn1.B1.releaseTemp()
hmn1.B2.releaseTemp()
hmn1.Cons.releaseTemp()

downInactive = 20
downActive = 19
frost = 12
dayfrost = [7,0,frost]

wkday_zearly =    [5,00,downActive,8,30,frost,15,00,downInactive,21,00,frost]
wkday_zlate =     [7,00,downInactive,12,00,frost,17,00,downInactive,21,30,frost]
wkday_ztraining = [7,00,downActive,8,30,frost,16,30,downInactive,21,00,frost]
wkend_zearly =    [5,00,downInactive,21,30,frost]
wkend_zlate =     [7,00,downInactive,21,30,frost]
wkend_zoff =      [7,00,downInactive,21,30,frost]
hmn1.Kit.setHeatingSchedule('mon_heat',wkend_zearly)
hmn1.Kit.setHeatingSchedule('tues_heat',wkend_zearly)
hmn1.Kit.setHeatingSchedule('wed_heat',wkday_ztraining)
hmn1.Kit.setHeatingSchedule('thurs_heat',wkend_zearly)
hmn1.Kit.setHeatingSchedule('fri_heat',wkend_zearly)
hmn1.Kit.setHeatingSchedule('sat_heat',wkend_zoff)
hmn1.Kit.setHeatingSchedule('sun_heat',wkend_zoff)

eveningwater = [17,30,18,0]
nowater = []
hmn1.Kit.setWaterSchedule('all',eveningwater)

upSleep = 16
upAwake = 18
upwkday_zearly =  [5,0,upAwake,7,00,frost,20,30,upAwake,21,30,upSleep]
upwkday_zlate =   [7,0,upAwake,8,00,frost,21,30,upAwake,22,30,upSleep]
upwkday =         [7,0,upAwake,8,30,frost,21,00,upAwake,21,30,upSleep]
upwkend_zearly =  [5,0,upAwake,8,00,frost,20,30,upAwake,21,30,upSleep]
upwkend_zlate =   [7,0,upAwake,9,30,frost,21,30,upAwake,22,30,upSleep]
upwkend =         [7,0,upAwake,9,30,frost,21,00,upAwake,22,00,upSleep]
dayfrost = [7,0,frost]

hmn1.B1.setHeatingSchedule('mon_heat',dayfrost)
hmn1.B1.setHeatingSchedule('tues_heat',dayfrost)
hmn1.B1.setHeatingSchedule('wed_heat',dayfrost)
hmn1.B1.setHeatingSchedule('thurs_heat',dayfrost)
hmn1.B1.setHeatingSchedule('fri_heat',dayfrost)
hmn1.B1.setHeatingSchedule('sat_heat',dayfrost)
hmn1.B1.setHeatingSchedule('sun_heat',dayfrost)

hmn1.B2.setHeatingSchedule('mon_heat',dayfrost)
hmn1.B2.setHeatingSchedule('tues_heat',dayfrost)
hmn1.B2.setHeatingSchedule('wed_heat',dayfrost)
hmn1.B2.setHeatingSchedule('thurs_heat',dayfrost)
hmn1.B2.setHeatingSchedule('fri_heat',dayfrost)
hmn1.B2.setHeatingSchedule('sat_heat',dayfrost)
hmn1.B2.setHeatingSchedule('sun_heat',dayfrost)

#hmn1.hmSetFields('Kit','wday_heat',[7,0,19,9,30,10,17,0,19,21,30,10])
#hmn1.hmSetFields('B1',HMV3_ID,'wday_heat',[7,0,18,8,30,10,20,30,18,22,0,16])
#hmn1.hmSetFields('B2',HMV3_ID,'wday_heat',[7,0,19,8,30,10,20,30,19,22,0,16])
hmn1.controllerByName('Cons').setField('wday_heat',[9,0,12,21,30,10,24,0,5,24,0,5])

#hmn1.hmSetFields('Kit','wend_heat',[7,0,19,21,30,10,24,0,5,24,0,5])
#hmn1.hmSetFields('B1',HMV3_ID,'wend_heat',[7,0,18,9,30,10,20,30,18,22,0,16])
#hmn1.hmSetFields('B2',HMV3_ID,'wend_heat',[7,0,19,9,30,10,20,30,19,22,0,16])
hmn1.controllerByName('Cons').setField('wend_heat',[9,0,12,21,30,10,24,0,5,24,0,5])

hmn1.Sit.setHeatingSchedule('wday_heat',dayfrost)
hmn1.Sit.setHeatingSchedule('wend_heat',dayfrost)

#hmn1.hmSetFields("Kit",'wday_water',[7,0,8,0,16,0,17,0,24,0,24,0,24,0,24,0])
#hmn1.hmSetFields("Kit",'wday_water',[24,0,24,0,24,0,24,0,24,0,24,0,24,0,24,0])
#hmn1.hmSetFields("Kit",'wend_water',[8,0,9,0,18,0,19,0,24,0,24,0,24,0,24,0])

#hmn1.hmSetField("Kit",'frosttemp',9)
#hmn1.hmSetField("B1",'frosttemp',9)
#hmn1.hmSetField("B2",'frosttemp',9)
#hmn1.hmSetField("Cons",'frosttemp',9)


