"""Unittests for heatmisercontroller.network module"""
import unittest
import logging
import os

from heatmisercontroller.logging_setup import initialize_logger

class TestLogging(unittest.TestCase):
    """Unit tests for logging."""
    def setUp(self):
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        self.errorlogfile = "error.log"
        self.alllogfile = "all.log"
        self.assertFalse(os.path.isfile(self.errorlogfile))
        self.assertFalse(os.path.isfile(self.alllogfile))
        print "test logging setup"

    def tearDown(self):
        print "test logging teardown"
        if os.path.isfile(self.errorlogfile):
            os.remove(self.errorlogfile)
        if os.path.isfile(self.alllogfile):
            os.remove(self.alllogfile)
        
    #@staticmethod
    def test_logging(self):
        initialize_logger('', logging.ERROR)
        
        logging.debug('Not shown')
        logging.info('Shown')
        logging.warn('Shown')

        self.assertTrue(os.path.isfile(self.errorlogfile))
        self.assertFalse(os.path.isfile(self.alllogfile))
        self.assertEqual(len(open(self.errorlogfile).readlines(  )),1)
        
        with open(self.errorlogfile) as fp:
            line = fp.readline().strip()

        self.assertTrue(line.endswith('WARNING - Shown'))
        
    def test_logging_all(self):
        initialize_logger('', logging.INFO, True)
        logging.debug('Not shown')
        logging.info('Shown')
        logging.warn('Shown')
        
        self.assertTrue(os.path.isfile(self.errorlogfile))
        self.assertTrue(os.path.isfile(self.alllogfile))
        self.assertEqual(len(open(self.alllogfile).readlines(  )),3)

if __name__ == '__main__':
    unittest.main()
