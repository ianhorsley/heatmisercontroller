"""Unittests for heatmisercontroller.thermostatstate module"""
import unittest
import logging

from heatmisercontroller.fields import HeatmiserFieldSingleReadOnly, HeatmiserFieldSingle, HeatmiserFieldDouble
from heatmisercontroller.fields_special import HeatmiserFieldTime, VALUES_OFF_ON, VALUES_ON_OFF, VALUES_OFF
from heatmisercontroller.hm_constants import *
from heatmisercontroller.thermostatstate import Thermostat
from heatmisercontroller.schedule_functions import SchedulerDayHeat, SchedulerWeekHeat

class FieldsContainer(object):
    """Class to hold fields. Test replacement for full blown thermostat device."""
    def read_field(self, _a, _b):
        """Method to mirror thermostat method."""
        pass

class TestState(unittest.TestCase):
    """Unit tests for state class."""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        self.fc = FieldsContainer()
        
        fc = self.fc
        fc.frostprotdisable = HeatmiserFieldSingleReadOnly('frostprotdisable', 7, [0, 1], MAX_AGE_LONG, VALUES_OFF_ON)  #0=enable frost prot when display off,  (opposite in protocol manual,  but tested and user guide is correct)  (default should be frost proc enabled)
        fc.programmode = HeatmiserFieldSingleReadOnly('programmode', 16, [0, 1], MAX_AGE_LONG, {'5_2': 0, '7': 1})  #0=5/2,  1= 7day
        fc.frosttemp = HeatmiserFieldSingle('frosttemp', 17, [7, 17], MAX_AGE_LONG)  #default is 12,  frost protection temperature
        fc.setroomtemp = HeatmiserFieldSingle('setroomtemp', 18, [5, 35], MAX_AGE_USHORT)
        fc.onoff = HeatmiserFieldSingle('onoff', 21, [0, 1], MAX_AGE_SHORT, VALUES_ON_OFF)  #1 = on
        fc.runmode = HeatmiserFieldSingle('runmode', 23, [0, 1], MAX_AGE_SHORT, {'HEAT': 0, 'FROST': 1})   #0 = heating mode,  1 = frost protection mode
        fc.holidayhours = HeatmiserFieldDouble('holidayhours', 24, [0, 720], MAX_AGE_SHORT, VALUES_OFF)  #range guessed and tested,  setting to 0 cancels hold and puts back to program 
        
        fc.tempholdmins = HeatmiserFieldDouble('tempholdmins', 32, [0, 5760], MAX_AGE_SHORT, VALUES_OFF)  #range guessed and tested,  setting to 0 cancels hold and puts setroomtemp back to program
        fc.currenttime = HeatmiserFieldTime('currenttime', 43, MAX_AGE_USHORT)  #day (Mon - Sun),  hour,  min,  sec.
        
        fc.heat_schedule = SchedulerWeekHeat()
        padschedule = fc.heat_schedule.pad_schedule([1, 0, 16])
        for fieldname in fc.heat_schedule.get_entry_names('all'):
            fc.heat_schedule.set_raw(fieldname, padschedule)
        #create stat
        self.t = Thermostat('room', self.fc)
        
        #on and off
        fc.frostprotdisable.add_notifable_is(fc.frostprotdisable.readvalues['ON'], self.t.switch_off)
        fc.frostprotdisable.add_notifable_is(fc.frostprotdisable.readvalues['OFF'], self.t.switch_off)
        fc.onoff.add_notifable_is(fc.onoff.readvalues['OFF'], self.t.switch_off)
        fc.onoff.add_notifable_is(fc.onoff.readvalues['ON'], self.t.switch_swap)
        #change within on
        fc.setroomtemp.add_notifable_changed(self.t.switch_swap)
        ###don't need the following if not modelling override holds or program events internally
        ###program change event
        #ftempholdmins.add_notifable_is(ftempholdmins.readvalues['OFF'], self.t.switch_swap) #check triggered by value force change and data change
        #ftempholdmins.add_notifable_is_not(ftempholdmins.readvalues['OFF'], self.t.switch_swap)
        #between frost and setpoint
        fc.runmode.add_notifable_is(fc.runmode.readvalues['HEAT'], self.t.switch_swap)
        fc.runmode.add_notifable_is(fc.runmode.readvalues['FROST'], self.t.switch_swap)
        fc.holidayhours.add_notifable_is(fc.holidayhours.readvalues['OFF'], self.t.switch_swap)
        fc.holidayhours.add_notifable_is_not(self.t.switch_swap)

    def test_state_set(self):
        print("intial", self.t.state)
        fc = self.fc
        
        print("finished connecting observers")
        fc.onoff.update_value(fc.onoff.readvalues['OFF'], 0)
        fc.frostprotdisable.update_value(fc.frostprotdisable.readvalues['OFF'], 0)
        fc.holidayhours.update_value(fc.holidayhours.readvalues['OFF'], 0)
        fc.runmode.update_value(fc.runmode.readvalues['HEAT'], 0)
        print("finished setting initial values")

        self.assertTrue(self.t.is_offfrost())
        #fulloff
        fc.frostprotdisable.update_value(1, 0)
        self.assertTrue(self.t.is_off())
        fc.onoff.update_value(1, 0)
        self.assertTrue(self.t.is_setpoint())
        self.assertEqual(self.t.threshold, None)
        fc.setroomtemp.update_value(10, 0)
        self.assertTrue(self.t.is_setpoint())
        self.assertEqual(self.t.threshold, 10)
        fc.setroomtemp.update_value(10, 0)
        fc.runmode.update_value(1, 0)
        self.assertTrue(self.t.is_frost())
        self.assertEqual(self.t.threshold, None)
        fc.holidayhours.update_value(5, 0)
        self.assertTrue(self.t.is_frost())
        fc.holidayhours.update_value(0, 0)
        fc.holidayhours.update_value(5, 0)
        self.assertTrue(self.t.is_frost())
        fc.runmode.update_value(0, 0)
        self.assertTrue(self.t.is_frost())
        fc.holidayhours.update_value(0, 0)
        self.assertTrue(self.t.is_setpoint())

    def test_text(self):
        fc = self.fc
        fc.holidayhours.update_value(fc.holidayhours.readvalues['OFF'], 0)
        fc.tempholdmins.update_value(fc.tempholdmins.readvalues['OFF'], 0)
        
        print(self.t.get_state_text())
        self.assertEqual(self.t.get_state_text(), "unknown state")
        
        fc.onoff.update_value(fc.onoff.readvalues['OFF'], 0)
        fc.frostprotdisable.update_value(fc.frostprotdisable.readvalues['ON'], 0)
        print(self.t.get_state_text())
        self.assertEqual(self.t.get_state_text(), "controller off, without frost protection")
        
        fc.frostprotdisable.update_value(fc.frostprotdisable.readvalues['OFF'], 0)
        print(self.t.get_state_text())
        self.assertEqual(self.t.get_state_text(), "controller off, with frost protection")
        
        fc.runmode.update_value(fc.runmode.readvalues['FROST'], 0)
        fc.onoff.update_value(fc.onoff.readvalues['ON'], 0)
        self.assertEqual(self.t.get_state_text(), "controller in frost mode")
        
        fc.runmode.update_value(fc.runmode.readvalues['HEAT'], 0)
        self.assertEqual(self.t.get_state_text(), "temp unknown")
        
        #### Not finished testing
        fc.setroomtemp.update_value(16, 0)
        #self.assertEqual(self.t.get_state_text(), "controller in frost mode")
        