"""Unittests for heatmisercontroller.network module"""
import unittest
import logging
import os

from heatmisercontroller.network import HeatmiserNetwork
from heatmisercontroller.exceptions import HeatmiserControllerSetupInitError
from heatmisercontroller.devices import HeatmiserDevice
from mock_serial import SerialTestClass, SetupTestClass, MockHeatmiserAdaptor

class TestNetwork(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
    
    def test_network_creation(self):
        HeatmiserNetwork()
        
    def test_network_find(self):
        module_path = os.path.abspath(os.path.dirname(__file__))
        configfile = os.path.join(module_path, "../bin/nocontrollers.conf")
    
        HMN = HeatmiserNetwork(configfile)

        setup = SetupTestClass()
        adaptor = MockHeatmiserAdaptor(setup)
        HMN.adaptor = adaptor
        
        #queue some data to recieve
        responses = [[4, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], [4, 0, 1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 1]]
        adaptor.setresponse(responses)
        
        HMN.find_devices(3)

        self.assertEqual(len(HMN.controllers), 2)
        self.assertIsInstance(HMN.controllers[0], HeatmiserDevice)
        self.assertIsInstance(HMN.controllers[1], HeatmiserDevice)
        self.assertEqual(HMN.controllers[1].address, 2)
        
    def test_network_stat_add(self):
        HMN = HeatmiserNetwork()
        self.assertEqual(1, HMN.get_stat_address('Kit'))
    
    def test_no_file(self):
        with self.assertRaises(HeatmiserControllerSetupInitError):
            HMN = HeatmiserNetwork('nofile.conf')
        
if __name__ == '__main__':
    unittest.main()
