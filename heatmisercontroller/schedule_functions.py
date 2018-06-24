"""Classes for holding and processing Heatmier heating and hot water schedule fields"""
import logging
import itertools

from hm_constants import CURRENT_TIME_DAY, CURRENT_TIME_HOUR, CURRENT_TIME_MIN

#mapping for chunks of heating schedule for a day
MAP_HOUR = 0
MAP_MIN = 1
MAP_TEMP = 2
#hour that indicates unused item
HOUR_UNUSED = 24
#index for returned schedule
SCH_ENT_DAY = 0
SCH_ENT_HOUR = 1
SCH_ENT_MIN = 2
SCH_ENT_TEMP = 3
#useful constants
HOUR_MINUTES = 60

class Scheduler(object):
    """General Schedule base class, providing a set of inherited methods"""
    #entry is a day or week/end, item is a part within the entry
    fieldbase = None
    fieldnames = ['mon', 'tues', 'wed', 'thurs', 'fri', 'sat', 'sun', 'wday', 'wend']

    def __init__(self):
        if not self.fieldbase is None:
            self.entrynames = [x + self.fieldbase for x in self.entrynames]
            self.fieldnames = [x + self.fieldbase for x in self.fieldnames]
        self.entries = dict.fromkeys(self.fieldnames, None)

    def set_raw_all(self, schedule):
        """Set all fields to same schedule"""
        for entry in self.fieldnames:
            self.set_raw(entry, schedule)

    def set_raw(self, entry, schedule):
        """Set single field to schedule"""
        if not entry in self.fieldnames:
            raise ValueError('Schedule entry does not exist %s'%entry)
        if not len(schedule) is self.valuesperentry * self.entriesperday:
            raise ValueError('Schedule entry wrong length %i'%len(entry))
        self.entries[entry] = schedule

    def pad_schedule(self, schedule):
        """Pads a partial schedule up to correct length"""
        if not len(schedule)%self.valuesperentry == 0:
            raise IndexError("Schedule length not multiple of %d"%self.valuesperentry)
        pad_item = [HOUR_UNUSED, 0, 12][0:self.valuesperentry]

        return schedule + pad_item * ((self.valuesperentry * self.entriesperday - len(schedule))/self.valuesperentry)

    def display(self):
        """Prints schedule to stdout"""
        print self.title + " Schedule"

        for name, entry in itertools.izip(self.printnames, self.entrynames):
            if self.entries[entry] is None:
                textstr = "None"
            else:
                textstr = self.entry_text(self.entries[entry])
            print(name.ljust(10) + textstr)
            logging.info(textstr)

    @staticmethod
    def _chunks(fulllist, chunklength):
        """Yield successive n-sized chunks from l."""
        for pos in range(0, len(fulllist), chunklength):
            yield fulllist[pos:pos + chunklength]
    
    @staticmethod
    def _reversechunks(fulllist, chunklength):
        """Yield successive n-sized chunks from l."""
        for pos in range(len(fulllist)-chunklength, -1, -chunklength):
            yield fulllist[pos:pos + chunklength]
            
    def get_current_schedule_item(self, timearray):
        ####check time and vars current
        
        todayschedule = self._get_schedule_entry(timearray[CURRENT_TIME_DAY])
            
        scheduletarget = self._get_current_item_from_an_entry(todayschedule, timearray)
            
        if scheduletarget == None:
            yestschedule = self._get_previous_schedule_entry(timearray)
            scheduletarget = self._get_last_item_from_an_entry(yestschedule)
            return [self._get_previous_day(timearray)] + scheduletarget
        else:
            return [timearray[CURRENT_TIME_DAY]] + scheduletarget
            
    def get_next_schedule_item(self, timearray):

        todayschedule = self._get_schedule_entry(timearray[CURRENT_TIME_DAY])
        
        scheduletarget = self._get_next_item_from_an_entry(todayschedule, timearray)
            
        if scheduletarget == None:
            tomschedule = self._get_next_schedule_entry(timearray)
            scheduletarget = self._get_first_item_from_an_entry(tomschedule)
            return [self._get_next_day(timearray)] + scheduletarget
        else:
            return [timearray[CURRENT_TIME_DAY]] + scheduletarget
            
    def _get_next_item_from_an_entry(self, schedule, timearray):
        scheduletarget = None
        dayminutes = timearray[CURRENT_TIME_HOUR] * HOUR_MINUTES + timearray[CURRENT_TIME_MIN]

        for i in self._reversechunks(schedule, self.valuesperentry):
            if dayminutes < i[MAP_HOUR] * HOUR_MINUTES + i[MAP_MIN] and i[MAP_HOUR] != HOUR_UNUSED:
                scheduletarget = i
        
        return scheduletarget
    
    def _get_current_item_from_an_entry(self, schedule, timearray):
        scheduletarget = None
        dayminutes = timearray[CURRENT_TIME_HOUR] * HOUR_MINUTES + timearray[CURRENT_TIME_MIN]
        
        for i in self._chunks(schedule, self.valuesperentry):
            if dayminutes >= i[MAP_HOUR] * HOUR_MINUTES + i[MAP_MIN] and i[MAP_HOUR] != HOUR_UNUSED:
                scheduletarget = i
        
        return scheduletarget
        
    def _get_previous_schedule_entry(self, timearray):
        return self._get_schedule_entry(self._get_previous_day(timearray))

    def _get_next_schedule_entry(self, timearray):
        return self._get_schedule_entry(self._get_next_day(timearray))

    @staticmethod
    def _get_previous_day(timearray):
        #shift from 1-7 to 0-6, subtract 1, modulo, shift back to 1-7
        return ((timearray[CURRENT_TIME_DAY] - 1 - 1) % 7) + 1
        
    @staticmethod
    def _get_next_day(timearray):
        #shift from 1-7 to 0-6, add 1, modulo, shift back to 1-7
        return ((timearray[CURRENT_TIME_DAY] - 1 + 1) % 7) + 1
        
    def _get_first_item_from_an_entry(self, schedule):
        #gets first schedule entry if valid (not 24)
        firstentry = self._chunks(schedule, self.valuesperentry).next()
        if firstentry[MAP_HOUR] != HOUR_UNUSED:
            return firstentry
        else:
            return None

    def _get_last_item_from_an_entry(self, schedule):
        #gets last valid schedule entry (not 24)
        scheduletarget = None
        for i in self._reversechunks(schedule, self.valuesperentry):
            if i[MAP_HOUR] != HOUR_UNUSED:
                scheduletarget = i
                break
        return scheduletarget

