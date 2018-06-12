"""


"""

import time
import logging
import os
from configobj import ConfigObj
from validate import Validator

from .exceptions import HeatmiserControllerSetupInitError

"""class HeatmiserControllerSetup

User interface to setup the contoller.

The settings attribute stores the settings of the hub. It is a
dictionary with the following keys:

        'controller': a dictionary containing general settings
        'serial': a dictionary containing the serial port settings
        'devices': a dictionary containing the configuration of each remote device


        The hub settings are:
        'loglevel': the logging level
        
        ###interfacers and reporters are dictionaries with the following keys:
        ###'Type': class name
        ###'init_settings': dictionary with initialization settings
        ###'runtimesettings': dictionary with runtime settings
        ###Initialization and runtime settings depend on the interfacer and
        ###reporter type.

The run() method is supposed to be run regularly by the instantiator, to
perform regular communication tasks.

The check_settings() method is run regularly as well. It checks the settings 
and returns True is settings were changed.

This almost empty class is meant to be inherited by subclasses specific to
each setup.

"""


class HeatmiserControllerSetup(object):

    def __init__(self):
        
        # Initialize logger
        self._log = logging.getLogger("HeatmiserController")
        
        # Initialize settings
        self.settings = None

    def run(self):
        """Run in background. 
        
        To be implemented in child class.

        """
        pass

    def check_settings(self):
        """Check settings
        
        Update attribute settings and return True if modified.
        
        To be implemented in child class.
        
        """

class HeatmiserControllerFileSetup(HeatmiserControllerSetup):

    def __init__(self, filename):
        
        # Initialization
        super(HeatmiserControllerFileSetup, self).__init__()

        # Initialize update timestamp
        self._settings_update_timestamp = 0
        self._retry_time_interval = 5

        # create a timeout message if time out is set (>0)
        if self._retry_time_interval > 0:
            self.retry_msg = " Retry in " + str(self._retry_time_interval) + " seconds"
        else:
            self.retry_msg = ""

        self._module_path = os.path.abspath(os.path.dirname(__file__))
        specpath = os.path.join(self._module_path, "hmcontroller.spec")
            
        # Initialize attribute settings as a ConfigObj instance
        logging.debug("Loading %s and checking against %s"%(filename, specpath))
        try:
            self.settings = ConfigObj(filename, file_error=True, configspec=specpath)
            validator = Validator()
            self.settings.validate(validator, copy=True)
            # Check the settings file sections
            self.settings['controller']
            self.settings['serial']
            self.settings['devices']
        except IOError as e:
            raise HeatmiserControllerSetupInitError(e)
        except SyntaxError as e:
            raise HeatmiserControllerSetupInitError(
                'Error parsing config file \"%s\": ' % filename + str(e))
        except KeyError as e:
            raise HeatmiserControllerSetupInitError(
                'Configuration file error - section: ' + str(e))

    def check_settings(self):
        """Check settings
        
        Update attribute settings and return True if modified.
        
        """
        
        # Check settings only once per second
        now = time.time()
        if now - self._settings_update_timestamp < 0:
            return
        # Update timestamp
        self._settings_update_timestamp = now
        
        # Backup settings
        settings = dict(self.settings)
        
        # Get settings from file
        try:
            self.settings.reload()
        except IOError as e:
            self._log.warning('Could not get settings: ' + str(e) + self.retry_msg)
            self._settings_update_timestamp = now + self._retry_time_interval
            return
        except SyntaxError as e:
            self._log.warning('Could not get settings: ' + 
                              'Error parsing config file: ' + str(e) + self.retry_msg)
            self._settings_update_timestamp = now + self._retry_time_interval
            return
        except Exception:
            import traceback
            self._log.warning("Couldn't get settings, Exception: " +
                              traceback.format_exc() + self.retry_msg)
            self._settings_update_timestamp = now + self._retry_time_interval
            return
        
        if self.settings != settings:
            # Check the settings file sections
            try:
                self.settings['hub']
                self.settings['interfacers']
                self.settings['reporters']
            except KeyError as e:
                self._log.warning("Configuration file missing section: " + str(e))
            else:
                 return True



