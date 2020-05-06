"""Set of tests for field functions

## Imported crc16 function not tested"""

import unittest
import logging

from heatmisercontroller.fields import HeatmiserFieldUnknown, HeatmiserField
from heatmisercontroller.hm_constants import MAX_AGE_LONG

class TestFields(unittest.TestCase):
    """Unitests for framing"""
    def setUp(self):
        self.field1 = HeatmiserFieldUnknown('test1', 5, [0, 12], MAX_AGE_LONG)
        self.field2 = HeatmiserFieldUnknown('test2', 5, [0, 12], MAX_AGE_LONG)
        self.field3 = HeatmiserField('test2', 5, [0, 12], MAX_AGE_LONG)
        
        
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
