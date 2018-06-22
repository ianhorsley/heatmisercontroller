
from .exceptions import hmResponseError


#class to provide list to decorator
class listclass(object):
    def __init__(self):
        self._x = None

    @property
    def list(self):
        """I'm the 'x' property."""
        return self._x

    @list.setter
    def list(self, value):
        self._x = value

    @list.deleter
    def list(self):
        self._x = None

#decorator to allow a class method to be run on all objects in a list
def func_on_all(liststore):
    def wraps(func):
        def inner(self, *args, **kwargs):
            if liststore.list is None:
              raise ValueError("liststore contains no list")
            func(self, *args, **kwargs)  
            results = [None] * len(liststore.list)
            lasterror = None  
            for index, obj in enumerate(liststore.list):
              try:
                results[index] = getattr(obj, func.__name__)(*args, **kwargs)
              except hmResponseError as e:
                lasterror = e
                continue
              
            if all(result is None for result in results):
              raise hmResponseError("All failed, last error was %s"%(str(lasterror)))

            return results
 
        return inner
    return wraps