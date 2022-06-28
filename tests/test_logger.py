"""Unittests for heatmisercontroller.network module"""
import unittest
import logging
import os

from heatmisercontroller.logging_setup import initialize_logger, initialize_logger_full

class TestLogging(unittest.TestCase):
    """Unit tests for logging."""
    def setUp(self):
        self.logger = logging.getLogger()
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            handler.close()
        self.errorlogfile = "error.log"
        self.alllogfile = "all.log"
        self.assertFalse(os.path.isfile(self.errorlogfile))
        self.assertFalse(os.path.isfile(self.alllogfile))
        print("test logging setup")

    def tearDown(self):
        print("test logging teardown")
        if os.path.isfile(self.errorlogfile):
            os.remove(self.errorlogfile)
        if os.path.isfile(self.alllogfile):
            os.remove(self.alllogfile)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            handler.close()

    def test_logging(self):
        initialize_logger('', logging.ERROR)
        
        logging.debug('Not shown')
        logging.info('Shown')
        logging.warning('Shown')

        self.assertTrue(os.path.isfile(self.errorlogfile))
        self.assertFalse(os.path.isfile(self.alllogfile))
        with open(self.errorlogfile) as fpointer:
            self.assertEqual(len(fpointer.readlines()), 1)
        
        with open(self.errorlogfile) as fpointer:
            line = fpointer.readline().strip()
        
        self.assertTrue(line.endswith('WARNING - Shown'))
        
    def test_logging_all(self):
        initialize_logger_full('', logging.INFO)
        logging.debug('Not shown')
        logging.info('Shown')
        logging.warning('Shown')
        
        self.assertTrue(os.path.isfile(self.errorlogfile))
        self.assertTrue(os.path.isfile(self.alllogfile))
        self.assertEqual(len(open(self.alllogfile).readlines()), 4)

    def test_logging_double(self):
        initialize_logger('', logging.DEBUG)
        logging.warning('Shown')
        initialize_logger_full('', logging.DEBUG)
        
        logging.debug('Not shown')
        logging.info('Shown')
        logging.warning('Shown')

        self.assertTrue(os.path.isfile(self.errorlogfile))
        self.assertTrue(os.path.isfile(self.alllogfile))
        self.assertEqual(len(open(self.errorlogfile).readlines()), 2)
        self.assertEqual(len(open(self.alllogfile).readlines()), 4) #last three plus one from creating rotating logger
        
        with open(self.errorlogfile) as fpointer:
            line = fpointer.readline().strip()
        
        self.assertTrue(line.endswith('WARNING - Shown'))        
        
if __name__ == '__main__':
    unittest.main()
