"""Thermostat statemachine to represent heat controller in Heatmiser ThermoStats

Ian Horsley 2018
"""

from transitions import Machine

from .hm_constants import MAX_AGE_MEDIUM
from .schedule_functions import SCH_ENT_TEMP

class Thermostat(object):
    """Thermostat statemachine"""
    states = [{'name': 'off', 'on_enter': 'thres_off'},
            {'name': 'offfrost', 'on_enter': 'thres_frost'},
            {'name': 'frost', 'on_enter': 'thres_frost'},
            {'name': 'setpoint', 'on_enter': 'thres_setpoint'}
            ]
    
    TEMP_STATE_OFF = 0    #thermostat display is off and frost protection disabled
    TEMP_STATE_OFF_FROST = 1 #thermostat display is off and frost protection enabled
    TEMP_STATE_FROST = 2 #frost protection enabled indefinitely
    TEMP_STATE_HOLIDAY = 3 #holiday mode, frost protection for a period
    TEMP_STATE_HELD = 4 #temperature held for a number of hours
    TEMP_STATE_OVERRIDDEN = 5 #temperature overridden until next program time
    TEMP_STATE_PROGRAM = 6 #following program
    
    def thres_off(self, _=None):
        """Entry to off state, set threshold to None and set text."""
        print("STATE off")
        self.threshold = None
        self.text_function = lambda _: "controller off, without frost protection"
        
    def thres_setpoint(self, _=None):
        """Entry to setpoint state, set threshold to setpoint and set text override, hold or program."""
        print("STATE to setpoint ", self.fieldscont.setroomtemp.value)
        self.threshold = self.fieldscont.setroomtemp.value
        
        if not self.fieldscont.tempholdmins.is_unknown() and self.fieldscont.tempholdmins.value != 0:
            self.text_function = lambda infields: "temp held for %i mins at %i"%(infields.tempholdmins.value, infields.setroomtemp.value)
        else:
            self.text_function = self._text_function_over_prog

    def thres_frost(self, _=None):
        """Entry to frost state, set threshold to frost and set text off, frost or holiday."""
        print("STATE to", self.state)
        
        self.threshold = self.fieldscont.frosttemp.value
        
        if self.fieldscont.onoff.is_unknown() or self.fieldscont.onoff.is_value('OFF'):
            self.text_function = lambda _: "controller off, with frost protection"
        elif not self.fieldscont.holidayhours.is_unknown() and not self.fieldscont.holidayhours.is_value('OFF'):
            self.text_function = lambda infields: "controller on holiday for %s hours" % (infields.holidayhours.value)
        elif self.fieldscont.runmode.is_unknown() or self.fieldscont.runmode.is_value('FROST'):
            self.text_function = lambda _: "controller in frost mode"
        else:
            self.text_function = None
    
    @staticmethod
    def _text_function_over_prog(infields):
        infields.read_field('currenttime', MAX_AGE_MEDIUM)
            
        locatimenow = infields.currenttime.localtimearray()
        scheduletarget = infields.heat_schedule.get_current_schedule_item(locatimenow)

        if infields.setroomtemp.is_unknown():
            return "temp unknown"
        if infields.setroomtemp.value != scheduletarget[SCH_ENT_TEMP]:
            basetext = "temp overridden"
        else:
            basetext = "temp set"
        return basetext + " to %0.1f until %02d:%02d" % (infields.setroomtemp.value, infields.nexttarget()[1], infields.nexttarget()[2])
    
    def get_state_text(self):
        """Return text desription of current state."""
        return self.text_function(self.fieldscont)
    
    def cond_frost(self, _=None):
        """Check is no frost triggers set."""
        return self.fieldscont.holidayhours.is_value('OFF') and self.fieldscont.runmode.is_value('HEAT')

    def cond_on(self, _=None):
        """Check switched on."""
        return self.fieldscont.onoff.is_value('ON')
        
    def cond_frostprotdisable(self, _=None):
        """Check frost protection is disabled."""
        return self.fieldscont.frostprotdisable.is_value('ON')
       
    def __init__(self, name, fieldcontainer):
    
        # intialise variables
        self.name = name #name of thermostat
        self.threshold = None #to store current thershold value
        self.text_function = lambda _: "unknown state"
        
        # field pointers
        self.fieldscont = fieldcontainer
        
        self.machine = Machine(model=self, states=Thermostat.states, initial='off')
        
        self.machine.add_transition('switch_off', ['frost', 'setpoint'], 'off', conditions='cond_frostprotdisable')
        self.machine.add_transition('switch_off', ['frost', 'setpoint'], 'offfrost', unless='cond_frostprotdisable')
        self.machine.add_transition('switch_off', 'offfrost', 'off', conditions='cond_frostprotdisable')
        self.machine.add_transition('switch_off', 'off', 'offfrost', unless='cond_frostprotdisable')

        self.machine.add_transition('switch_swap', '*', 'setpoint', conditions=['cond_frost', 'cond_on'])
        self.machine.add_transition('switch_swap', '*', 'frost', conditions='cond_on', unless='cond_frost')
        