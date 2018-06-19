import unittest
import logging
import time

from heatmisercontroller.devices import hmController
from heatmisercontroller.hm_constants import HMV3_ID, PROG_MODES, PROG_MODE_DAY, DCB_INVALID
from heatmisercontroller.exceptions import hmResponseError, hmControllerTimeError

class argstore(object):
    def store(self, *args):
        self.args = args

class test_reading_data(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.ERROR)
    #network, address, protocol, short_name, long_name, model, mode
    #self.func = hmController(None, 1, HMV3_ID, 'test', 'test controller', 'prt_hw_model', PROG_MODE_DAY)
    self.settings = {'address':1,'protocol':HMV3_ID,'long_name':'test controller','expected_model':'prt_hw_model','expected_prog_mode':PROG_MODE_DAY}
      
  def test_procfield(self):
    #unique_address,length,divisor, valid range
    self.func = hmController(None, self.settings)
    self.func._procfield([1],['test',0, 1, 1, []])
    self.func._procfield([1],['test',0, 1, 1, [0, 1]])
    self.func._procfield([1, 1],['test',0, 2, 1, [0, 257]])
    self.func._procfield([4],['model',0, 1, 1, []])
    self.func._procfield([PROG_MODES[PROG_MODE_DAY]],['programmode',0, 1, 1, []])
    
  def test_procfield_range(self):
    self.func = hmController(None, self.settings)
    with self.assertRaises(hmResponseError):
      self.func._procfield([3],['test',0, 1, 1, [0, 1]])
      
  def test_procfield_model(self):
    self.func = hmController(None, self.settings)
    with self.assertRaises(hmResponseError):
      self.func._procfield([3],['model',0, 1, 1, []])
    
  def test_procpayload(self):
    import time
    print -time.timezone
    goodmessage = [1, 37, 0, 22, 4, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1, 38, 1, 9, 12, 28, 1, 1, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 0, 220, 0, 0, 0, 3, 14, 49, 36, 7, 0, 19, 9, 30, 10, 17, 0, 19, 21, 30, 10, 7, 0, 19, 21, 30, 10, 24, 0, 5, 24, 0, 5, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 8, 0, 9, 0, 18, 0, 19, 0, 24, 0, 24, 0, 24, 0, 24, 0, 7, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 19, 8, 30, 12, 16, 30, 20, 21, 0, 12, 7, 0, 20, 12, 0, 12, 17, 0, 20, 21, 30, 12, 5, 0, 20, 21, 30, 12, 24, 0, 12, 24, 0, 12, 7, 0, 20, 12, 0, 12, 17, 0, 20, 21, 30, 12, 7, 0, 12, 24, 0, 12, 24, 0, 12, 24, 0, 12, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 17, 30, 18, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0]

    self.func = hmController(None, self.settings)
    self.func.autocorrectime = False
    self.func.lastreadtime = 6 * 86400 + 53376.0 - 3600
    self.func._procpayload(goodmessage)

  def test_procpartpayload(self):
    self.func = hmController(None, self.settings)
    self.func._procpartpayload([0, 1],'tempholdmins','tempholdmins')
    self.assertEqual(1, self.func.tempholdmins)
    self.func._procpartpayload([0, 1, 0, 0, 0, 0, 0, 0],'tempholdmins','airtemp')
    self.assertEqual(1, self.func.tempholdmins)
    
  def test_readall(self):
    pass

class test_other_functions(unittest.TestCase):
  def test_getDCBaddress(self):
    self.settings = {'address':1,'protocol':HMV3_ID,'long_name':'test controller','expected_model':'prt_e_model','expected_prog_mode':PROG_MODE_DAY}
    self.func = hmController(None, self.settings)
    self.assertEqual(0, self.func._getDCBaddress(0))
    self.assertEqual(24, self.func._getDCBaddress(24))
    self.assertEqual(DCB_INVALID, self.func._getDCBaddress(26))
    
  def test_getFieldBlocks(self):
    self.settings = {'address':1,'protocol':HMV3_ID,'long_name':'test controller','expected_model':'prt_e_model','expected_prog_mode':PROG_MODE_DAY}
    self.func = hmController(None, self.settings)
    self.assertEqual([[34, 41, 8]], self.func._getFieldBlocks('remoteairtemp','hotwaterdemand'))
    self.assertEqual([[43, 43, 4]], self.func._getFieldBlocks('hotwaterdemand','currenttime'))
    self.assertEqual([[0, 24, 26], [32, 41, 10], [43, 43, 4]], self.func._getFieldBlocks('DCBlen','currenttime'))
    self.assertEqual([[0, 24, 26], [32, 41, 10], [43, 59, 28], [103, 175, 84]], self.func._getFieldBlocks('DCBlen','sun_water'))
    
  def test_checkblock4(self):
    self.settings = {'address':1,'protocol':HMV3_ID,'long_name':'test controller','expected_model':'prt_e_model','expected_prog_mode':PROG_MODE_DAY}
    self.func = hmController(None, self.settings)
    #print 'DCBlen','sun_water'
    #print self.func._getFieldBlocks('DCBlen','sun_water')
    from timeit import default_timer as timer
    start = timer()
    for i in range(1):self.func._getFieldBlocks('DCBlen','sun_water')
    #print (timer()-start)/1000
    
  def test_buildDCBtables(self):
    self.settings = {'address':1,'protocol':HMV3_ID,'long_name':'test controller','expected_model':'prt_e_model','expected_prog_mode':PROG_MODE_DAY}
    self.func = hmController(None, self.settings)    
    self.func._buildDCBtables()
    expected = [[0,0],[25,25],[26,None],[31,None],[32,26],[186,147],[187,None],[298,None]]
    for u,d in expected:
        self.assertEqual(d,self.func._uniquetodcb[u])
  
