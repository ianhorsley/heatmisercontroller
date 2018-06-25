"""Constants and field definitions for Heatmiser protocol"""

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

# Master must be in range [0x81, 0xa0] = [129, 160]
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
FUNC_READ = 0
FUNC_WRITE = 1

BROADCAST_ADDR = 0xff
RW_LENGTH_ALL = 0xffff
DCB_START = 0x00

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

MAX_AGE_LONG = 86400
MAX_AGE_MEDIUM = 3600
MAX_AGE_SHORT = 65
MAX_AGE_USHORT = 11

FIELD_NAME_LENGTH = 13
MAX_UNIQUE_ADDRESS = 298
#name,  unique_address, length, divisor,  valid range,  writeable]
FIELD_NAME = 0
FIELD_ADD = 1
FIELD_LEN = 2
FIELD_DIV = 3
FIELD_RANGE = 4
FIELD_MAX_AGE = 5
FIELD_WRITE = 6
fields = [
['DCBlen', 0, 2, 1, [], MAX_AGE_LONG],
['vendor', 2, 1, 1, [0, 1], MAX_AGE_LONG],  #00 heatmiser,  01 OEM
['version', 3, 1, 1, [], MAX_AGE_LONG],
['model', 4, 1, 1, [0, 5], MAX_AGE_LONG],  # DT/DT-E/PRT/PRT-E 00/01/02/03
['tempformat', 5, 1, 1, [0, 1], MAX_AGE_LONG],  # 00 C,  01 F
['switchdiff', 6, 1, 1, [1, 3], MAX_AGE_LONG],
['frostprot', 7, 1, 1, [0, 1], MAX_AGE_LONG],  #0=enable frost prot when display off,  (opposite in protocol manual,  but tested and user guide is correct)  (default should be enabled)
['caloffset', 8, 2, 1, [], MAX_AGE_LONG],
['outputdelay', 10, 1, 1, [0, 15], MAX_AGE_LONG],  # minutes (to prevent rapid switching)
['address', 11, 1, 1, [SLAVE_ADDR_MIN, SLAVE_ADDR_MAX], MAX_AGE_LONG],
['updwnkeylimit', 12, 1, 1, [0, 10], MAX_AGE_LONG],   #limits use of up and down keys
['sensorsavaliable', 13, 1, 1, [0, 4], MAX_AGE_LONG],  #00 built in only,  01 remote air only,  02 floor only,  03 built in + floor,  04 remote + floor
['optimstart', 14, 1, 1, [0, 3], MAX_AGE_LONG],  # 0 to 3 hours,  default 0
['rateofchange', 15, 1, 1, [], MAX_AGE_LONG],  #number of minutes per degree to raise the temperature,  default 20. Applies to the Wake and Return comfort levels (1st and 3rd)
['programmode', 16, 1, 1, [0, 1], MAX_AGE_LONG],  #0=5/2,  1= 7day
['frosttemp', 17, 1, 1, [7, 17], MAX_AGE_LONG, 'W'],  #default is 12,  frost protection temperature
['setroomtemp', 18, 1, 1, [5, 35], MAX_AGE_USHORT, 'W'],
['floormaxlimit', 19, 1, 1, [20, 45], MAX_AGE_LONG, 'W'],
['floormaxlimitenable', 20, 1, 1, [0, 1], MAX_AGE_LONG],  #1=enable
['onoff', 21, 1, 1, [0, 1], MAX_AGE_SHORT, 'W'],  #1 = on
['keylock', 22, 1, 1, [0, 1], MAX_AGE_SHORT, 'W'],  #1 = on
['runmode', 23, 1, 1, [0, 1], MAX_AGE_SHORT, 'W'],   #0 = heating mode,  1 = frost protection mode
['holidayhours', 24, 2, 1, [0, 720], MAX_AGE_SHORT, 'W'],  #range guessed and tested,  setting to 0 cancels hold and puts back to program 
['unknown', 26, 6, 1, [], MAX_AGE_LONG],  # gap from 26 to 31
['tempholdmins', 32, 2, 1, [0, 5760], MAX_AGE_SHORT, 'W'],  #range guessed and tested,  setting to 0 cancels hold and puts setroomtemp back to program
['remoteairtemp', 34, 2, 10, [], MAX_AGE_USHORT],  #ffff if no sensor
['floortemp', 36, 2, 10, [], MAX_AGE_USHORT],  #ffff if no sensor
['airtemp', 38, 2, 10, [], MAX_AGE_USHORT],  #ffff if no sensor
['errorcode', 40, 1, 1, [0, 3], MAX_AGE_SHORT],  # 0 is no error # errors,  0 built in,  1,  floor,  2 remote
['heatingdemand', 41, 1, 1, [0, 1], MAX_AGE_USHORT],  #0 none,  1 heating currently
['hotwaterdemand', 42, 1, 1, [0, 2], MAX_AGE_USHORT, 'W'],  # read [0=off, 1=on],  write [0=as prog, 1=override on, 2=overide off]
['currenttime', 43, 4, 1, [[1, 7], [0, 23], [0, 59], [0, 59]], MAX_AGE_USHORT, 'W'],  #day (Mon - Sun),  hour,  min,  sec.
#5/2 progamming #if hour = 24 entry not used
['wday_heat', 47, 12, 1, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM, "W"],  #hour,  min,  temp  (should minutes be only 0 and 30?)
['wend_heat', 59, 12, 1, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM, "W"],
['wday_water', 71, 16, 1, [[0, 24], [0, 59]], MAX_AGE_MEDIUM, "W"],  # pairs,  on then off repeated,  hour,  min
['wend_water', 87, 16, 1, [[0, 24], [0, 59]], MAX_AGE_MEDIUM, "W"],
#7day progamming
['mon_heat', 103, 12, 1, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM, "W"],
['tues_heat', 115, 12, 1, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM, "W"],
['wed_heat', 127, 12, 1, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM, "W"],
['thurs_heat', 139, 12, 1, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM, "W"],
['fri_heat', 151, 12, 1, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM, "W"],
['sat_heat', 163, 12, 1, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM, "W"],
['sun_heat', 175, 12, 1, [[0, 24], [0, 59], [5, 35]], MAX_AGE_MEDIUM, "W"],
['mon_water', 187, 16, 1, [[0, 24], [0, 59]], MAX_AGE_MEDIUM, "W"],
['tues_water', 203, 16, 1, [[0, 24], [0, 59]], MAX_AGE_MEDIUM, "W"],
['wed_water', 219, 16, 1, [[0, 24], [0, 59]], MAX_AGE_MEDIUM, "W"],
['thurs_water', 235, 16, 1, [[0, 24], [0, 59]], MAX_AGE_MEDIUM, "W"],
['fri_water', 251, 16, 1, [[0, 24], [0, 59]], MAX_AGE_MEDIUM, "W"],
['sat_water', 267, 16, 1, [[0, 24], [0, 59]], MAX_AGE_MEDIUM, "W"],
['sun_water', 283, 16, 1, [[0, 24], [0, 59]], MAX_AGE_MEDIUM, "W"]
]

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

