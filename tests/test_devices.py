"""Unittests for heatmisercontroller.devices module"""
import unittest
import logging
import time

from heatmisercontroller.fields import HeatmiserFieldSingleReadOnly, HeatmiserFieldDoubleReadOnly
from heatmisercontroller.devices import ThermoStatDay, ThermoStatHotWaterDay
from heatmisercontroller.generaldevices import HeatmiserBroadcastDevice
from heatmisercontroller.hm_constants import HMV3_ID, PROG_MODE_DAY
from heatmisercontroller.exceptions import HeatmiserResponseError, HeatmiserControllerTimeError

from mock_serial import SetupTestClass, MockHeatmiserAdaptor

class ArgumentStore(object):
    """Class used to replace class method allowing arguments to be captured"""
    def __init__(self):
        self.arguments = ()
    
    def store(self, *args):
        """Method used to replace other writing methods"""
        self.arguments = args

class TestBroadcastController(unittest.TestCase):
    """Unittests for reading data functions"""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        setup = SetupTestClass()
        self.adaptor = MockHeatmiserAdaptor(setup)
        #network, address, protocol, short_name, long_name, model, mode
        #self.func = ThermoStat(None, 1, HMV3_ID, 'test', 'test controller', 'prt_hw_model', PROG_MODE_DAY)
        self.settings = {'address':1, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_hw_model', 'expected_prog_mode':PROG_MODE_DAY}
        dev1 = ThermoStatHotWaterDay(self.adaptor, self.settings)
        self.settings2 = {'address':2, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_hw_model', 'expected_prog_mode':PROG_MODE_DAY}
        dev2 = ThermoStatHotWaterDay(self.adaptor, self.settings)
        self.func = HeatmiserBroadcastDevice(self.adaptor, 'Broadcaster', [dev1, dev2])
            
    def test_read_fields(self):
        responses = [[0, 0, 0, 0, 0, 0, 0, 170], [0, 1, 0, 0, 0, 0, 0, 180]]
        self.adaptor.setresponse(responses)
        self.assertEqual([[0, 17], [1, 18]], self.func.read_fields(['tempholdmins', 'airtemp'], 0))
        
class TestReadingData(unittest.TestCase):
    """Unittests for reading data functions"""
    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        #network, address, protocol, short_name, long_name, model, mode
        #self.func = ThermoStat(None, 1, HMV3_ID, 'test', 'test controller', 'prt_hw_model', PROG_MODE_DAY)
        self.settings = {'address':1, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_hw_model', 'expected_prog_mode':PROG_MODE_DAY}
        self.settings2 = {'address':1, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_e_model', 'expected_prog_mode':PROG_MODE_DAY}
        self.func = ThermoStatHotWaterDay(None, self.settings)
            
    def test_procfield(self):
        #unique_address, length, divisor, valid range
        self.func._procfield([1], HeatmiserFieldSingleReadOnly('test', 0, [], None))
        self.func._procfield([1], HeatmiserFieldSingleReadOnly('test', 0, [0, 1], None))
        self.func._procfield([1, 1], HeatmiserFieldDoubleReadOnly('test', 0, [0, 257], None))
        self.func._procfield([4], HeatmiserFieldSingleReadOnly('model', 0, [], None))
        #self.func._procfield([PROG_MODES[PROG_MODE_DAY]], HeatmiserFieldSingleReadOnly('programmode', 0, [], None))
        
    def test_procfield_range(self):
        with self.assertRaises(HeatmiserResponseError):
            self.func._procfield([3], HeatmiserFieldSingleReadOnly('test', 0, [0, 1], None))
            
    def test_procfield_model(self):
        field = HeatmiserFieldSingleReadOnly('model', 0, [], None)
        field.expectedvalue = 4
        with self.assertRaises(HeatmiserResponseError):
            self.func._procfield([3], field)
        
    def test_procpayload(self):
        print "tz %i alt tz %i"%(time.timezone, time.altzone)
        goodmessage = [1, 37, 0, 22, 4, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 38, 1, 9, 12, 28, 1, 1, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0, 220, 0, 0, 0, 3, 14, 49, 36, 7, 0, 19, 9, 30, 10, 17, 0, 19, 21, 30, 10, 7, 0, 19, 21, 30, 10, 24, 0, 5, 24, 0, 5, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 8, 0, 9, 0, 18, 0, 19, 0, 24, 0, 24, 0, 24, 0, 24, 0, 7, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 19, 8, 30, 12, 16, 30, 20, 21, 0, 12, 7, 0, 20, 12, 0, 12, 17, 0, 20, 21, 30, 12, 5, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 20, 12, 0, 12, 17, 0, 20, 21, 30, 12, 7, 0, 12, 24, 0, 12, 24, 0, 12, 24, 0, 12, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0]

        self.func.autocorrectime = False
        basetime = (6 - 2) * 86400 + 53376.0 + YEAR2000
        self.func.lastreadtime = basetime - get_offset(basetime)
        self.func._procpayload(goodmessage)

    def test_procpartpayload(self):
        self.func._procpartpayload([0, 1], 'tempholdmins', 'tempholdmins')
        self.assertEqual(1, self.func.tempholdmins.value)
        self.func._procpartpayload([0, 1, 0, 0, 0, 0, 0, 0], 'tempholdmins', 'airtemp')
        self.assertEqual(1, self.func.tempholdmins.value)
        
    def test_readall(self):
        setup = SetupTestClass()
        adaptor = MockHeatmiserAdaptor(setup)
        self.func = ThermoStatHotWaterDay(adaptor, self.settings)
        #basetime = (6 - 2) * 86400 + 53376.0 + YEAR2000
        #self.func.lastreadtime = basetime - get_offset(basetime)
        lta = self.func.currenttime.localtimearray()
        #, 3, 14, 49, 36,
        responses = [[1, 37, 0, 22, 4, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 38, 1, 9, 12, 28, 1, 1, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0, 220, 0, 0, 0] + lta + [7, 0, 19, 9, 30, 10, 17, 0, 19, 21, 30, 10, 7, 0, 19, 21, 30, 10, 24, 0, 5, 24, 0, 5, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 8, 0, 9, 0, 18, 0, 19, 0, 24, 0, 24, 0, 24, 0, 24, 0, 7, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 19, 8, 30, 12, 16, 30, 20, 21, 0, 12, 7, 0, 20, 12, 0, 12, 17, 0, 20, 21, 30, 12, 5, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 20, 12, 0, 12, 17, 0, 20, 21, 30, 12, 7, 0, 12, 24, 0, 12, 24, 0, 12, 24, 0, 12, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0]]
        adaptor.setresponse(responses)
        self.func.read_all()
        self.assertEqual([(1, 3, 0, 293, True)], adaptor.arguments)
        
    def test_readvariables(self):
        setup = SetupTestClass()
        adaptor = MockHeatmiserAdaptor(setup)
        self.func = ThermoStatHotWaterDay(adaptor, self.settings)
        
        #queue some data to recieve
        responses = [[17, 30, 1, 1, 1, 1, 0, 0], [0, 0, 17, 0, 17, 0, 17, 0, 0, 0, 0]]
        adaptor.setresponse(responses)
        #run command
        self.func.get_variables()
        self.assertEqual([(1, 3, 18, 8, False), (1, 3, 32, 11, False)], adaptor.arguments)
        self.assertEqual(17, self.func.setroomtemp.value)
        self.assertEqual(0, self.func.hotwaterdemand.value)

    def test_read_field(self):
        setup = SetupTestClass()
        adaptor = MockHeatmiserAdaptor(setup)
        self.func = ThermoStatDay(adaptor, self.settings2)
        responses = [[0, 170], [0, 180]]
        adaptor.setresponse(responses)
        self.assertEqual(17, self.func.read_field('airtemp', 1))
        self.assertEqual(17, self.func.read_field('airtemp', -1)) #only check presence
        self.func.airtemp.lastreadtime = 0 #force reread
        self.assertEqual(18, self.func.read_field('airtemp', None))
        
    def test_read_fields(self):
        setup = SetupTestClass()
        adaptor = MockHeatmiserAdaptor(setup)
        self.func = ThermoStatDay(adaptor, self.settings2)
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
        self.func = ThermoStatHotWaterDay(None, self.settings)
    
    @staticmethod
    def extract_addresses(blocklist):
        return [[block[0].address, block[1].address, block[2]] for block in blocklist]
    
    def test_getfieldblocks(self):
        self.assertEqual([[34, 42, 9]], self.extract_addresses(self.func._get_field_blocks_from_id_range(self.func._fieldnametonum['remoteairtemp'], self.func._fieldnametonum['hotwaterdemand'])))
        self.assertEqual([[42, 43, 5]], self.extract_addresses(self.func._get_field_blocks_from_id_range(self.func._fieldnametonum['hotwaterdemand'], self.func._fieldnametonum['currenttime'])))
        self.func = ThermoStatDay(None, self.settings)
        self.assertEqual([[0, 24, 26], [32, 41, 10], [43, 43, 4]], self.extract_addresses(self.func._get_field_blocks_from_id_range(self.func._fieldnametonum['DCBlen'], self.func._fieldnametonum['currenttime'])))
        self.assertEqual([[0, 24, 26], [32, 41, 10], [43, 59, 28], [103, 175, 84]], self.extract_addresses(self.func._get_field_blocks_from_id_range(self.func._fieldnametonum['DCBlen'], self.func._fieldnametonum['sun_heat'])))
        
    def test_checkblock4(self):
        #print 'DCBlen','sun_water'
        #print self.func._getFieldBlocks('DCBlen','sun_water')
        #from timeit import default_timer as timer
        #start = timer()
        for _ in range(1):
            self.func._get_field_blocks_from_id_range(self.func._fieldnametonum['DCBlen'], self.func._fieldnametonum['sun_water'])
        #print (timer()-start)/1000
        
    def test_configure_fields(self):
        self.func._configure_fields()
        expected = [[0, 0], [25, 30], [26, 32], [31, 41], [32, 53], [40, 157], [48, 277]]
        for u, d in expected:
            self.assertEqual(d, self.func.fields[u].dcbaddress)
            
    def test_print_target(self):
        self.assertEqual("controller off without frost protection", self.func.target_texts[self.func.TEMP_STATE_OFF](self.func))
        self.func.holidayhours = 12
        self.assertEqual("controller on holiday for 12 hours", self.func.target_texts[self.func.TEMP_STATE_HOLIDAY](self.func))

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
        self.func = ThermoStatHotWaterDay(None, self.settings)
        
    def test_comparecontrollertime_none(self):
        with self.assertRaises(HeatmiserResponseError):
            self.func.currenttime.comparecontrollertime()
            
    def test_comparecontrollertime_bad(self):
        basetime = (1 + 1) * 86400 + 9 * 3600 + 33 * 60 + 0 + YEAR2000
        self.func.currenttime.lastreadtime = basetime - get_offset(basetime) #has been read
        self.func.data['currenttime'] = self.func.currenttime.value = [1, 0, 0, 0]
        with self.assertRaises(HeatmiserControllerTimeError):
            self.func.currenttime.comparecontrollertime()
        
    def test_comparecontrollertime_1(self):
        basetime = (4 + 1) * 86400 + 9 * 3600 + 33 * 60 + 5 + YEAR2000
        self.func.currenttime.lastreadtime = basetime - get_offset(basetime) #has been read
        self.func.data['currenttime'] = self.func.currenttime.value = [4, 9, 33, 0]
        #print "s ", self.func._localtimearray(self.func.datareadtime['currenttime']), self.func.data['currenttime'], self.func.datareadtime['currenttime'], time.localtime(self.func.datareadtime['currenttime']).tm_hour, time.localtime(self.func.datareadtime['currenttime']), "e"
        self.func.currenttime.comparecontrollertime()
        self.assertEqual(5, self.func.currenttime.timeerr)
        
    def test_comparecontrollertime_2(self):
        #self.func.datareadtime['currenttime'] = ( 7 + 3) * 86400 + 23 * 3600 + 59 * 60 + 55 - self.utc_offset #has been read
        basetime = (7 + 1) * 86400 + 23 * 3600 + 59 * 60 + 55 + YEAR2000
        self.func.currenttime.lastreadtime = basetime - get_offset(basetime) #has been read
        self.func.data['currenttime'] = self.func.currenttime.value = [1, 0, 0, 0]
        self.func.currenttime.comparecontrollertime()
        self.assertEqual(5, self.func.currenttime.timeerr)

    def test_localtimearray(self):
        hour = time.localtime(1528350527).tm_hour
        self.assertEqual([4, hour, 48, 47], self.func.currenttime.localtimearray(1528350527))
        self.assertEqual([7, hour, 48, 47], self.func.currenttime.localtimearray(1528350527-86400*4))

class TestSettingData(unittest.TestCase):
    """Unittests for setting data functions"""
    def setUp(self):
        logging.basicConfig(level=logging.ERROR)
        self.settings = {'address':5, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_e_model', 'expected_prog_mode':PROG_MODE_DAY}
        setup = SetupTestClass()
        self.tester = MockHeatmiserAdaptor(setup)
        #self.tester.write_to_device = self.tester.store
        self.func = ThermoStatDay(self.tester, self.settings)
        
    def test_setfield_1(self):
        #checks the arguments sent to write_to_device
        #fieldname, payload
        self.func.set_field('frosttemp', 7)
        self.assertEqual(self.tester.arguments, [(5, 3, 17, 1, [7])])
        self.assertEqual(self.func.frosttemp.value, 7)
        
    def test_setfield_2(self):
        self.func.autocorrectime = False
        #self.func.lastreadtime = 7 * 86400 + 7 *3600 + 7 * 60 - 3600
        self.func.lastreadtime = time.time()
        loctime = self.func.currenttime.localtimearray(self.func.lastreadtime)
        self.func.set_field('currenttime', loctime)
        self.assertEqual(self.tester.arguments, [(5, 3, 43, 4, loctime)])

    def test_setfield_notvalid(self):
        with self.assertRaises(KeyError):
            self.func.set_field('hotwaterdemand', 0)
        
    def test_setfield_3(self):
        """Check hotwaterdemand mapping"""
        settings2 = {'address':1, 'protocol':HMV3_ID, 'long_name':'test controller', 'expected_model':'prt_hw_model', 'expected_prog_mode':PROG_MODE_DAY}
        #self.func._update_settings(settings2, None)
        self.func = ThermoStatHotWaterDay(self.tester, settings2)
        #make sure read time is set and check value
        self.func.set_field('hotwaterdemand', self.func.hotwaterdemand.writevalues['OVER_OFF'])
        self.assertNotEqual(getattr(self.func, 'hotwaterdemand').lastreadtime, None)
        self.assertEqual(self.func.data['hotwaterdemand'], self.func.hotwaterdemand.readvalues['OFF'])
        self.func._adaptor.reset()
        #check releasing works
        self.func.set_field('hotwaterdemand', self.func.hotwaterdemand.writevalues['PROG'])
        self.assertEqual(self.tester.arguments, [(1, 3, 42, 1, [self.func.hotwaterdemand.writevalues['PROG']])])
        self.assertEqual(self.func.hotwaterdemand.value, None)
        self.assertEqual(self.func.hotwaterdemand.lastreadtime, None)
        
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
        self.assertEqual(self.func.frosttemp.value, 7)
        
    def test_setfields_2(self):
        setarray = [1, 0, 17, 9, 0, 20, 13, 0, 17, 20, 0, 20]
        self.func.set_fields(['mon_heat'], [setarray])
        self.assertEqual(self.tester.arguments, [(5, 3, 103, 12, setarray)])
        self.assertEqual(self.func.mon_heat.value, setarray)
        
    def test_setfields_3(self):
        setarray = [[1, 0, 17, 9, 0, 20, 13, 0, 17, 20, 0, 20], [1, 0, 17, 9, 0, 20, 13, 0, 17, 20, 0, 20]]
        self.func.set_fields(['mon_heat', 'wed_heat'], setarray)
        self.assertEqual(self.tester.arguments, [(5, 3, 103, 12, setarray[0]), (5, 3, 127, 12, setarray[0])])
        self.assertEqual(self.func.mon_heat.value, setarray[0])
        self.assertEqual(self.func.wed_heat.value, setarray[1])  

    def test_setfields_4(self):
        indata = [[1, 0, 17, 9, 0, 20, 13, 0, 17, 20, 0, 20], [1, 0, 18, 9, 0, 21, 13, 0, 18, 20, 0, 21]]
        flat_list = [item for sublist in indata for item in sublist]
        self.func.set_fields(['mon_heat', 'tues_heat'], indata)
        self.assertEqual(self.tester.arguments, [(5, 3, 103, 24, flat_list)])
        self.assertEqual(self.func.mon_heat.value, indata[0])
        self.assertEqual(self.func.tues_heat.value, indata[1])           
    
if __name__ == '__main__':
    unittest.main()
