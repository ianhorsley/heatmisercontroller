class Observable:#Synchronization):
    def __init__(self):
        self.obs = []
        self.changed = 0
        #Synchronization.__init__(self)

    def addObserver(self, observer):
        if observer not in self.obs:
            self.obs.append(observer)

    def deleteObserver(self, observer):
        self.obs.remove(observer)

    def notifyObservers(self, arg = None):
        '''If 'changed' indicates that this object
        has changed, notify all its observers, then
        call clearChanged(). Each observer has its
        update() called with two arguments: this
        observable object and the generic 'arg'.'''
       
        if not self.changed: return
        # Make a local copy in case of synchronous
        # additions of observers:
        localArray = self.obs[:]
        self.clearChanged()
        for observer in localArray:
            #observer.update(self, arg)
            observer()

    def deleteObservers(self): self.obs = []
    def setChanged(self): self.changed = 1
    def clearChanged(self): self.changed = 0
    def hasChanged(self): return self.changed
    def countObservers(self): return len(self.obs)

class Notifier(object):
    def __init__(self):
        self.value = None
        self.nots_is = {}
        self.nots_is_not = self.GeneralNotifier(self)
        self.nots_changed = self.GeneralNotifier(self)
        self.previousvalue = None
        self.notify_value_change = lambda _ : True
    
    def notify_value_change_is(self, value):
        #self.cappedvalue = min(value, self.valuecap)
        #print "cv", self.cappedvalue
        #stop time waste
        if self.value in self.nots_is:
            print "in is", self.previousvalue, self.value
            self.nots_is[self.value].notifyObservers()
        else:
            print "in not"
            self.nots_is_not.notifyObservers()
            
    def notify_value_change_changed(self, value):        
        self.nots_changed.notifyObservers()
        
    class GeneralNotifier(Observable):
        def __init__(self, outer):
            Observable.__init__(self)
            self.previousvalue = None
            self.outer = outer
        def notifyObservers(self, arg = None):
            if not self.outer.value == self.outer.previousvalue:
                print self.outer.name, "changed to", self.outer.value, "from", self.outer.previousvalue
                self.setChanged()
                Observable.notifyObservers(self, arg)
                self.outer.previousvalue = self.outer.value
                
    def get_value(self):
        """method to return the current value"""
        return value
        
    def add_notifable_is(self, value, method):
        self.nots_is.setdefault(value, self.GeneralNotifier(self)).addObserver(method)
        self.notify_value_change = self.notify_value_change_is
    def delete_notifable_is(self, value, method):
        self.nots_is.get(value, self.GeneralNotifierCompare(self)).deleteObserver(method)
    def add_notifable_is_not(self, method):
        self.notify_value_change = self.notify_value_change_is
        self.nots_is_not.addObserver(method)
    def delete_notifable_is_not(self, method):
        self.nots_is_not.deleteObserver(method)
    def add_notifable_changed(self, method):
        self.nots_changed.addObserver(method)
        self.notify_value_change = self.notify_value_change_changed
    def delete_notifable_changed(self, method):
        self.nots_changed.deleteObserver(method) 