"""Class to initialise loggers to screen and files"""

import logging
import os

from logging.handlers import RotatingFileHandler

def _add_streamhandler(screenlevel, logger):
    """create console handler and set level to requested level"""
    screenhandler = logging.StreamHandler()
    screenhandler.setLevel(screenlevel)
    screenformatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    screenhandler.setFormatter(screenformatter)
    logger.addHandler(screenhandler)
    logging.debug('Added stream handler')

def _update_streamhandler(screenlevel, screenhandler):
    screenhandler.setLevel(screenlevel)
    screenformatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    screenhandler.setFormatter(screenformatter)
    
def _add_filehandler(output_dir, logger):
    """create error file handler and set level to warn"""
    filehandler = logging.FileHandler(os.path.join(output_dir, "error.log"), "w", encoding=None, delay="true")
    filehandler.setLevel(logging.WARN)
    fileformatter = logging.Formatter("%(asctime)-15s %(levelname)s - %(message)s")
    filehandler.setFormatter(fileformatter)
    logger.addHandler(filehandler)
    logging.debug('Added file handler')

def _add_allfilehandler(output_dir, logger):
    """create debug file handler and set level to debug"""
    #a is append, w is write
    # this one ok is to rehandle because it is an append. Also can be added by a second call to initialize logger
    
    allhandler = RotatingFileHandler(os.path.join(output_dir, "all.log"), mode='a', maxBytes=5*1024*1024,
                                 backupCount=2, encoding=None, delay=0)
    #handler = logging.FileHandler(os.path.join(output_dir, "all.log"),"w", encoding=None, delay="true")
    allhandler.setLevel(logging.DEBUG)
    allformatter = logging.Formatter("%(asctime)-15s %(levelname)s - %(message)s")
    allhandler.setFormatter(allformatter)
    logger.addHandler(allhandler)
    logging.debug('Added all handler')
    
def initialize_logger(output_dir, screenlevel, debug_log=None):
    """Class to initialise loggers to screen and files"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers: #only create if handlers haven't already been created.
        if debug_log != None:
            _add_allfilehandler(output_dir, logger)
        _add_streamhandler(screenlevel, logger)
        _add_filehandler(output_dir, logger)
    else:
        #check for rotating filehandler
        if debug_log != None:
            for handler in logger.handlers:
                if type(handler) is logging.handlers.RotatingFileHandler:
                    break
            else:
                _add_allfilehandler(output_dir, logger)
        #check for stream and update if needed
        for handler in logger.handlers:
            if type(handler) is logging.StreamHandler:
                _update_streamhandler(screenlevel, handler)
                break
        else:
            _add_streamhandler(screenlevel, logger)
        #check for filehandler
        for handler in logger.handlers:
            if type(handler) is logging.FileHandler:
                break
        else:
            _add_filehandler(output_dir, logger)
        

