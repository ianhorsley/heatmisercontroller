"""Class to initialise loggers to screen and files"""

import logging
import os

from logging.handlers import RotatingFileHandler

def initialize_logger(output_dir, screenlevel, debug_log=None):
    """Class to initialise loggers to screen and files"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers: #only create if handlers haven't already been created.
    
        # create console handler and set level to info
        screenhandler = logging.StreamHandler()
        screenhandler.setLevel(screenlevel)
        screenformatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        screenhandler.setFormatter(screenformatter)
        logger.addHandler(screenhandler)
    
        # create error file handler and set level to error
        filehandler = logging.FileHandler(os.path.join(output_dir, "error.log"), "w", encoding=None, delay="true")
        filehandler.setLevel(logging.WARN)
        fileformatter = logging.Formatter("%(asctime)-15s %(levelname)s - %(message)s")
        filehandler.setFormatter(fileformatter)
        logger.addHandler(filehandler)
        
    #a is append, w is write
    # this one ok is to rehandle because it is an append. Also can be added by a second call to initialize logger
    if debug_log != None:
        #create debug file handler and set level to debug
        allhandler = RotatingFileHandler(os.path.join(output_dir, "all.log"), mode='a', maxBytes=5*1024*1024,
                                     backupCount=2, encoding=None, delay=0)
        #handler = logging.FileHandler(os.path.join(output_dir, "all.log"),"w", encoding=None, delay="true")
        allhandler.setLevel(logging.DEBUG)
        allformatter = logging.Formatter("%(asctime)-15s %(levelname)s - %(message)s")
        allhandler.setFormatter(allformatter)
        logger.addHandler(allhandler)
