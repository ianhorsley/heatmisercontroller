"""Thermostat statemachine to represent heat controller in Heatmiser ThermoStats

Ian Horsley 2018
"""

from transitions import Machine

from hm_constants import MAX_AGE_MEDIUM
from schedule_functions import SCH_ENT_TEMP

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
    
    def thres_off(self, arg=None):
        """Entry to off state, set threshold to None and set text."""
        print("STATE off")
        self.threshold = None
        self.text_function = lambda input: "controller off without frost protection",
        
    def thres_setpoint(self, arg=None):
        """Entry to setpoint state, set threshold to setpoint and set text override, hold or program."""
        print("STATE to setpoint ", self.fieldscont.setroomtemp.value)
        self.threshold = self.fieldscont.setroomtemp.value
        
        if self.fieldscont.tempholdmins.value != 0:
            self.text_function = lambda input: "temp held for %i mins at %i"%(input.tempholdmins.value, input.setroomtemp.value)
        else:
            self.text_function = self._text_function_over_prog

    def thres_frost(self, arg=None):
        print("STATE to", self.state)
        self.threshold = self.fieldscont.frosttemp.value
        
        if self.fieldscont.onoff.is_value('OFF'):
            self.text_function = lambda input: "controller off"
        elif self.fieldscont.holidayhours.value != 0:
            self.text_function = lambda input: "controller on holiday for %s hours" % (input.holidayhours.value)
        elif self.fieldscont.runmode.is_value('FROST'):
            self.text_function = lambda input: "controller in frost mode"
        else:
            self.text_function = None
    
    @staticmethod
    def _text_function_over_prog(input):
        input.read_field('currenttime', MAX_AGE_MEDIUM)
            
        locatimenow = input.currenttime.localtimearray()
        scheduletarget = input.heat_schedule.get_current_schedule_item(locatimenow)

        if input.setroomtemp.value != scheduletarget[SCH_ENT_TEMP]:
            basetext = "temp overridden"
        else:
            basetext = "temp set"
        return basetext + "temp overridden to %0.1f until %02d:%02d" % (input.setroomtemp.value, input.nexttarget()[1], input.nexttarget()[2])
    
    def get_state_text(self):
        """Return text desription of current state"""
        return self.text_function(self.fieldscont)
    
    def cond_frost(self, arg=None):
        return self.fieldscont.holidayhours.is_value('OFF') and self.fieldscont.runmode.is_value('HEAT')

    def cond_on(self, arg=None):
        return self.fieldscont.onoff.is_value('ON')
        
    def cond_frostprotdisable(self, arg=None):
        return self.fieldscont.frostprotdisable.is_value('ON')
       
    def __init__(self, name, fieldcontainer):
    
        # intialise variables
        self.name = name #name of thermostat
        self.threshold = None #to store current thershold value
        self.text_function = lambda _:"unknown state"
        
        # field pointers
        self.fieldscont = fieldcontainer
        
        self.machine = Machine(model=self, states=Thermostat.states, initial='off')
        
        self.machine.add_transition('switch_off', ['frost', 'setpoint'], 'off', conditions='cond_frostprotdisable')
        self.machine.add_transition('switch_off', ['frost', 'setpoint'], 'offfrost', unless='cond_frostprotdisable')
        self.machine.add_transition('switch_off', 'offfrost', 'off', conditions='cond_frostprotdisable')
        self.machine.add_transition('switch_off', 'off', 'offfrost', unless='cond_frostprotdisable')
        
        #self.machine.add_transition('switch_on', ['off', 'offfrost'], 'setpoint', conditions='cond_frost')
        #self.machine.add_transition('switch_on', ['off', 'offfrost'], 'frost', unless='cond_frost')
        
        self.machine.add_transition('switch_swap', '*', 'setpoint', conditions=['cond_frost', 'cond_on'])
        #self.machine.add_transition('switch_swap', ['off', 'offfrost', 'setpoint'], 'frost', conditions='cond_on', unless='cond_frost')
        self.machine.add_transition('switch_swap', '*', 'frost', conditions='cond_on', unless='cond_frost')
        