class SchedulerDay(Scheduler):
    entrynames = ['mon', 'tues', 'wed', 'thurs', 'fri', 'sat', 'sun']
    printnames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    def _get_schedule_entry(self, day):
        return self.entries[self.entrynames[day - 1]]

class SchedulerWeek(Scheduler):
    entrynames = ['wday', 'wend']
    printnames = ['Weekdays', 'Weekends']
    
    def _get_schedule_entry(self, day):
        if day == 6 or day == 7:
            return self.entries[self.entrynames[1]]
        elif day >= 1 and day <= 5:
            return self.entries[self.entrynames[0]]
        else:
            raise ValueError("Day not recognised")
            
class SchedulerHeat(Scheduler):
    title = 'Heating'
    valuesperentry = 3
    entriesperday = 4
    fieldbase = '_heat'
    
    def entry_text(self, data):
        tempstr = ''
        for valueset in self._chunks(data, self.valuesperentry):
            if valueset[MAP_HOUR] != HOUR_UNUSED:
                tempstr += "%02d:%02d at %02iC " % (valueset[MAP_HOUR], valueset[MAP_MIN], valueset[MAP_TEMP])
                
        return tempstr
    
class SchedulerWater(Scheduler):
    title = 'Hot Water'
    valuesperentry = 2
    entriesperday = 8
    fieldbase = '_water'
    
    def entry_text(self, data):
        toggle = True
        count = 1
    
        tempstr = ''
        for dataset in self._chunks(data, 2):
            if dataset[0] != HOUR_UNUSED:
                if toggle:
                    tempstr += "Time %i On at %02d:%02d " %(count, dataset[0], dataset[1])
                else:
                    tempstr += "Off at %02d:%02d, " %(dataset[0], dataset[1])
                    count=count+1
                toggle = not toggle
                
        return tempstr
    
class SchedulerDayHeat(SchedulerDay, SchedulerHeat):
    pass
class SchedulerWeekHeat(SchedulerWeek, SchedulerHeat):
    pass
class SchedulerDayWater(SchedulerDay, SchedulerWater):
    pass
class SchedulerWeekWater(SchedulerWeek, SchedulerWater):
    pass
