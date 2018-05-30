#
# Ian Horsley 2018

#
# Sets time and gets information on all controllers
#

# Assume Python 2.7.x
#

# Protocols
HMV2_ID = 2
HMV3_ID = 3
DEFAULT_PROTOCOL = HMV3_ID

BYTEMASK = 0xff

DONT_CARE_LENGTH = 1
TIME_ERR_LIMIT = 10

#
# HM Version 3 Magic Numbers
#

# Master must be in range [0x81,0xa0] = [129,160]
MASTER_ADDR_MIN = 0x81
MASTER_ADDR_MAX = 0xa0
SLAVE_ADDR_MIN = 1
SLAVE_ADDR_MAX = 32

MAX_FRAME_RESP_LENGTH = 159 # NB max return is 75 in 5/2 mode or 159 in 7day mode
MIN_FRAME_RESP_LENGTH = 7
FRAME_WRITE_RESP_LENGTH = 7
MIN_FRAME_READ_RESP_LENGTH = 11
MIN_FRAME_SEND_LENGTH = 10
MAX_PAYLOAD_SEND_LENGTH = 100
CRC_LENGTH = 2

# Define magic numbers used in messages
FUNC_READ  = 0
FUNC_WRITE = 1

BROADCAST_ADDR = 0xff
RW_LENGTH_ALL = 0xffff
DCB_START = 0x00

SET_TEMP_ADDR = 18
KEY_LOCK_ADDR = 22
HOL_HOURS_LO_ADDR = 24
HOL_HOURS_HI_ADDR = 25
CUR_TIME_ADDR = 43

KEY_LOCK_UNLOCK = 0
KEY_LOCK_LOCK = 1

# Define frame send contents
FS_DEST_ADDR = 0
FS_LEN = 1
FS_SOURCE_ADDR = 2
FS_FUNC_CODE = 3

# Define frame response contents
FR_DEST_ADDR = 0
FR_LEN_LOW = 1
FR_LEN_HIGH = 2
FR_SOURCE_ADDR = 3
FR_FUNC_CODE = 4
FR_START_LOW = 5 # this field and following on present if function code read
FR_START_HIGH = 6
FR_CONT_LEN_LOW = 7
FR_CONT_LEN_HIGH = 8
FR_CONTENTS = 9

# Define payload response contents
PL_LEN_HIGH = 0
PL_LEN_LOW = 1 
PL_VENDOR_ID = 2
#PL_LIMITS = 3
PL_MODEL = 4
PL_PROG_MODE = 16

# Define DCB write addresses
UNIQUE_WRITEABLE_ADDRESSES = [17,18,19,21,22,23,24,32,42,43]
UNIQUE_WRITEABLE_ABOVE = 47

DCB_ON_OFF = 21
DCB_RUN_MODE = 23

UNIQUE_ADD_MODEL = 4

