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
            self.fieldscont.read_field('currenttime', MAX_AGE_MEDIUM)
            
            locatimenow = self.fieldscont.currenttime.localtimearray()
            scheduletarget = self.fieldscont.heat_schedule.get_current_schedule_item(locatimenow)

            if self.setroomtemp.value != scheduletarget[SCH_ENT_TEMP]:
                basetext = "temp overridden"
                
            else:
                basetext = "temp set"
            self.text_function = lambda input: basetext + "temp overridden to %0.1f until %02d:%02d" % (input.setroomtemp.value, input.nexttarget()[1], input.nexttarget()[2])

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
        