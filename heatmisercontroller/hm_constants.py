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

#these maps are used to translate the unique address which is the same for all controllers to the DCB address for a specific controller
PROG_MODE_WEEK = 'week'
PROG_MODE_DAY = 'day'
DEFAULT_PROG_MODE = PROG_MODE_DAY #allows broadcast to program both modes.

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
