"""Generic Heatmiser Device Class

Modules handle all the DCB and self.fields for each device on the Heatmiser network

Ian Horsley 2018
"""
import logging
import time
import copy
import serial

from fields import HeatmiserFieldSingleReadOnly, HeatmiserFieldDoubleReadOnly
from hm_constants import DEFAULT_PROTOCOL, DCB_INVALID
from hm_constants import PROG_MODE_DAY, PROG_MODE_WEEK, PROG_MODES
from hm_constants import MAX_AGE_LONG
from hm_constants import FIELD_NAME_LENGTH
from .exceptions import HeatmiserResponseError
from .logging_setup import csvlist

class HeatmiserDevice(object):
    """General device class"""
    ## Variables used by code
    lastreadtime = 0 #records last time of a successful read

    ## Initialisation functions and low level functions
    def __init__(self, adaptor, devicesettings, generalsettings=None):
        
        self._adaptor = adaptor

        # initialise external parameters
        self.protocol = DEFAULT_PROTOCOL
        self._buildfields()
        self._build_dcb_tables()
        # estimated read time for read_all method
        self.fullreadtime = self._estimate_read_time(self.dcb_length)
        # initialise data structures
        self.expected_prog_mode = None
        self._expected_model_number = 0
        self.long_name = ''

        self._buildfieldtables()
        self.data = dict.fromkeys(self._fieldnametonum.keys(), None)
        self.floorlimiting = None
        self.timeerr = None
        self.fullreadtime = 0 #default to full read
        self.heat_schedule = self.water_schedule = None
        self.lastwritetime = None
        self.lastreadtime = None
        self._update_settings(devicesettings, generalsettings)

        self.rawdata = [None] * self.dcb_length

    def _update_settings(self, settings, generalsettings):
        """Laod and process settings."""

        self._load_settings(settings, generalsettings)
        self._set_expected_field_values()
    
    def _load_settings(self, settings, generalsettings):
        """Loading settings from dictionary into properties"""
        
        if not generalsettings is None:
            for name, value in generalsettings.iteritems():
                setattr(self, name, value)

        for name, value in settings.iteritems():
            setattr(self, name, value)

        try:
            self.long_name
        except AttributeError:
            self.long_name = 'Unknown'

    def _buildfields(self):
        """build list of fields"""
        self.fields = [
            HeatmiserFieldDoubleReadOnly('DCBlen', 0, 1, [], MAX_AGE_LONG),
            HeatmiserFieldSingleReadOnly('vendor', 2, 1, [0, 1], MAX_AGE_LONG),  #00 heatmiser,  01 OEM
            HeatmiserFieldSingleReadOnly('version', 3, 1, [], MAX_AGE_LONG),
            HeatmiserFieldSingleReadOnly('model', 4, 1, [0, 5], MAX_AGE_LONG),  # DT/DT-E/PRT/PRT-E 00/01/02/03
        ]
    
    def _set_expected_field_values(self):
        """set the expected values for fields that should be fixed"""

        self.fields[self._fieldnametonum['address']].expectedvalue = self.address
        self.fields[self._fieldnametonum['DCBlen']].expectedvalue = self.dcb_length
        self.fields[self._fieldnametonum['model']].expectedvalue = self._expected_model_number
        self.fields[self._fieldnametonum['programmode']].expectedvalue = PROG_MODES[self.expected_prog_mode]

    def _csvlist_field_names_from(self, fields):
        """return csv of fieldnames from list of fields"""
        return ', '.join(field.name for field in fields)
        
    def _buildfieldtables(self):
        """build dict to map field name to index"""
        self._fieldnametonum = {}
        for key, field in enumerate(self.fields):
            fieldname = field.name
            self._fieldnametonum[fieldname] = key
            setattr(self, fieldname, field)
                
    def _build_dcb_tables(self):
        """update dcb addresses and list of valid fields """
        self.fields.sort(key=lambda field: field.address)
        
        dcbaddress = 0
        for field in self.fields:
            field.dcbaddress = dcbaddress
            dcbaddress += field.fieldlength
        self.dcb_length = dcbaddress
        
    ## Basic reading and getting functions
    
    def read_all(self):
        """Returns all the field values having got them from the device"""
        try:
            self.rawdata = self._adaptor.read_all_from_device(self.address, self.protocol, self.dcb_length)
        except serial.SerialException as err:

            logging.warn("C%i Read all failed, Serial Port error %s"%(self.address, str(err)))
            raise
        else:
            logging.info("C%i Read all"%(self.address))

            self.lastreadtime = time.time()
            self._procpayload(self.rawdata)
            return self.rawdata

    def read_field(self, fieldname, maxage=None):
        """Returns a fields value, gets from the device if to old"""
        #return field value
        #get field from network if
        # maxage = None, older than the default from fields
        # maxage = -1, not read before
        # maxage >=0, older than maxage
        # maxage = 0, always
        if maxage == 0 or not getattr(self, fieldname).check_data_fresh(maxage):
            if self.autoreadall is True:
                self.get_field_range(fieldname)
            else:
                raise ValueError("Need to read %s first"%fieldname)
        return self.data[fieldname]
    
    def read_fields(self, fieldnames, maxage=None):
        """Returns a list of field values, gets from the device if any are to old"""
        #find which fields need getting because to old
        if not isinstance(fieldnames, list):
            raise TypeError("fieldnames must be a list")
        
        fieldids = [self._fieldnametonum[fieldname] for fieldname in fieldnames if hasattr(self, fieldname) and (maxage == 0 or not getattr(self, fieldname).check_data_fresh(maxage))]
        
        fieldids = list(set(fieldids)) #remove duplicates, ordering doesn't matter
        
        if len(fieldids) > 0 and self.autoreadall is True:
            self._get_fields(fieldids)
        elif len(fieldids) > 0:
            raise ValueError("Need to read fields first")
        return [self.data[fieldname] for fieldname in fieldnames]
    
    def get_variables(self):
        """Gets setroomtemp to hotwaterdemand fields from device"""
        self.get_field_range('setroomtemp', 'hotwaterdemand')
        
    def get_temps_and_demand(self):
        """Gets remoteairtemp to hotwaterdemand fields from device"""
        self.get_field_range('remoteairtemp', 'hotwaterdemand')
    
    def get_field_range(self, firstfieldname, lastfieldname=None):
        """gets fieldrange from device
        
        safe for blocks crossing gaps in dcb"""
        if lastfieldname == None:
            lastfieldname = firstfieldname

        blockstoread = self._get_field_blocks_from_range(firstfieldname, lastfieldname)
        logging.debug(blockstoread)
        estimatedreadtime = self._estimate_blocks_read_time(blockstoread)
        
        if estimatedreadtime < self.fullreadtime - 0.02: #if to close to full read time, then read all
            try:
                for firstfieldid, lastfieldid, blocklength in blockstoread:
                    logging.debug("C%i Reading ui %i to %i len %i, proc %s to %s"%(self.address, self.fields[firstfieldid].address, self.fields[lastfieldid].address, blocklength, self.fields[firstfieldid].name, self.fields[lastfieldid].name))
                    rawdata = self._adaptor.read_from_device(self.address, self.protocol, self.fields[firstfieldid].address, blocklength)
                    self.lastreadtime = time.time()
                    self._procpartpayload(rawdata, self.fields[firstfieldid].name, self.fields[lastfieldid].name)
            except serial.SerialException as err:
                logging.warn("C%i Read failed of fields %s to %s, Serial Port error %s"%(self.address, firstfieldname.ljust(FIELD_NAME_LENGTH), lastfieldname.ljust(FIELD_NAME_LENGTH), str(err)))
                raise
            else:
                logging.info("C%i Read fields %s to %s, in %i blocks"%(self.address, firstfieldname.ljust(FIELD_NAME_LENGTH), lastfieldname.ljust(FIELD_NAME_LENGTH), len(blockstoread)))
        else:
            logging.debug("C%i Read fields %s to %s by read_all, %0.3f %0.3f"%(self.address, firstfieldname.ljust(FIELD_NAME_LENGTH), lastfieldname.ljust(FIELD_NAME_LENGTH), estimatedreadtime, self.fullreadtime))
            self.read_all()
            
    def _get_fields(self, fieldids):
        """gets fields from device
        
        safe for blocks crossing gaps in dcb"""
        
        blockstoread = self._get_field_blocks_from_id_list(fieldids)
        logging.debug(blockstoread)
        estimatedreadtime = self._estimate_blocks_read_time(blockstoread)
        
        if estimatedreadtime < self.fullreadtime - 0.02: #if to close to full read time, then read all
            try:
                for firstfieldid, lastfieldid, blocklength in blockstoread:
                    logging.debug("C%i Reading ui %i to %i len %i, proc %s to %s"%(self.address, self.fields[firstfieldid].address, self.fields[lastfieldid].address, blocklength, self.fields[firstfieldid].name, self.fields[lastfieldid].name))
                    rawdata = self._adaptor.read_from_device(self.address, self.protocol, self.fields[firstfieldid].address, blocklength)
                    self.lastreadtime = time.time()
                    self._procpartpayload(rawdata, self.fields[firstfieldid].name, self.fields[lastfieldid].name)
            except serial.SerialException as err:
                logging.warn("C%i Read failed of fields %s, Serial Port error %s"%(self.address, self._csvlist_field_names_from(fieldids), str(err)))
                raise
            else:
                logging.info("C%i Read fields %s in %i blocks"%(self.address, self._csvlist_field_names_from(fieldids), len(blockstoread)))
                    
        else:
            logging.debug("C%i Read fields %s by read_all, %0.3f %0.3f"%(self.address, self._csvlist_field_names_from(fieldids), estimatedreadtime, self.fullreadtime))
            self.read_all()
                
        #data can only be requested from the controller in contiguous blocks
        #functions takes a first and last field and separates out the individual blocks available for the controller type
        #return, fieldstart, fieldend, length of read in bytes
    def _get_field_blocks_from_range(self, firstfieldname, lastfieldname):
        """Takes range of fieldnames and returns field blocks"""
        firstfieldid = self._fieldnametonum[firstfieldname]
        lastfieldid = self._fieldnametonum[lastfieldname]
        return self._get_field_blocks_from_id_range(firstfieldid, lastfieldid)
        
    def _get_field_blocks_from_id_range(self, firstfieldid, lastfieldid):
        """Takes range of fieldids and returns field blocks
        
        Splits by invalid fields"""
        blocks = []
        previousfieldvalid = False

        for fieldnum, fieldvalid in enumerate(self._fieldsvalid[firstfieldid:lastfieldid + 1], firstfieldid):
            if previousfieldvalid is False and not fieldvalid is False:
                start = fieldnum
            elif not previousfieldvalid is False and fieldvalid is False:
                blocks.append([start, fieldnum - 1, self.fields[fieldnum - 1].address + self.fields[fieldnum - 1].fieldlength - self.fields[start].address])
            
            previousfieldvalid = fieldvalid

        if not previousfieldvalid is False:
            blocks.append([start, lastfieldid, self.fields[lastfieldid].address + self.fields[lastfieldid].fieldlength - self.fields[start].address])
        return blocks
    
    def _get_field_blocks_from_id_list(self, fieldids):
        """Takes range of fieldids and returns field blocks
        
        Splits by invalid fields. Uses timing to determine the optimum blocking"""
        #find blocks between lowest and highest field
        fieldblocks = self._get_field_blocks_from_id_range(min(fieldids), max(fieldids))
        
        readblocks = []
        for block in fieldblocks:
            #find fields in that block
            inblock = [fieldid for fieldid in fieldids if block[0] <= fieldid <= block[1]]
            if len(inblock) > 0:
                #if single read is shorter than individual
                readlen = self.fields[max(inblock)].fieldlength + self.fields[max(inblock)].address - self.fields[min(inblock)].address
                if self._estimate_read_time(readlen) < sum([self._estimate_read_time(self.fields[fieldid].fieldlength) for fieldid in inblock]):
                    readblocks.append([min(inblock), max(inblock), readlen])
                else:
                    for ids in inblock:
                        readblocks.append([ids, ids, self.fields[ids].fieldlength])
        return readblocks
    
    def _estimate_blocks_read_time(self, blocks):
        """estimates read time for a set of blocks, including the COM_BUS_RESET_TIME between blocks
        
        excludes the COM_BUS_RESET_TIME before first block"""
        readtimes = [self._estimate_read_time(x[2]) for x in blocks]
        return sum(readtimes) + self._adaptor.min_time_between_reads() * (len(blocks) - 1)
    
    @staticmethod
    def _estimate_read_time(length):
        """"estimates the read time for a call to read_from_device without COM_BUS_RESET_TIME
        
        based on empirical measurements of one prt_hw_model and 5 prt_e_model"""
        return length * 0.002075 + 0.070727
    
    def _procfield(self, data, fieldinfo):
        """Process data for a single field storing in relevant.
        
        Converts from bytes to integers/floats
        Checks the validity"""
        fieldname = fieldinfo.name

        #logging.debug("Processing %s %s"%(fieldinfo.name,csvlist(data)))
        if data is None:
            value = None
        else:
            value = fieldinfo.update_data(data, self.lastreadtime)
            #unless sent payload and don't know the read value
        
        if fieldname == 'version' and self.expected_model != 'prt_hw_model':
            value = data[0] & 0x7f
            self.floorlimiting = data[0] >> 7
            self.data['floorlimiting'] = self.floorlimiting
        
        self.data[fieldname] = value
        
        if fieldname == 'currenttime':
            self._checkcontrollertime()

    def _procpartpayload(self, rawdata, firstfieldname, lastfieldname):
        """Wraps procpayload by converting fieldnames to fieldids"""
        #rawdata must be a list
        #converts field names to unique addresses to allow process of shortened raw data
        logging.debug("C%i Processing Payload from field %s to %s"%(self.address, firstfieldname, lastfieldname))
        firstfieldid = self._fieldnametonum[firstfieldname]
        lastfieldid = self._fieldnametonum[lastfieldname]
        self._procpayload(rawdata, firstfieldid, lastfieldid)
        
    def _procpayload(self, rawdata, firstfieldid=0, lastfieldid=False):
        """Split payload with field information and processes each field"""
        logging.debug("C%i Processing Payload from field %i to %i"%(self.address, firstfieldid, lastfieldid))
        
        if not lastfieldid:
            lastfieldid = len(self.fields)
        
        fullfirstdcbadd = self.fields[firstfieldid].dcbaddress
        
        for fieldinfo in self.fields[firstfieldid:lastfieldid + 1]:
            uniqueaddress = fieldinfo.address
            
            length = fieldinfo.fieldlength
            dcbadd = fieldinfo.dcbaddress

            if dcbadd == DCB_INVALID:
                getattr(self, fieldinfo.name).value = None
                self.data[fieldinfo.name] = None
            else:
                dcbadd -= fullfirstdcbadd #adjust for the start of the request
                
                try:
                    self._procfield(rawdata[dcbadd:dcbadd+length], fieldinfo)
                except HeatmiserResponseError as err:
                    logging.warn("C%i Field %s process failed due to %s"%(self.address, fieldinfo.name, str(err)))

        self.rawdata[fullfirstdcbadd:fullfirstdcbadd+len(rawdata)] = rawdata
    
    ## Basic set field functions
    
    def set_field(self, fieldname, values):
        """Set a field (single member of fields) on a device to a state or values. Defined for all known field lengths."""
        #values must not be list for field length 1 or 2
        fieldid = self._fieldnametonum[fieldname]
        if not hasattr(self, fieldname):
            raise IndexError('Field not valid for this device')
        field = self.fields[fieldid]
        
        field.is_writable()
        field.check_payload_values(values)
        payloadbytes = field.format_data_from_value(values)
        
        printvalues = values if isinstance(values, list) else [values] #adjust for logging
            
        try:
            self._adaptor.write_to_device(self.address, self.protocol, field.address, field.fieldlength, payloadbytes)
        except serial.SerialException as err:
            logging.warn("C%i failed to set field %s to %s, due to %s"%(self.address, fieldname.ljust(FIELD_NAME_LENGTH), csvlist(printvalues), str(err)))
            raise
        else:
            logging.info("C%i set field %s to %s"%(self.address, fieldname.ljust(FIELD_NAME_LENGTH), csvlist(printvalues)))
        
        self.lastwritetime = time.time()
        self.data[fieldname] = field.update_value(values, self.lastwritetime)
    
    def set_fields(self, fieldnames, values):
        """Set multiple fields on a device to a state or payload."""
        #It groups adjacent fields and issues multiple sets if required.
        #inputs must be matching length lists
        
        
        fields = [getattr(self, fieldname) for fieldname in fieldnames]#Get fields
        outputdata = self._get_payload_blocks_from_list(fields, values)
        try:
            for unique_start_address, lengthbytes, payloadbytes, firstfieldname, lastfieldname, writtenvalues, fields in outputdata:
                logging.debug("C%i Setting ui %i len %i, proc %s to %s"%(self.address, unique_start_address, lengthbytes, firstfieldname, lastfieldname))
                self._adaptor.write_to_device(self.address, self.protocol, unique_start_address, lengthbytes, payloadbytes)
                self.lastwritetime = time.time()
                self._update_fields_values(writtenvalues, fields)
        except serial.SerialException as err:
            logging.warn("C%i settings failed of fields %s, Serial Port error %s"%(self.address, self._csvlist_field_names_from(fields), str(err)))
            raise
        else:
            logging.info("C%i set fields %s in %i blocks"%(self.address, self._csvlist_field_names_from(fields), len(outputdata)))

    def _update_fields_values(self, values, fields):
        """update the field values once data successfully written"""
        for field, value in zip(fields, values):
            self.data[field.name] = field.update_value(value, self.lastwritetime)
            
    def _get_payload_blocks_from_list(self, fields, values):
        """Converts list of fields and values into groups of payload data"""
        #returns unique_start_address, lengthbytes, payloadbytes, firstfieldname, lastfieldname
        sortedfields = sorted(enumerate(fields), key=lambda fielde: fielde[1].address)
        
        valuescopy = copy.deepcopy(values) #force copy of values so doesn't get changed later.
        
        #Check field data and sort values
        sorteddata = []
        for orginalindex, field in sortedfields:
            field.is_writable()
            field.check_payload_values(valuescopy[orginalindex])
            sorteddata.append([field, valuescopy[orginalindex]]) 
        
        #Groups and map to unique addresses
        outputdata = []
        previousfield = None
        for field, value in sorteddata:
            if not previousfield is None and field.dcbaddress - previousfield.last_dcb_byte_address() == 1: #if follows previousfield
                outputdata[-1][1] += field.fieldlength
                outputdata[-1][2].extend(field.format_data_from_value(value))
                outputdata[-1][4] = field.name
                outputdata[-1][5].append(value)
                outputdata[-1][6].append(field)
            else:
                #unique_start_address, bytelength, payloadbytes, firstfieldname, lastfieldname, values, firstfieldid
                outputdata.append([field.address, field.fieldlength, field.format_data_from_value(value), field.name, field.name, [value], [field]])
            previousfield = field

        return outputdata