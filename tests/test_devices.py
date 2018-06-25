"""Unittests for heatmisercontroller.devices module"""
import unittest
import logging
import time

from heatmisercontroller.devices import HeatmiserDevice, HeatmiserBroadcastDevice
from heatmisercontroller.hm_constants import HMV3_ID, PROG_MODES, PROG_MODE_DAY, DCB_INVALID, WRITE_HOTWATERDEMAND_OVER_OFF, READ_HOTWATERDEMAND_OFF, WRITE_HOTWATERDEMAND_PROG
from heatmisercontroller.exceptions import HeatmiserResponseError, HeatmiserControllerTimeError
from heatmisercontroller.adaptor import HeatmiserAdaptor

from mock_serial import SetupTestClass

class ArgumentStore(object):
    """Class used to replace class method allowing arguments to be captured"""
    def __init__(self):
        self.arguments = ()
    
    def store(self, *args):
        """Method used to replace other writing methods"""
        self.arguments = args

class MockHeatmiserAdaptor(HeatmiserAdaptor):
    """Modified HeatmiserAdaptor that stores writes and and provide read responses."""
    def __init__(self, setup):
        super(MockHeatmiserAdaptor, self).__init__(setup)
        self.reset()
    
    def reset(self):
        """Resets input and output arrays"""
        self.arguments = []
        self.outputs = []
        
    def write_to_device(self, network_address, protocol, unique_address, length, payload):
        """Stores the arguments sent to write"""
        self.arguments.append((network_address, protocol, unique_address, length, payload))

    def setresponse(self, inputs):
        """Sets responses to read from device.
        
        Expects a list of lists"""
        self.outputs = inputs

    def read_from_device(self, network_address, protocol, unique_start_address, expected_length, readall=False):
        """Stores the arguments sent to read and provides a response"""
        self.arguments.append((network_address, protocol, unique_start_address, expected_length, readall))
        return self.outputs.pop(0)

