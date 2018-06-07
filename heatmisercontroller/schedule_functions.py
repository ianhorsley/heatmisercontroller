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

class scheduler(object):
  #entry is a day or week/end, item is a part within the entry
  fieldbase = None
  fieldnames = ['mon','tues','wed','thurs','fri','sat','sun','wday','wend']
  
  def __init__(self):
    if not self.fieldbase is None:
      self.entrynames = [x + self.fieldbase for x in self.entrynames]
      self.fieldnames = [x + self.fieldbase for x in self.fieldnames]
    self.entries = dict.fromkeys(self.fieldnames, None)
    
  def set_raw_all(self, schedule):
    for entry in self.fieldnames:
      self.set_raw(entry, schedule)

  def set_raw(self, entry, schedule):
    if not entry in self.fieldnames:
      raise ValueError('Schedule entry does not exist %s'%entry)
    if not len(schedule) is self.valuesperentry * self.entriesperday:
      raise ValueError('Schedule entry wrong length %i'%len(entry))
    self.entries[entry] = schedule
    
  def pad_schedule(self,schedule):
    if not len(schedule)%self.valuesperentry == 0:
      raise IndexError("Schedule length not multiple of %d"%self.valuesperentry)
    pad_item = [HOUR_UNUSED,0,12][0:self.valuesperentry]
  
    return schedule + pad_item * ((self.valuesperentry * self.entriesperday - len(schedule))/self.valuesperentry)
    
  def display(self):
    print self.title + " Schedule"
    
    for name, entry in itertools.izip(self.printnames,self.entrynames):
      if self.entries[entry] is None:
        textstr = "None"
      else:
        textstr = self.entry_text(self.entries[entry])
      print(name.ljust(10) + textstr)
      logging.info(textstr)
      
  def _chunks(self, l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]
  
  def _reversechunks(self, l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(len(l)-n, -1, -n):
        yield l[i:i + n]
      
  def getCurrentScheduleItem(self,timearray):
    ####check time and vars current
    
    todayschedule = self._getScheduleEntry(timearray[CURRENT_TIME_DAY])
      
    scheduletarget = self._getCurrentItemFromAnEntry(todayschedule,timearray)
      
    if scheduletarget == None:
      yestschedule = self._getPreviousScheduleEntry(timearray)
      scheduletarget = self._getLastItemFromAnEntry(yestschedule)
      return [self._getPreviousDay(timearray)] + scheduletarget
    else:
      return [timearray[CURRENT_TIME_DAY]] + scheduletarget
      
  def getNextScheduleItem(self,timearray):

    todayschedule = self._getScheduleEntry(timearray[CURRENT_TIME_DAY])
    
    scheduletarget = self._getNextItemFromAnEntry(todayschedule,timearray)
      
    if scheduletarget == None:
      tomschedule = self._getNextScheduleEntry(timearray)
      scheduletarget = self._getFirstItemFromAnEntry(tomschedule)
      return [self._getNextDay(timearray)] + scheduletarget
    else:
      return [timearray[CURRENT_TIME_DAY]] + scheduletarget
      
  def _getNextItemFromAnEntry(self,schedule,timearray):
    scheduletarget = None
    dayminutes = timearray[CURRENT_TIME_HOUR] * HOUR_MINUTES + timearray[CURRENT_TIME_MIN]

    for i in self._reversechunks(schedule,self.valuesperentry):
      if dayminutes < i[MAP_HOUR] * HOUR_MINUTES + i[MAP_MIN] and i[MAP_HOUR] != HOUR_UNUSED:
        scheduletarget = i
    
    return scheduletarget
  
  def _getCurrentItemFromAnEntry(self,schedule,timearray):
    scheduletarget = None
    dayminutes = timearray[CURRENT_TIME_HOUR] * HOUR_MINUTES + timearray[CURRENT_TIME_MIN]
    
    for i in self._chunks(schedule,self.valuesperentry):
      if dayminutes >= i[MAP_HOUR] * HOUR_MINUTES + i[MAP_MIN] and i[MAP_HOUR] != HOUR_UNUSED:
        scheduletarget = i
    
    return scheduletarget
    
  def _getPreviousScheduleEntry(self,timearray):
    return self._getScheduleEntry(self._getPreviousDay(timearray))

  def _getNextScheduleEntry(self,timearray):
    return self._getScheduleEntry(self._getNextDay(timearray))

  def _getPreviousDay(self,timearray):
    #shift from 1-7 to 0-6, subtract 1, modulo, shift back to 1-7
    return ((timearray[CURRENT_TIME_DAY] - 1 - 1 ) % 7 ) + 1
    
  def _getNextDay(self,timearray):
    #shift from 1-7 to 0-6, add 1, modulo, shift back to 1-7
    return ((timearray[CURRENT_TIME_DAY] - 1 + 1 ) % 7 ) + 1
    
  def _getFirstItemFromAnEntry(self,schedule):
    #gets first schedule entry if valid (not 24)
    firstentry = self._chunks(schedule,self.valuesperentry).next()
    if firstentry[MAP_HOUR] != HOUR_UNUSED:
      return firstentry
    else:
      return None

  def _getLastItemFromAnEntry(self,schedule):
    #gets last valid schedule entry (not 24)
    scheduletarget = None
    for i in self._reversechunks(schedule,self.valuesperentry):
          if i[MAP_HOUR] != HOUR_UNUSED:
            scheduletarget = i
            break
    
    return scheduletarget

class schedulerday(scheduler):
  entrynames = ['mon','tues','wed','thurs','fri','sat','sun']
  printnames = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
  
  def _getScheduleEntry(self, day):
    return self.entries[self.entrynames[day - 1]]

class schedulerweek(scheduler):
  entrynames = ['wday','wend']
  printnames = ['Weekdays','Weekends']
  
  def _getScheduleEntry(self, day):
    if day == 6 or day == 7:
      return self.entries[self.entrynames[1]]
    elif day >= 1 and day <= 5:
      return self.entries[self.entrynames[0]]
    else:
      raise ValueError("Day not recognised")
      
class schedulerheat(scheduler):
  title = 'Heating'
  valuesperentry = 3
  entriesperday = 4
  fieldbase = '_heat'
  
  def entry_text(self, data):
    tempstr = ''
    for set in self._chunks(data,self.valuesperentry):
      if set[MAP_HOUR] != HOUR_UNUSED:
        tempstr += "%02d:%02d at %02iC " % (set[MAP_HOUR],set[MAP_MIN],set[MAP_TEMP])
        
    return tempstr
  
class schedulerwater(scheduler):
  title = 'Hot Water'
  valuesperentry = 2
  entriesperday = 8
  fieldbase = '_water'
  
  def entry_text(self, data):
    toggle = True
    count = 1
  
    tempstr = ''
    for set in self._chunks(data,2):
      if set[0] != HOUR_UNUSED:
        if toggle:
          tempstr += "Time %i On at %02d:%02d " % (count,set[0],set[1])
        else:
          tempstr += "Off at %02d:%02d, " % (set[0],set[1])
          count=count+1
        toggle = not toggle
        
    return tempstr
  
class schedulerdayheat(schedulerday, schedulerheat):
  pass
class schedulerweekheat(schedulerweek, schedulerheat):
  pass
class schedulerdaywater(schedulerday, schedulerwater):
  pass
class schedulerweekwater(schedulerweek, schedulerwater):
  pass
