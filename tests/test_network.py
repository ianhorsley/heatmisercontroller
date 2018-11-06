"""Unittests for heatmisercontroller.network module"""
import unittest
import logging
import os

from heatmisercontroller.network import HeatmiserNetwork
from heatmisercontroller.exceptions import HeatmiserControllerSetupInitError
from heatmisercontroller.devices import HeatmiserDevice
from mock_serial import SetupTestClass, MockHeatmiserAdaptor

class TestNetwork(unittest.TestCase):
    """Unit tests for network class."""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
    
    @staticmethod
    def test_network_creation():
        module_path = os.path.abspath(os.path.dirname(__file__))
        configfile = os.path.join(module_path, "hmcontroller.conf")
        HeatmiserNetwork(configfile)
        
    def test_network_find(self):
        module_path = os.path.abspath(os.path.dirname(__file__))
        configfile = os.path.join(module_path, "nocontrollers.conf")
    
        hmn = HeatmiserNetwork(configfile)

        setup = SetupTestClass()
        adaptor = MockHeatmiserAdaptor(setup)
        hmn.adaptor = adaptor

        #queue some data to recieve
        responses = [[4, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1], [4, 0, 1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 1]]
        adaptor.setresponse(responses)
        
        hmn.find_devices(3)
        
        self.assertEqual(len(hmn.controllers), 2)
        self.assertIsInstance(hmn.controllers[0], HeatmiserDevice)
        self.assertIsInstance(hmn.controllers[1], HeatmiserDevice)
        self.assertEqual(hmn.controllers[1].set_address, 2)
        
    def test_network_stat_add(self):
        module_path = os.path.abspath(os.path.dirname(__file__))
        configfile = os.path.join(module_path, "hmcontroller.conf")
        hmn = HeatmiserNetwork(configfile)
        self.assertEqual(1, hmn.get_stat_address('Kit'))
    
    def test_no_file(self):
        with self.assertRaises(HeatmiserControllerSetupInitError):
            HeatmiserNetwork('nofile.conf')
        
if __name__ == '__main__':
    unittest.main()
