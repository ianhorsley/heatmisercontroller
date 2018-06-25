"""User interface to setup the contoller."""

import logging
import os
from configobj import ConfigObj
from validate import Validator

from .exceptions import HeatmiserControllerSetupInitError

# The settings attribute stores the settings of the hub. It is a
# dictionary with the following keys:

        # 'controller': a dictionary containing general settings
        # 'serial': a dictionary containing the serial port settings
        # 'devices': a dictionary containing the configuration of each remote device
        # 'setup':

        # The controller settings are:
        # 'loglevel': the logging level

        # ###interfacers and reporters are dictionaries with the following keys:
        # ###'Type': class name
        # ###'init_settings': dictionary with initialization settings
        # ###'runtimesettings': dictionary with runtime settings
        # ###Initialization and runtime settings depend on the interfacer and
        # ###reporter type.

# The run() method is supposed to be run regularly by the instantiator, to
# perform regular communication tasks.

# The check_settings() method is run regularly as well. It checks the settings
# and returns True is settings were changed.

# This almost empty class is meant to be inherited by subclasses specific to
# each setup."""

class HeatmiserControllerSetup(object):
    """Inherited base class"""
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
    """Handles importing confiugration from file"""
    def __init__(self, filename):
        
        # Initialization
        super(HeatmiserControllerFileSetup, self).__init__()

        self._module_path = os.path.abspath(os.path.dirname(__file__))
        specpath = os.path.join(self._module_path, "hmcontroller.spec")
        
        # List of expected sections
        self._sections = ['controller', 'serial', 'devices', 'setup']
            
        # Initialize attribute settings as a ConfigObj instance
        logging.debug("Loading %s and checking against %s"%(filename, specpath))
        try:
            self.settings = ConfigObj(filename, file_error=True, configspec=specpath)
            self._validator = Validator()
        except IOError as err:
            raise HeatmiserControllerSetupInitError(err)
        except SyntaxError as err:
            raise HeatmiserControllerSetupInitError(
                'Error parsing config file \"%s\": ' % filename + str(err))
        except KeyError as err:
            raise HeatmiserControllerSetupInitError(
                'Configuration file error - section missing: ' + str(err))
        
        #check settings and add any default values
        self._check_settings()
        
        # Initialize update timestamps
        self._settings_update_timestamp = 0
        
        # Load use configured variables
        for name, value in self.settings['setup'].iteritems():
            setattr(self, '_c_'+name, value)

        # create a timeout message if time out is set (>0)
        self.retry_msg = " Retry in " + str(self._c_retry_time_interval) + " seconds" if self._c_retry_time_interval <= 0 else ""

    # def reload_settings(self):
        # """Reload and check settings

        # Update attribute settings and return True if modified. Return False if failed to load new settings. Return None if nothing new or not checked

        # """
        
        # # Check settings only once per second
        # now = time.time()
        # if now - self._settings_update_timestamp < 0:
            # return
        # # Update timestamp
        # self._settings_update_timestamp = now + self._c_check_time_interval
        
        # # Backup settings
        # settings = dict(self.settings)
        
        # # Get settings from file
        # try:
            # self.settings.reload()
        # except IOError as err:
            # self._log.warning('Could not get settings: ' + str(err) + self.retry_msg)
            # self._settings_update_timestamp = now + self._c_retry_time_interval
            # return
        # except SyntaxError as err:
            # self._log.warning('Could not get settings: ' +
                              # 'Error parsing config file: ' + str(err) + self.retry_msg)
            # self._settings_update_timestamp = now + self._c_retry_time_interval
            # return
        # except Exception:
            # import traceback
            # self._log.warning("Couldn't get settings, Exception: " +
                              # traceback.format_exc() + self.retry_msg)
            # self._settings_update_timestamp = now + self._c_retry_time_interval
            # return

        # if self.settings != settings:
            # try:
                # self._check_settings()
            # except (ValueError, KeyError):
                # self.settings = settings
                # return False
            # return True
            
    def _check_settings(self):
        """Function validates configuration against specification."""
        try:
            # Validate the configuration file and copy any missing defaults
            returnval = self.settings.validate(self._validator, preserve_errors=True, copy=True)
            if not returnval is True:
                raise ValueError("failed validation of config file %s"%str(returnval))

            # Check the settings file sections exist
            for name in self._sections:
                if not name in self.settings:
                    raise KeyError("Section %s not defined"%name)
        except (ValueError, KeyError) as err:
            logging.warning("Configuration parse failed : " + str(err))
            raise


            



