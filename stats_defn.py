#
# Ian Horsley 2018
#

from hm_constants import *

# A zone is a controlled area from a single thermostat
# A zone may consist of one or more heating circuits
# Each heating circuit covers a floor area

CONTROL_MODE_AUTO = 0 #temps follow user inputs
CONTROL_MODE_MANUAL = 1 #Ignores user inputs and takes manual data ###manual currently implimented as frost

# A list of controllers
# Adjust the number of rows in this list as required
# Items in each row are :
# Controller Address, ShortName, LongName, Protocol, Graph Colour, List of circuits on this zone, Model, Program Mode (Week or Day), Control Mode, Frost Target
StatList = [
[1,  "Kit", "Kitchen",    HMV3_ID, "A020F0", [19,20], PRT_HW_MODEL, PROG_MODE_DAY, CONTROL_MODE_AUTO, 10],
[2,  "B1", "Bedroom 1", HMV3_ID, "D02090", [21,22], PRT_E_MODEL, PROG_MODE_DAY, CONTROL_MODE_AUTO, 10],
[3,  "B2", "Bedroom 2",   HMV3_ID, "FF4500", [17,18], PRT_E_MODEL, PROG_MODE_DAY, CONTROL_MODE_AUTO, 10],
# [4,  "Livig", "Living",   HMV3_ID, "FF8C00", [13,14,15,16]],
[5,  "Cons", "Conservatory",  HMV3_ID, "FA8072", [23,5,7], PRT_E_MODEL, PROG_MODE_WEEK, CONTROL_MODE_MANUAL, 12]#,
]

# Named indexing into StatList
SL_ADDR = 0
SL_SHORT_NAME = 1
SL_LONG_NAME = 2
SL_PROTOCOL = 3
SL_GRAPH_COL = 4
SL_CIRCUITS = 5
SL_EXPECTED_TYPE = 6
SL_MODE = 7
SL_CONTROL_MODE = 8
SL_FROST_TEMP = 9

# A list of circuits
# A circuit is a single run of pipe from manifold
# Circuit No., ShortName, LongName, Area heated
# Area heated is a list of rectangles, each rectangle has a x and y dimension
#    This means you do not have to work out the area, just the size of the rectangles that make up the area
CircuitList = [
[1,  "Bath", "Bathroom", [[2.15,2.8],[1.0,1.0]]],
]

# Named indexing into CircuitList
CL_ADDR = 0
CL_SHRT_NAME = 1
CL_LONG_NAME = 2
CL_RECTANGLES = 3
