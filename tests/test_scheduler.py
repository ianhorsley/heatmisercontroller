import unittest
import logging
#import time

from heatmisercontroller.schedule_functions import SchedulerDayHeat
#from heatmisercontroller.hm_constants import HMV3_ID, PRT_HW_MODEL, PROG_MODE_DAY
#from heatmisercontroller.exceptions import hmResponseError

class test_SchedulerDayHeat(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.ERROR)
    #network, address, protocol, short_name, long_name, model, mode
    #self.func = hmController(None, 1, HMV3_ID, 'test', 'test controller', PRT_HW_MODEL, PROG_MODE_DAY)
      
  def test_create(self):
    #unique_address,length,divisor, valid range
    self.func = SchedulerDayHeat()
    self.func.set_raw_all([7,0,21,9,0,12,17,0,21,22,30,15])
    self.func.set_raw('tues_heat',[7,0,21,9,0,12,17,0,21,24,30,15])
    self.func.display()
    
  def test_getnextday(self):
    self.func = SchedulerDayHeat()
    self.assertEqual(3, self.func._get_next_day([2,0,0,0]) )
    self.assertEqual(1, self.func._get_next_day([7,0,0,0]) )
    
  def test_pad_bad_input(self):
    self.func = SchedulerDayHeat()
    self.assertRaises(IndexError, self.func.pad_schedule, [1])
    self.assertRaises(IndexError, self.func.pad_schedule, [1, 2])
    self.assertRaises(IndexError, self.func.pad_schedule, [1, 2, 3, 4])

  def test_pad(self):
    self.func = SchedulerDayHeat()
    self.assertEqual([24, 0, 12, 24, 0, 12, 24, 0, 12, 24, 0, 12], self.func.pad_schedule([]))
    self.assertEqual([1, 2, 3, 24, 0, 12, 24, 0, 12, 24, 0, 12], self.func.pad_schedule([1, 2, 3]))
    
      
if __name__ == '__main__':
    unittest.main()

