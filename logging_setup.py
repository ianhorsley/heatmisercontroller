#
# Ian Horsley 2018

#
# function to setup logging to screen and files

# Assume Python 2.7.x
#
import logging
import os

from logging.handlers import RotatingFileHandler

def initialize_logger(output_dir, screenlevel, debugLog = None):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
     
    # create console handler and set level to info
    handler = logging.StreamHandler()
    handler.setLevel(screenlevel)
    formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # create error file handler and set level to error
    handler = logging.FileHandler(os.path.join(output_dir, "error.log"),"w", encoding=None, delay="true")
    handler.setLevel(logging.WARN)
    formatter = logging.Formatter("%(asctime)-15s %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    #a is append, w is write
    if debugLog != None:
      #create debug file handler and set level to debug
      handler = RotatingFileHandler(os.path.join(output_dir, "all.log"), mode='a', maxBytes=5*1024*1024, 
                                   backupCount=2, encoding=None, delay=0)
      #handler = logging.FileHandler(os.path.join(output_dir, "all.log"),"w", encoding=None, delay="true")
      handler.setLevel(logging.DEBUG)
      formatter = logging.Formatter("%(asctime)-15s %(levelname)s - %(message)s")
      handler.setFormatter(formatter)
      logger.addHandler(handler)