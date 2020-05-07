"""Set of tests for field functions

## Imported crc16 function not tested"""

import unittest
import datetime
import time

from heatmisercontroller.fields import HeatmiserFieldUnknown, HeatmiserField
from heatmisercontroller.fields_special import HeatmiserFieldTime
from heatmisercontroller.hm_constants import MAX_AGE_LONG, CURRENT_TIME_DAY, CURRENT_TIME_HOUR, CURRENT_TIME_MIN, CURRENT_TIME_SEC
from heatmisercontroller.exceptions import HeatmiserControllerTimeError

class TestFields(unittest.TestCase):
    """Unitests for framing"""
    def setUp(self):
        self.field1 = HeatmiserFieldUnknown('test1', 5, [0, 12], MAX_AGE_LONG)
        self.field2 = HeatmiserFieldUnknown('test2', 5, [0, 12], MAX_AGE_LONG)
        self.field3 = HeatmiserField('test2', 5, [0, 12], MAX_AGE_LONG)

    def time_from_array(self, timearray):
        t = datetime.time(timearray[CURRENT_TIME_HOUR], timearray[CURRENT_TIME_MIN], timearray[CURRENT_TIME_SEC])
        heatmiserday = timearray[CURRENT_TIME_DAY] #1 = Monday
        basedate = datetime.date(2011, 7, 2)
        d = self.next_weekday(basedate, heatmiserday - 1) # 0 = Monday, 1=Tuesday, 2=Wednesday...
        dt = datetime.datetime.combine(d, t)
        dt_tuple = dt.timetuple()
        return time.mktime(dt_tuple)

    def next_weekday(self, d, weekday):
        days_ahead = weekday - d.weekday()
        if days_ahead <= 0: # Target day already happened this week
            days_ahead += 7
        return d + datetime.timedelta(days_ahead)

    def create_time_field(self, lastreadtimearray, timearray):
        fieldtime = HeatmiserFieldTime('test1', 5, MAX_AGE_LONG)
        fieldtime.lastreadtime = self.time_from_array(lastreadtimearray) #1 = Monday
        fieldtime.value = timearray
        fieldtime.comparecontrollertime()
        return fieldtime
        
    def test_overridden_functions(self):
        self.field1.value = 1
        self.field2.value = 1
        self.field3.value = 2

        self.assertEqual(self.field1 == self.field2, True)
        self.assertEqual(self.field1 == self.field3, False)
        self.assertEqual(self.field1 > self.field3, False)
        self.assertEqual(self.field3 > self.field1, True)
        self.assertEqual(str(self.field1), "1")

    def test_not_implimented(self):
        with self.assertRaises(NotImplementedError):
            self.field1.update_value(12, 12)
        with self.assertRaises(NotImplementedError):
            self.field1.check_values(12)
        with self.assertRaises(NotImplementedError):
            self.field3._calculate_value(12)
        with self.assertRaises(NotImplementedError):
            self.field3.format_data_from_value(12)
        with self.assertRaises(NotImplementedError):
            self.field3.update_data(12, 12)

    def test_time(self):
        self.field1 = HeatmiserFieldTime('test1', 5, MAX_AGE_LONG)
        #self.assertEqual(self.field1.localtimearray(1588782127.06), [3, 17, 22, 7])
        self.assertEqual(self.field1.localtimearray(self.time_from_array([3, 17, 22, 7])), [3, 17, 22, 7])
        
    def test_compare_time(self):
        #currentday is numbered 1-7 for M-S
        #local time and remote time
        fieldtime = self.create_time_field([1, 17, 22, 7], [1, 17, 22, 7])
        self.assertEqual(fieldtime.timeerr, 0)

        fieldtime = self.create_time_field([1, 17, 22, 8], [1, 17, 22, 7])
        self.assertEqual(fieldtime.timeerr, -1)
        fieldtime = self.create_time_field([1, 17, 22, 6], [1, 17, 22, 7])
        self.assertEqual(fieldtime.timeerr, 1)
        
        fieldtime = self.create_time_field([1, 0, 0, 1], [7, 23, 59, 59])
        self.assertEqual(fieldtime.timeerr, -2)
        fieldtime = self.create_time_field([7, 23, 59, 59], [1, 0, 0, 1])
        self.assertEqual(fieldtime.timeerr, 2)
        
        TIME_ERR_LIMIT = 10000000
        with self.assertRaises(HeatmiserControllerTimeError):
            fieldtime = self.create_time_field([1, 17, 22, 7], [3, 17, 22, 7])
        with self.assertRaises(HeatmiserControllerTimeError):
            fieldtime = self.create_time_field([3, 17, 22, 7], [1, 17, 22, 7])
        
        TIME_ERR_LIMIT = 10
        self.create_time_field([1, 17, 22, 40], [1, 17, 22, 30])
        self.create_time_field([1, 17, 22, 30], [1, 17, 22, 40])
        with self.assertRaises(HeatmiserControllerTimeError):
            fieldtime = self.create_time_field([1, 17, 22, 41], [1, 17, 22, 30])
        with self.assertRaises(HeatmiserControllerTimeError):
            fieldtime = self.create_time_field([1, 17, 22, 30], [1, 17, 22, 41])

    def test_field_assignment(self):
        print self.field1.value
        fieldtemp = self.field1
        valuetemp = self.field1.value
        print fieldtemp.value
        fieldtemp.value = 1
        print self.field1.value
        print self.field1
        print valuetemp
        