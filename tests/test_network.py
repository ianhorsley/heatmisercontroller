"""Unittests for heatmisercontroller.network module"""
import unittest
import logging

from heatmisercontroller.network import HeatmiserNetwork
from heatmisercontroller.exceptions import HeatmiserResponseError
from mock_serial import SerialTestClass, SetupTestClass

class TestNetwork(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
    
    def test_network_creation(self):
        HeatmiserNetwork()
        
    def test_network_stat_add(self):
        HMN = HeatmiserNetwork()
        self.assertEqual(1, HMN.get_stat_address('Kit'))
        
if __name__ == '__main__':
    unittest.main()
