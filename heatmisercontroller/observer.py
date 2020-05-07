"""Observer framework to trigger methods"""

class Observable(object):
    """Observerable object that manages observer methods"""
    def __init__(self):
        self.obs = []
        self.changed = 0

    def add_observer(self, observer):
        """add obserser method if not already connected"""
        if observer not in self.obs:
            self.obs.append(observer)

    def delete_observer(self, observer):
        """remove observer method"""
        self.obs.remove(observer)

    def notify_observers(self, arg=None):
        '''If 'changed' indicates that this object
        has changed, notify all its observers, then
        call clearChanged(). Each observer is called directly'''
       
        if not self.changed: return
        # additions of observers:
        self.clear_changed()
        for observer in self.obs:
            #observer.update(self, arg)
            observer(arg)

    def delete_observers(self):
        self.obs = []
    def set_changed(self):
        self.changed = 1
    def clear_changed(self):
        self.changed = 0
    def has_changed(self):
        return self.changed
    def count_observers(self):
        return len(self.obs)

class Notifier(object):
    """Object that notfies observers when value changes.
    Either triggers on is/is not or on any change."""
    def __init__(self):
        self.value = None
        self.nots_is = {}
        self.nots_is_not = self.GeneralNotifier(self)
        self.nots_changed = self.GeneralNotifier(self)
        self.previousvalue = None
        self.notify_value_change = lambda _: True # no action, unless observers added
    
    def notify_value_change_is(self, value):
        """Nofifies observers if value is, otherwise notifies other observers."""
        if value in self.nots_is:
            self.nots_is[self.value].notify(self)
        else:
            self.nots_is_not.notify(self)
            
    def notify_value_change_changed(self, _):
        """Notifies obersers on any change."""
        self.nots_changed.notify(self)
        
    class GeneralNotifier(Observable):
        """Notifier which only triggers on change of outer value"""
        def __init__(self, outer):
            Observable.__init__(self)
            self.previousvalue = None
            self.outer = outer

        def notify(self, arg=None):
            """Notify if changed."""
            if not self.outer.value == self.outer.previousvalue:
                self.set_changed()
                Observable.notify_observers(self, arg)
                self.outer.previousvalue = self.outer.value

    def add_notifable_is(self, value, method):
        """Add notifable for value is."""
        self.nots_is.setdefault(value, self.GeneralNotifier(self)).add_observer(method)
        self.notify_value_change = self.notify_value_change_is
    def delete_notifable_is(self, value, method):
        """Remove notifiable."""
        self.nots_is.get(value, self.GeneralNotifierCompare(self)).delete_observer(method)
    def add_notifable_is_not(self, method):
        """Add notifable for value is not."""
        self.notify_value_change = self.notify_value_change_is
        self.nots_is_not.add_observer(method)
    def delete_notifable_is_not(self, method):
        """Remove notifiable."""
        self.nots_is_not.delete_dbserver(method)
    def add_notifable_changed(self, method):
        """Add notifable for value changes."""
        self.nots_changed.add_observer(method)
        self.notify_value_change = self.notify_value_change_changed
    def delete_notifable_changed(self, method):
        """Remove notifiable."""
        self.nots_changed.delete_observer(method)
