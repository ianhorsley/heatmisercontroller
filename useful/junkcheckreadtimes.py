#!/usr/bin/python
#
# Ian Horsley 2018

#
# Sets a bunch of different configurations on stats
#
from timeit import default_timer as timer
import logging

from heatmisercontroller.logging_setup import initialize_logger
from heatmisercontroller.hm_constants import *
from heatmisercontroller.network import *
from heatmisercontroller.exceptions import hmResponseError



initialize_logger('logs', logging.WARN, True)
hmn1 = HeatmiserNetwork()

stat = hmn1.B1
address = stat._address
bcdlen = stat.DCBlength

#field = 'tempholdmins' #Kit
#field = 'currenttime' #Others
field = 'mon_heat' #Others on day

print stat._getFieldBlocks('DCBlen','sun_water')
print stat.DCBlength

import numpy as np

def all():
    print "All No proc"
    times = []
    for i in range(tests):
        try:
            start = timer()
            hmn1.adaptor.hmReadAllFromController(address, HMV3_ID, bcdlen)
            times.append(timer() - start - hmn1.adaptor.serport.COM_BUS_RESET_TIME) 
        except:
            print "errored"
            time.sleep(5)
    print "%.3f"%np.median(times), len(times)

def test(number):
    print "%i No proc"%number
    times = []
    for i in range(tests):
        try:
            start = timer()
            hmn1.adaptor.hmReadFromController(address, HMV3_ID, uniadd[field][UNIADD_ADD], number)
            times.append(timer() - start - hmn1.adaptor.serport.COM_BUS_RESET_TIME) 
        except:
            pass        
    print "%.3f"%np.median(times), len(times)


tests = 30
cases = [1,150,200,250]
for i in cases:
    test(i)
all()
