
from heatmisercontroller.fields import *
from heatmisercontroller.hm_constants import *

from heatmisercontroller.thermostatstate import Thermostat

from heatmisercontroller import fields  

ffrostprocdisable = HeatmiserFieldSingleReadOnly('frostprotdisable', 7, [0, 1], MAX_AGE_LONG, VALUES_OFF_ON)  #0=enable frost prot when display off,  (opposite in protocol manual,  but tested and user guide is correct)  (default should be frost proc enabled)
fprogrammode = HeatmiserFieldSingleReadOnly('programmode', 16, [0, 1], MAX_AGE_LONG, {'5_2': 0, '7': 1})  #0=5/2,  1= 7day
ffrosttemp = HeatmiserFieldSingle('frosttemp', 17, [7, 17], MAX_AGE_LONG),  #default is 12,  frost protection temperature
fsetroomtemp = HeatmiserFieldSingle('setroomtemp', 18, [5, 35], MAX_AGE_USHORT)
fonoff = HeatmiserFieldSingle('onoff', 21, [0, 1], MAX_AGE_SHORT, VALUES_ON_OFF)  #1 = on
frunmode = HeatmiserFieldSingle('runmode', 23, [0, 1], MAX_AGE_SHORT, {'HEAT': 0, 'FROST': 1})   #0 = heating mode,  1 = frost protection mode
fholidayhours = HeatmiserFieldDouble('holidayhours', 24, [0, 720], MAX_AGE_SHORT, VALUES_OFF)  #range guessed and tested,  setting to 0 cancels hold and puts back to program 
#HeatmiserFieldUnknown('unknown', 26, 1, [], MAX_AGE_LONG, 6),  # gap from 26 to 31
ftempholdmins = HeatmiserFieldDouble('tempholdmins', 32, [0, 5760], MAX_AGE_SHORT, VALUES_OFF)  #range guessed and tested,  setting to 0 cancels hold and puts setroomtemp back to program
     
t1 = Thermostat('room')
t1.holidayhours = fholidayhours
t1.runmode = frunmode
t1.frostprocdisable = ffrostprocdisable
t1.setroomtemp = fsetroomtemp
t1.onoff = fonoff
print "intial", t1.state

#on and off
ffrostprocdisable.add_notifable_is(ffrostprocdisable.readvalues['ON'], t1.switch_off)
ffrostprocdisable.add_notifable_is(ffrostprocdisable.readvalues['OFF'], t1.switch_off)
fonoff.add_notifable_is(fonoff.readvalues['OFF'], t1.switch_off)
fonoff.add_notifable_is(fonoff.readvalues['ON'], t1.switch_swap)
#change within on
fsetroomtemp.add_notifable_changed(t1.switch_swap)
###don't need the following if not modelling override holds or program events internally
###program change event
#ftempholdmins.add_notifable_is(ftempholdmins.readvalues['OFF'], t1.switch_swap) #check triggered by value force change and data change
#ftempholdmins.add_notifable_is_not(ftempholdmins.readvalues['OFF'], t1.switch_swap)
#between frost and setpoint
frunmode.add_notifable_is(frunmode.readvalues['HEAT'], t1.switch_swap)
frunmode.add_notifable_is(frunmode.readvalues['FROST'], t1.switch_swap)
fholidayhours.add_notifable_is(fholidayhours.readvalues['OFF'], t1.switch_swap)
fholidayhours.add_notifable_is_not(t1.switch_swap)
print "finished connecting observers"
fonoff.update_value(fonoff.readvalues['OFF'], 0)
ffrostprocdisable.update_value(ffrostprocdisable.readvalues['OFF'], 0)
fholidayhours.update_value(fholidayhours.readvalues['OFF'], 0)
frunmode.update_value(frunmode.readvalues['HEAT'], 0)
print "finished setting initial values"

ffrostprocdisable.update_value(1, 0)
fonoff.update_value(1, 0)
fsetroomtemp.update_value(10, 0)
fsetroomtemp.update_value(10, 0)
frunmode.update_value(1, 0)
fholidayhours.update_value(5, 0)
fholidayhours.update_value(0, 0)
fholidayhours.update_value(5, 0)
frunmode.update_value(0, 0)
fholidayhours.update_value(0, 0)

print "end", fholidayhours.nots_is[0], fholidayhours.nots_is_not