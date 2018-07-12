"""Decorators meethods to support broadcast controller running functions on multiple devices"""
import logging
import serial

from .exceptions import HeatmiserResponseError, HeatmiserControllerTimeError

class ListWrapperClass(object):
    """Class to provide mutable list as decorator argument"""
    def __init__(self):
        self._storedlist = None

    @property
    def list(self):
        """I'm the 'x' property."""
        return self._storedlist

    @list.setter
    def list(self, value):
        self._storedlist = value

    @list.deleter
    def list(self):
        self._storedlist = None

def run_function_on_all(liststore):
    """Decorator to allow a class method to be run on all objects in a list"""
    def wraps(func):
        """Decorator internal"""
        def inner(self, *args, **kwargs):
            """Decorator internal"""
            if liststore.list is None:
                raise ValueError("liststore contains no list")
            logging.info("All running %s for %i controllers"%(func.__name__, len(liststore.list)))
            func(self, *args, **kwargs)
            results = [None] * len(liststore.list)
            lasterror = None
            for index, obj in enumerate(liststore.list):
                try:
                    results[index] = getattr(obj, func.__name__)(*args, **kwargs)
                except (HeatmiserResponseError, serial.SerialException, HeatmiserControllerTimeError) as err:
                    logging.warn("C%i %s failed due to %s"%(obj.address, func.__name__, str(lasterror)))
                    lasterror = err
                    continue

            if all(result is None for result in results):
                raise HeatmiserResponseError("All failed, last error was %s"%(str(lasterror)))

            return results

        return inner
    return wraps