class test_time_functions(unittest.TestCase):
  def setUp(self):
    #gettimezone offset
    is_dst = time.daylight and time.localtime().tm_isdst > 0
    self.utc_offset = - (time.altzone if is_dst else time.timezone)
    self.settings = {'address':1,'protocol':HMV3_ID,'long_name':'test controller','expected_model':'prt_hw_model','expected_prog_mode':PROG_MODE_DAY}
    self.func = hmController(None, self.settings)
    
  def test_comparecontrollertime_none(self):
    with self.assertRaises(hmResponseError):
      self.func._comparecontrollertime()
      
  def test_comparecontrollertime_bad(self):
    self.func.datareadtime['currenttime'] = ( 1 + 3) * 86400 + 9 * 3600 + 33 * 60 + 0 - self.utc_offset #has been read 
    self.func.data['currenttime'] = self.func.currenttime = [1, 0, 0, 0]
    with self.assertRaises(hmControllerTimeError):
      self.func._comparecontrollertime()
    
  def test_comparecontrollertime_1(self):
    self.func.datareadtime['currenttime'] = ( 4 + 3) * 86400 + 9 * 3600 + 33 * 60 + 5 - self.utc_offset #has been read 
    self.func.data['currenttime'] = self.func.currenttime = [4, 9, 33, 0]
    self.func._comparecontrollertime()
    self.assertEqual(5, self.func.timeerr)
    
  def test_comparecontrollertime_2(self):
    self.func.datareadtime['currenttime'] = ( 7 + 3) * 86400 + 23 * 3600 + 59 * 60 + 55 - self.utc_offset #has been read 
    self.func.data['currenttime'] = self.func.currenttime = [1, 0, 0, 0]
    self.func._comparecontrollertime()
    self.assertEqual(5, self.func.timeerr)

  def test_localtimearray(self):
    self.assertEqual([4, 6, 48, 47], self.func._localtimearray(1528350527))
    self.assertEqual([7, 6, 48, 47], self.func._localtimearray(1528350527-86400*4))

class test_protocol(unittest.TestCase):
  def setUp(self):
    logging.basicConfig(level=logging.ERROR)
    self.settings = {'address':5,'protocol':HMV3_ID,'long_name':'test controller','expected_model':'prt_e_model','expected_prog_mode':PROG_MODE_DAY}
    self.tester = argstore()
    self.tester.hmWriteToController = self.tester.store
    self.func = hmController(self.tester, self.settings)
    
  def test_setfield_1(self):
    #checks the arguements sent to hmWriteToController
    #fieldname, payload
    self.func.setField('frosttemp', 7 )
    self.assertEqual(self.tester.args,(5, 3, 17, 1, [7]))
    
  def test_setfield_2(self):
    self.func.autocorrectime = False
    #self.func.lastreadtime = 7 * 86400 + 7 *3600 + 7 * 60 - 3600
    self.func.lastreadtime = time.time()
    loctime = self.func._localtimearray(self.func.lastreadtime)
    self.func.setField('currenttime', loctime )
    self.assertEqual(self.tester.args,(5, 3, 43, 4, loctime))
    
  def test_setfield_errors(self):
    with self.assertRaises(ValueError):
        self.func.setField('frosttemp', 3 )
    with self.assertRaises(TypeError):
        self.func.setField('frosttemp', [3,3] )
    with self.assertRaises(ValueError):
        self.func.setField('currenttime', [8,7,7,7] )
    with self.assertRaises(TypeError):
        self.func.setField('currenttime', 7  )        
  
if __name__ == '__main__':
    unittest.main()