FIELD_NAME_LENGTH = 13
MAX_UNIQUE_ADDRESS = 298
#name, unique_address,length,divisor, valid range, writeable]
UNIADD_ADD = 0
UNIADD_LEN = 1
UNIADD_DIV = 2
UNIADD_RANGE = 3
UNIADD_WRITE = 4
uniadd = {'DCBlen':[0,2,1,[]],
'vendor':[2,1,1,[0,1]], #00 heatmiser, 01 OEM
'version':[3,1,1,[]],
'model': [4,1,1,[0,5]], # DT/DT-E/PRT/PRT-E 00/01/02/03
'tempformat': [5,1,1,[0,1]], # 00 C, 01 F
'switchdiff': [6,1,1,[1,3]],
'frostprot': [7,1,1,[0,1]], #0=enable frost prot when display off, (opposite in protocol manual, but tested and user guide is correct)  (default should be enabled)
'caloffset': [8,2,1,[]],
'outputdelay': [10,1,1,[0,15]], # minutes (to prevent rapid switching)
'address': [11,1,1,[SLAVE_ADDR_MIN,SLAVE_ADDR_MAX]],
'updwnkeylimit': [12,1,1,[0,10]],  #limits use of up and down keys
'sensorsavaliable': [13,1,1,[0,4]], #00 built in only, 01 remote air only, 02 floor only, 03 built in + floor, 04 remote + floor
'optimstart': [14,1,1,[0,3]], # 0 to 3 hours, default 0
'rateofchange': [15,1,1,[]], #number of minutes per degree to raise the temperature, default 20. Applies to the Wake and Return comfort levels (1st and 3rd)
'programmode': [16,1,1,[0,1]], #0=5/2, 1= 7day
'frosttemp': [17,1,1,[7,17],'W'], #default is 12, frost protection temperature
'setroomtemp': [18,1,1,[5,35],'W'],
'floormaxlimit': [19,1,1,[20,45],'W'],
'floormaxlimitenable': [20,1,1,[0,1]], #1=enable
'onoff': [21,1,1,[0,1],'W'], #1 = on
'keylock': [22,1,1,[0,1],'W'], #1 = on
'runmode': [23,1,1,[0,1],'W'],  #0 = heating mode, 1 = frost protection mode
'holidayhours': [24,2,1,[0,720],'W'], #range guessed and tested, setting to 0 cancels hold and puts back to program gap from 26 to 31
'tempholdmins': [32,2,1,[0,5760],'W'], #range guessed and tested, setting to 0 cancels hold and puts setroomtemp back to program
'remoteairtemp': [34,2,10,[]], #ffff if no sensor
'floortemp': [36,2,10,[]], #ffff if no sensor
'airtemp': [38,2,10,[]], #ffff if no sensor
'errorcode': [40,1,1,[0,3]], #0 built in, 1, floor, 2 remote
'heatingstate': [41,1,1,[0,1]], #0 none, 1 heating currently
'hotwaterstate': [42,1,1,[0,3],'W'], # read [0=off,1=on], write [0=as prog,1=override on,2=overide off]
'currenttime': [43,4,1,[[1,7],[0,23],[0,59],[0,59]],'W'], #day (Mon - Sun), hour, min, sec.
#5/2 progamming #if hour = 24 entry not used
'wday_heat':[47,12,1,[[0,24],[0,59],[5,35]],"W"], #hour, min, temp  (should minutes be only 0 and 30?)
'wend_heat':[59,12,1,[[0,24],[0,59],[5,35]],"W"],
'wday_water':[71,16,1,[[0,24],[0,59]],"W"], # pairs, on then off repeated, hour, min
'wend_water':[87,16,1,[[0,24],[0,59]],"W"],
#7day progamming
'mon_heat':[103,12,1,[[0,24],[0,59],[5,35]],"W"],
'tues_heat':[115,12,1,[[0,24],[0,59],[5,35]],"W"],
'wed_heat':[127,12,1,[[0,24],[0,59],[5,35]],"W"],
'thurs_heat':[139,12,1,[[0,24],[0,59],[5,35]],"W"],
'fri_heat':[151,12,1,[[0,24],[0,59],[5,35]],"W"],
'sat_heat':[163,12,1,[[0,24],[0,59],[5,35]],"W"],
'sun_heat':[175,12,1,[[0,24],[0,59],[5,35]],"W"],
'mon_water':[187,16,1,[[0,24],[0,59]],"W"],
'tues_water':[203,16,1,[[0,24],[0,59]],"W"],
'wed_water':[219,16,1,[[0,24],[0,59]],"W"],
'thurs_water':[235,16,1,[[0,24],[0,59]],"W"],
'fri_water':[251,16,1,[[0,24],[0,59]],"W"],
'sat_water':[267,16,1,[[0,24],[0,59]],"W"],
'sun_water':[283,16,1,[[0,24],[0,59]],"W"],
}

CURRENT_TIME_DAY = 0
CURRENT_TIME_HOUR = 1
CURRENT_TIME_MIN = 2
CURRENT_TIME_SEC = 3

READ_FROST_PROT_ON = 0
READ_FROST_PROT_OFF = 1

READ_SENSORS_AVALIABLE_INT_ONLY = 00
READ_SENSORS_AVALIABLE_EXT_ONLY = 01
READ_SENSORS_AVALIABLE_FLOOR_ONLY = 02
READ_SENSORS_AVALIABLE_INT_FLOOR = 03
READ_SENSORS_AVALIABLE_EXT_FLOOR = 04

READ_PROGRAM_MODE_5_2 = 0
READ_PROGRAM_MODE_7 = 1

WRITE_ONOFF_OFF = 0
WRITE_ONOFF_ON = 1
WRITE_KEYLOCK_OFF = 0
WRITE_KEYLOCK_ON = 1

WRITE_RUNMODE_HEATING = 0
WRITE_RUNMODE_FROST = 1
WRITE_HOTWATERSTATE_PROG = 0
WRITE_HOTWATERSTATE_OVER_ON = 1
WRITE_HOTWATERSTATE_OVER_OFF = 2

#mapping for chunks of heating schedule for a day
HEAT_MAP_HOUR = 0
HEAT_MAP_MIN = 1
HEAT_MAP_TEMP = 2
HOUR_UNUSED = 24

#these maps are used to translate the unique address which is the same for all controllers to the DCB address for a specific controller
PROG_MODE_WEEK = 0
PROG_MODE_DAY = 1
DEFAULT_PROG_MODE = PROG_MODE_DAY #allows broadcast to program both modes.

#PRT-E DCB map
DCB_INVALID = -1
PRTEmap = range(2)
PRTEmap[0] = list(reversed([(25,0),(31,DCB_INVALID),(41,6),(42,DCB_INVALID),(70,7),(MAX_UNIQUE_ADDRESS,DCB_INVALID)]))
PRTEmap[1] = list(reversed([(25,0),(31,DCB_INVALID),(41,6),(42,DCB_INVALID),(70,7),(102,DCB_INVALID),(186,39),(MAX_UNIQUE_ADDRESS,DCB_INVALID)]))
PRT_E_MODEL = 03
PRTHWmap = range(2)
PRTHWmap[0] = list(reversed([(25,0),(31,DCB_INVALID),(102,6),(MAX_UNIQUE_ADDRESS,DCB_INVALID)]))
PRTHWmap[1] = list(reversed([(25,0),(31,DCB_INVALID),(MAX_UNIQUE_ADDRESS,6)]))
PRT_HW_MODEL = 04
STRAIGHTmap = list([(MAX_UNIQUE_ADDRESS,0)])