class TestBroadcastController(unittest.TestCase):
    """Unittests for reading data functions"""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        setup = SetupTestClass()
        self.adaptor = MockHeatmiserAdaptor(setup)
        #network, address, protocol, short_name, long_name, model, mode
        #self.func = HeatmiserDevice(None, 1, HMV3_ID, 'test', 'test controller', 'prt_hw_model', PROG_MODE_DAY)
        self.settings = {'address':1, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_hw_model', 'expected_prog_mode':PROG_MODE_DAY, 'autoreadall':True}
        dev1 = HeatmiserDevice(self.adaptor, self.settings)
        self.settings2 = {'address':2, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_hw_model', 'expected_prog_mode':PROG_MODE_DAY, 'autoreadall':True}
        dev2 = HeatmiserDevice(self.adaptor, self.settings)
        self.func = HeatmiserBroadcastDevice(self.adaptor, 'Broadcaster', [dev1, dev2])
            
    def test_read_fields(self):
        print
        responses = [[0, 0, 0, 0, 0, 0, 0, 170], [0, 1, 0, 0, 0, 0, 0, 180]]
        self.adaptor.setresponse(responses)
        self.assertEqual([[0, 17], [1, 18]], self.func.read_fields(['tempholdmins', 'airtemp'], 0))
        
class TestReadingData(unittest.TestCase):
    """Unittests for reading data functions"""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        #network, address, protocol, short_name, long_name, model, mode
        #self.func = HeatmiserDevice(None, 1, HMV3_ID, 'test', 'test controller', 'prt_hw_model', PROG_MODE_DAY)
        self.settings = {'address':1, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_hw_model', 'expected_prog_mode':PROG_MODE_DAY}
        self.settings2 = {'address':1, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_e_model', 'expected_prog_mode':PROG_MODE_DAY, 'autoreadall':True}
        self.func = HeatmiserDevice(None, self.settings)
            
    def test_procfield(self):
        #unique_address, length, divisor, valid range
        self.func._procfield([1], ['test', 0, 1, 1, []])
        self.func._procfield([1], ['test', 0, 1, 1, [0, 1]])
        self.func._procfield([1, 1], ['test', 0, 2, 1, [0, 257]])
        self.func._procfield([4], ['model', 0, 1, 1, []])
        self.func._procfield([PROG_MODES[PROG_MODE_DAY]], ['programmode', 0, 1, 1, []])
        
    def test_procfield_range(self):
        with self.assertRaises(HeatmiserResponseError):
            self.func._procfield([3], ['test', 0, 1, 1, [0, 1]])
            
    def test_procfield_model(self):
        with self.assertRaises(HeatmiserResponseError):
            self.func._procfield([3], ['model', 0, 1, 1, []])
        
    def test_procpayload(self):
        print "tz %i alt tz %i"%(time.timezone, time.altzone)
        goodmessage = [1, 37, 0, 22, 4, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 38, 1, 9, 12, 28, 1, 1, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0, 220, 0, 0, 0, 3, 14, 49, 36, 7, 0, 19, 9, 30, 10, 17, 0, 19, 21, 30, 10, 7, 0, 19, 21, 30, 10, 24, 0, 5, 24, 0, 5, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 8, 0, 9, 0, 18, 0, 19, 0, 24, 0, 24, 0, 24, 0, 24, 0, 7, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 19, 8, 30, 12, 16, 30, 20, 21, 0, 12, 7, 0, 20, 12, 0, 12, 17, 0, 20, 21, 30, 12, 5, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 20, 12, 0, 12, 17, 0, 20, 21, 30, 12, 7, 0, 12, 24, 0, 12, 24, 0, 12, 24, 0, 12, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0]

        self.func.autocorrectime = False
        basetime = (6 - 2) * 86400 + 53376.0 + year2000
        self.func.lastreadtime = basetime - get_offset(basetime)
        self.func._procpayload(goodmessage)

    def test_procpartpayload(self):
        self.func._procpartpayload([0, 1], 'tempholdmins', 'tempholdmins')
        self.assertEqual(1, self.func.tempholdmins)
        self.func._procpartpayload([0, 1, 0, 0, 0, 0, 0, 0], 'tempholdmins', 'airtemp')
        self.assertEqual(1, self.func.tempholdmins)
        
    def test_readall(self):
        pass
        # setup = SetupTestClass()
        # adaptor = MockHeatmiserAdaptor(setup)
        # self.func = HeatmiserDevice(adaptor, self.settings)
        # basetime = (6 - 2) * 86400 + 53376.0 + year2000
        # self.func.lastreadtime = basetime - get_offset(basetime)
        # responses = [[1, 37, 0, 22, 4, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 38, 1, 9, 12, 28, 1, 1, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0, 220, 0, 0, 0, 3, 14, 49, 36, 7, 0, 19, 9, 30, 10, 17, 0, 19, 21, 30, 10, 7, 0, 19, 21, 30, 10, 24, 0, 5, 24, 0, 5, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 8, 0, 9, 0, 18, 0, 19, 0, 24, 0, 24, 0, 24, 0, 24, 0, 7, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 19, 8, 30, 12, 16, 30, 20, 21, 0, 12, 7, 0, 20, 12, 0, 12, 17, 0, 20, 21, 30, 12, 5, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 20, 12, 0, 12, 17, 0, 20, 21, 30, 12, 7, 0, 12, 24, 0, 12, 24, 0, 12, 24, 0, 12, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0]]
        # adaptor.setresponse(responses)
        # self.func.read_all()
        # self.assertEqual([(1, 3, 18, 0, True)], adaptor.arguments)
        
    def test_readvariables(self):
        setup = SetupTestClass()
        adaptor = MockHeatmiserAdaptor(setup)
        self.func = HeatmiserDevice(adaptor, self.settings)
        
        #queue some data to recieve
        responses = [[17, 30, 1, 1, 1, 1, 0, 0], [0, 0, 17, 0, 17, 0, 17, 0, 0, 0, 0]]
        adaptor.setresponse(responses)
        #run command
        self.func.get_variables()
        self.assertEqual([(1, 3, 18, 8, False), (1, 3, 32, 11, False)], adaptor.arguments)
        self.assertEqual(17, self.func.setroomtemp)
        self.assertEqual(0, self.func.hotwaterdemand)

    def test_read_field(self):
        setup = SetupTestClass()
        adaptor = MockHeatmiserAdaptor(setup)
        self.func = HeatmiserDevice(adaptor, self.settings2)
        responses = [[0, 170]]
        adaptor.setresponse(responses)
        self.assertEqual(17, self.func.read_field('airtemp', 1))
        
    def test_read_fields(self):
        setup = SetupTestClass()
        adaptor = MockHeatmiserAdaptor(setup)
        self.func = HeatmiserDevice(adaptor, self.settings2)
        responses = [[0, 170]]
        adaptor.setresponse(responses)
        self.assertEqual([17], self.func.read_fields(['airtemp'], 1))
        responses = [[0, 0, 0, 0, 0, 0, 0, 170]]
        adaptor.setresponse(responses)
        self.assertEqual([0, 17], self.func.read_fields(['tempholdmins', 'airtemp'], 0))
        responses = [[3], [0, 100]]
        adaptor.setresponse(responses)
        self.assertEqual([3, 10], self.func.read_fields(['model', 'airtemp'], 0))
        responses = [[3], [0, 100, 0, 1]]
        adaptor.setresponse(responses)
        print self.func.read_fields(['model', 'airtemp', 'heatingdemand'], 0)
        responses = [[3], [0, 100, 0, 1]]
        adaptor.setresponse(responses)
        print self.func.read_fields(['model', 'airtemp', 'hotwaterdemand'], 0)
        responses = [[3, 0, 1, 0, 0, 0, 0, 4, 0, 0, 0, 0, 1, 7, 5, 20, 0, 0, 0], [0, 100, 0, 1]]
        adaptor.setresponse(responses)
        print self.func.read_fields(['model', 'airtemp', 'hotwaterdemand', 'keylock'], 0)
        responses = [[0, 3, 0, 1, 0, 0, 0, 0, 4, 0, 0, 0, 0, 1, 7, 5, 20, 0, 0, 0, 0, 0, 0, 0]]
        adaptor.setresponse(responses)
        print self.func.read_fields(['holidayhours', 'version'], 0)
        responses = [[0, 3, 0, 1, 0, 0, 0, 0, 4, 0, 0, 0], [0, 3, 0, 1, 0, 0, 0, 0, 4, 0, 0, 0]]
        adaptor.setresponse(responses)
        print self.func.read_fields(['mon_heat', 'sun_heat'], 0)
        
class TestOtherFunctions(unittest.TestCase):
    """Unittests for other functions"""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        self.settings = {'address':1, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_e_model', 'expected_prog_mode':PROG_MODE_DAY}
        self.func = HeatmiserDevice(None, self.settings)
    
    def test_get_dcb_address(self):
        self.assertEqual(0, self.func._get_dcb_address(0))
        self.assertEqual(24, self.func._get_dcb_address(24))
        self.assertEqual(DCB_INVALID, self.func._get_dcb_address(26))
        
    def test_getfieldblocks(self):
        self.assertEqual([[25, 29, 8]], self.func._get_field_blocks_from_range('remoteairtemp', 'hotwaterdemand'))
        self.assertEqual([[31, 31, 4]], self.func._get_field_blocks_from_range('hotwaterdemand', 'currenttime'))
        self.assertEqual([[0, 22, 26], [24, 29, 10], [31, 31, 4]], self.func._get_field_blocks_from_range('DCBlen', 'currenttime'))
        self.assertEqual([[0, 22, 26], [24, 29, 10], [31, 33, 28], [36, 42, 84]], self.func._get_field_blocks_from_range('DCBlen', 'sun_water'))
        
    def test_checkblock4(self):
        #print 'DCBlen','sun_water'
        #print self.func._getFieldBlocks('DCBlen','sun_water')
        #from timeit import default_timer as timer
        #start = timer()
        for _ in range(1):
            self.func._get_field_blocks_from_range('DCBlen', 'sun_water')
        #print (timer()-start)/1000
        
    def test_build_dcb_tables(self):
        self.func._build_dcb_tables()
        expected = [[0, 0], [25, 25], [26, None], [31, None], [32, 26], [186, 147], [187, None], [298, None]]
        for u, d in expected:
            self.assertEqual(d, self.func._uniquetodcb[u])

def get_offset(timenum):
    #gettime zone offset for that date
    is_dst = time.daylight and time.localtime(timenum).tm_isdst > 0
    utc_offset = - (time.altzone if is_dst else time.timezone)
    return utc_offset
    
YEAR2000 = (30 * 365 + 7) * 86400 #get some funny effects if you use times from 1970
        
class TestTimeFunctions(unittest.TestCase):
    """Unittests for time functions"""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        self.settings = {'address':1, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_hw_model', 'expected_prog_mode':PROG_MODE_DAY}
        self.func = HeatmiserDevice(None, self.settings)
        
    def test_comparecontrollertime_none(self):
        with self.assertRaises(HeatmiserResponseError):
            self.func._comparecontrollertime()
            
    def test_comparecontrollertime_bad(self):
        basetime = (1 + 1) * 86400 + 9 * 3600 + 33 * 60 + 0 + YEAR2000
        self.func.datareadtime['currenttime'] = basetime - get_offset(basetime) #has been read
        self.func.data['currenttime'] = self.func.currenttime = [1, 0, 0, 0]
        with self.assertRaises(HeatmiserControllerTimeError):
            self.func._comparecontrollertime()
        
    def test_comparecontrollertime_1(self):
        basetime = (4 + 1) * 86400 + 9 * 3600 + 33 * 60 + 5 + YEAR2000
        self.func.datareadtime['currenttime'] = basetime - get_offset(basetime) #has been read
        self.func.data['currenttime'] = self.func.currenttime = [4, 9, 33, 0]
        #print "s ", self.func._localtimearray(self.func.datareadtime['currenttime']), self.func.data['currenttime'], self.func.datareadtime['currenttime'], time.localtime(self.func.datareadtime['currenttime']).tm_hour, time.localtime(self.func.datareadtime['currenttime']), "e"
        self.func._comparecontrollertime()
        self.assertEqual(5, self.func.timeerr)
        
    def test_comparecontrollertime_2(self):
        #self.func.datareadtime['currenttime'] = ( 7 + 3) * 86400 + 23 * 3600 + 59 * 60 + 55 - self.utc_offset #has been read
        basetime = (7 + 1) * 86400 + 23 * 3600 + 59 * 60 + 55 + YEAR2000
        self.func.datareadtime['currenttime'] = basetime - get_offset(basetime) #has been read
        self.func.data['currenttime'] = self.func.currenttime = [1, 0, 0, 0]
        self.func._comparecontrollertime()
        self.assertEqual(5, self.func.timeerr)

    def test_localtimearray(self):
        hour = time.localtime(1528350527).tm_hour
        self.assertEqual([4, hour, 48, 47], self.func._localtimearray(1528350527))
        self.assertEqual([7, hour, 48, 47], self.func._localtimearray(1528350527-86400*4))

class TestSettingData(unittest.TestCase):
    """Unittests for setting data functions"""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        self.settings = {'address':5, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_e_model', 'expected_prog_mode':PROG_MODE_DAY}
        setup = SetupTestClass()
        self.tester = MockHeatmiserAdaptor(setup)
        #self.tester.write_to_device = self.tester.store
        self.func = HeatmiserDevice(self.tester, self.settings)
        
    def test_setfield_1(self):
        #checks the arguments sent to write_to_device
        #fieldname, payload
        self.func.set_field('frosttemp', 7)
        self.assertEqual(self.tester.arguments, [(5, 3, 17, 1, [7])])
        self.assertEqual(self.func.frosttemp, 7)
        
    def test_setfield_2(self):
        self.func.autocorrectime = False
        #self.func.lastreadtime = 7 * 86400 + 7 *3600 + 7 * 60 - 3600
        self.func.lastreadtime = time.time()
        loctime = self.func._localtimearray(self.func.lastreadtime)
        self.func.set_field('currenttime', loctime)
        self.assertEqual(self.tester.arguments, [(5, 3, 43, 4, loctime)])

    def test_setfield_notvalid(self):
        with self.assertRaises(IndexError):
            self.func.set_field('hotwaterdemand', WRITE_HOTWATERDEMAND_OVER_OFF)
        
    def test_setfield_3(self):
        """Check hotwaterdemand mapping"""
        settings2 = {'address':1, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_hw_model', 'expected_prog_mode':PROG_MODE_DAY}
        self.func._update_settings(settings2, None)
        #make sure read time is set and check value
        self.func.set_field('hotwaterdemand', WRITE_HOTWATERDEMAND_OVER_OFF)
        self.assertNotEqual(self.func.datareadtime['hotwaterdemand'], None)
        self.assertEqual(self.func.data['hotwaterdemand'], READ_HOTWATERDEMAND_OFF)
        self.func._adaptor.reset()
        #check releasing works
        self.func.set_field('hotwaterdemand', WRITE_HOTWATERDEMAND_PROG)
        self.assertEqual(self.tester.arguments, [(1, 3, 42, 1, [WRITE_HOTWATERDEMAND_PROG])])
        self.assertEqual(self.func.hotwaterdemand, None)
        self.assertEqual(self.func.datareadtime['hotwaterdemand'], None)
        
    def test_setfield_errors(self):
        with self.assertRaises(ValueError):
            self.func.set_field('frosttemp', 3)
        with self.assertRaises(TypeError):
            self.func.set_field('frosttemp', [3, 3])
        with self.assertRaises(ValueError):
            self.func.set_field('currenttime', [8, 7, 7, 7])
        with self.assertRaises(TypeError):
            self.func.set_field('currenttime', 7)
    
    def test_setfields_1(self):
        self.func.set_fields(['frosttemp'], [7])
        self.assertEqual(self.tester.arguments, [(5, 3, 17, 1, [7])])
        self.assertEqual(self.func.frosttemp, 7)
        
    def test_setfields_2(self):
        setarray = [1, 0, 17, 9, 0, 20, 13, 0, 17, 20, 0, 20]
        self.func.set_fields(['mon_heat'], [setarray])
        self.assertEqual(self.tester.arguments, [(5, 3, 103, 12, setarray)])
        self.assertEqual(self.func.mon_heat, setarray)
        
    def test_setfields_3(self):
        setarray = [[1, 0, 17, 9, 0, 20, 13, 0, 17, 20, 0, 20], [1, 0, 17, 9, 0, 20, 13, 0, 17, 20, 0, 20]]
        self.func.set_fields(['mon_heat','wed_heat'], setarray)
        self.assertEqual(self.tester.arguments, [(5, 3, 103, 12, setarray[0]), (5, 3, 127, 12, setarray[0])])
        self.assertEqual(self.func.mon_heat, setarray[0])
        self.assertEqual(self.func.wed_heat, setarray[1])  

    def test_setfields_4(self):
        indata = [[1, 0, 17, 9, 0, 20, 13, 0, 17, 20, 0, 20], [1, 0, 17, 9, 0, 20, 13, 0, 17, 20, 0, 20]]
        flat_list = [item for sublist in indata for item in sublist]
        self.func.set_fields(['mon_heat', 'tues_heat'], indata)
        self.assertEqual(self.tester.arguments, [(5, 3, 103, 24, flat_list)])
        self.assertEqual(self.func.mon_heat, indata[0])
        self.assertEqual(self.func.tues_heat, indata[1])           
    
if __name__ == '__main__':
    unittest.main()
