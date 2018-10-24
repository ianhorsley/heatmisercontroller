"""Constants and """
        
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