WRITE_HOTWATERDEMAND_PROG = 0
WRITE_HOTWATERDEMAND_OVER_ON = 1
WRITE_HOTWATERDEMAND_OVER_OFF = 2
READ_HOTWATERDEMAND_OFF = 0
READ_HOTWATERDEMAND_ON = 1

#these maps are used to translate the unique address which is the same for all controllers to the DCB address for a specific controller
PROG_MODE_WEEK = 'week'
PROG_MODE_DAY = 'day'
DEFAULT_PROG_MODE = PROG_MODE_DAY #allows broadcast to program both modes.
PROG_MODES = {'week':0, 'day':1}

#models
DEVICE_MODELS = {'prt_e_model': 3, 'prt_hw_model': 4, False: 0}
#PRT-E DCB map
DCB_INVALID = None
PRTEmap = {}
PRTEmap[PROG_MODE_WEEK] = list(reversed([(25, 0), (31, DCB_INVALID), (41, 6), (42, DCB_INVALID), (70, 7), (MAX_UNIQUE_ADDRESS, DCB_INVALID)]))
PRTEmap[PROG_MODE_DAY] = list(reversed([(25, 0), (31, DCB_INVALID), (41, 6), (42, DCB_INVALID), (70, 7), (102, DCB_INVALID), (186, 39), (MAX_UNIQUE_ADDRESS, DCB_INVALID)]))
PRTHWmap = {}
PRTHWmap[PROG_MODE_WEEK] = list(reversed([(25, 0), (31, DCB_INVALID), (102, 6), (MAX_UNIQUE_ADDRESS, DCB_INVALID)]))
PRTHWmap[PROG_MODE_DAY] = list(reversed([(25, 0), (31, DCB_INVALID), (MAX_UNIQUE_ADDRESS, 6)]))
STRAIGHTmap = list([(MAX_UNIQUE_ADDRESS, 0)])

#Fields for each stat type and mode,  list of ranges.
#PRT-E fields
FIELDRANGES = {}
FIELDRANGES['prt_e_model'] = {}
FIELDRANGES['prt_e_model'][PROG_MODE_WEEK] = [['DCBlen', 'holidayhours'], ['tempholdmins', 'heatingdemand'], ['currenttime', 'wend_heat']]
FIELDRANGES['prt_e_model'][PROG_MODE_DAY] = [['DCBlen', 'holidayhours'], ['tempholdmins', 'heatingdemand'], ['currenttime', 'wend_heat'], ['mon_heat', 'sun_heat']]
#PRT-HW fields
FIELDRANGES['prt_hw_model'] = {}
FIELDRANGES['prt_hw_model'][PROG_MODE_WEEK] = [['DCBlen', 'holidayhours'], ['tempholdmins', 'wend_water']]
FIELDRANGES['prt_hw_model'][PROG_MODE_DAY] = [['DCBlen', 'holidayhours'], ['tempholdmins', 'sun_water']]
#Full map
FIELDRANGES[False] = {PROG_MODE_WEEK: [['DCBlen', 'sun_water']], PROG_MODE_DAY: [['DCBlen', 'sun_water']]}
