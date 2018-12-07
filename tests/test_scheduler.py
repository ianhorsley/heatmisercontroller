"""Unittests for heatmisercontroller.scheduler module"""
import unittest
import logging


from heatmisercontroller.schedule_functions import SchedulerDayHeat, SchedulerWeekWater
#from heatmisercontroller.exceptions import hmResponseError

class TestSchedulerDayHeat(unittest.TestCase):
    """Tests for day heat class"""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        self.func = SchedulerDayHeat()
            
    def test_create(self):
        #unique_address,length,divisor, valid range
        self.func.set_raw_all([7, 0, 21, 9, 0, 12, 17, 0, 21, 22, 30, 15])
        self.func.set_raw('tues_heat', [7, 0, 21, 9, 0, 12, 17, 0, 21, 24, 30, 15])
        self.func.display()
        
    def test_getnextday(self):
        self.assertEqual(3, self.func._get_next_day([2, 0, 0, 0]))
        self.assertEqual(1, self.func._get_next_day([7, 0, 0, 0]))
        
    def test_pad_bad_input(self):
        self.assertRaises(IndexError, self.func.pad_schedule, [1])
        self.assertRaises(IndexError, self.func.pad_schedule, [1, 2])
        self.assertRaises(IndexError, self.func.pad_schedule, [1, 2, 3, 4])

    def test_pad(self):
        self.assertEqual([24, 0, 12, 24, 0, 12, 24, 0, 12, 24, 0, 12], self.func.pad_schedule([]))
        self.assertEqual([1, 2, 3, 24, 0, 12, 24, 0, 12, 24, 0, 12], self.func.pad_schedule([1, 2, 3]))

class TestSchedulerWeekWater(unittest.TestCase):
    """Tests for week water class"""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        self.func = SchedulerWeekWater()

    def test_entry_text(self):
        self.assertEqual(self.func.entry_text([12, 12, 14, 30, 15, 00, 15, 30, 17, 00, 24, 00, 24, 00, 24, 00]),"Time 1 On at 12:12 Off at 14:30, Time 2 On at 15:00 Off at 15:30, Time 3 On at 17:00 Time 4 ")
        self.assertEqual(self.func.entry_text([24, 00, 14, 30, 15, 00, 15, 30, 17, 00, 24, 00, 24, 00, 24, 00]),"Time 1 Off at 14:30, Time 2 On at 15:00 Off at 15:30, Time 3 On at 17:00 Time 4 ")
        
    def test_entry(self):
        entry = [12, 12, 14, 30, 15, 00, 15, 30, 17, 00, 24, 00, 24, 00, 24, 00]
        self.func.set_raw('wday_water', entry)
        self.assertEqual(self.func._get_schedule_entry(1), entry)
        self.assertEqual(self.func._get_schedule_entry(5), entry)
        self.assertIsNone(self.func._get_schedule_entry(6))
            
if __name__ == '__main__':
    unittest.main()
