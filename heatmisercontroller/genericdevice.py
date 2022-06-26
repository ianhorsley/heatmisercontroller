"""Generic Heatmiser Device Class

Modules handle all the DCB and self.fields for each device on the Heatmiser network

Ian Horsley 2018
"""
import logging
import time
import copy
import serial

from .fields import HeatmiserFieldSingleReadOnly, HeatmiserFieldDoubleReadOnly
from .hm_constants import DEFAULT_PROTOCOL, SLAVE_ADDR_MIN, SLAVE_ADDR_MAX
from .hm_constants import MAX_AGE_LONG
from .hm_constants import FIELD_NAME_LENGTH
from .exceptions import HeatmiserResponseError
from .logging_setup import csvlist

class HeatmiserDevice(object):
    """General device class"""

    ## Initialisation functions and low level functions
    def __init__(self, adaptor, devicesettings, generalsettings=None):
        self._adaptor = adaptor

        # initalise variables
        self.dcb_length = None #set after building fields
        self.floorlimiting = None
        self.lastwritetime = None
        self.lastreadtime = None
        # initalise variables that may be overriden by settings
        self.set_protocol = DEFAULT_PROTOCOL #
        self.set_expected_prog_mode = None
        self.set_long_name = 'Unknown'
        self._load_settings(devicesettings, generalsettings) #take all settings and make them attributes

        # initialise external parameters
        self._buildfields() # add fields to self.fields and insome cases add schdulers (extended regularly)
        self._configure_fields() #build fieldname to number dictionary and attached fields to attributes add dcb address to fields and add set dcb_length  (extended in unknown to change length)
        # estimated read time for read_all method
        self.fullreadtime = self._estimate_read_time(self.dcb_length)
        
        self._set_expected_field_values() #set some fields expected values (extended in week)
        self._connect_observers() #connect various observers methods (extended regularly)
        self.rawdata = [None] * self.dcb_length
    
    def _load_settings(self, settings, generalsettings):
        """Loading settings from dictionary into properties"""
        if generalsettings is not None:
            for name, value in generalsettings.items():
                setattr(self, "set_" + name, value)

        for name, value in settings.items():
            setattr(self, "set_" + name, value)

    def _buildfields(self):
        """build list of fields"""
        self.fields = [
            HeatmiserFieldDoubleReadOnly('DCBlen', 0, [], MAX_AGE_LONG),
            HeatmiserFieldSingleReadOnly('vendor', 2, [0, 1], MAX_AGE_LONG, {'heatmiser': 0, 'OEM': 1}),
            HeatmiserFieldSingleReadOnly('version', 3, [], MAX_AGE_LONG),
            HeatmiserFieldSingleReadOnly('model', 4, [0, 5], MAX_AGE_LONG, {'prt_e_model': 3, 'prt_hw_model': 4, False: 0}),  # DT/DT-E/PRT/PRT-E 00/01/02/03
            HeatmiserFieldSingleReadOnly('address', 11, [SLAVE_ADDR_MIN, SLAVE_ADDR_MAX], MAX_AGE_LONG),
        ]
    
    def _set_expected_field_values(self):
        """set the expected values for fields that should be fixed"""
        self.address.expectedvalue = self.set_address
        self.DCBlen.expectedvalue = self.dcb_length
        self.model.expectedvalue = self.model.readvalues[self.set_expected_model]

    @staticmethod
    def _csvlist_field_names_from(fields):
        """return csv of fieldnames from list of fields"""
        return ', '.join(field.name for field in fields)
        
    def _csvlist_field_names_from_ids(self, fieldids):
        """return csv of fieldnames from list of fieldids"""
        fields = [self.fields[fieldid] for fieldid in fieldids]
        return self._csvlist_field_names_from(fields)
        
    def _configure_fields(self):
        """build dict to map field name to index, map fields tables to properties and set dcb addresses."""
        self.fields.sort(key=lambda field: field.address)
        
        dcbaddress = 0
        self.fieldsbyname = {}
        self._fieldnametonum = {}
        for key, field in enumerate(self.fields):
            #set dcbaddress
            field.dcbaddress = dcbaddress
            dcbaddress += field.fieldlength
            #add field to key lookup
            self._fieldnametonum[field.name] = key
            #store field pointer as property
            setattr(self, field.name, field)
            #store field pointer in dictionary
            self.fieldsbyname[field.name] = field
        #record maximum dcb length
        self.dcb_length = dcbaddress
    
    def _connect_observers(self):
        """called to connect obersers to fields"""
        pass
    
    ## Basic reading and getting functions
    
    def read_raw_data(self, startfieldname, endfieldname):
        """Return subset of raw data"""
        return self.rawdata[getattr(self, startfieldname).dcbaddress:getattr(self, endfieldname).last_dcb_byte_address()]
    
    def read_all(self):
        """Returns all the rawdata having got it from the device"""
        try:
            self.rawdata = self._adaptor.read_all_from_device(self.set_address, self.set_protocol, self.dcb_length)
        except serial.SerialException as err:
            logging.warn("C%i Read all failed, Serial Port error %s"%(self.set_address, str(err)))
            raise

        logging.info("C%i Read all"%(self.set_address))

        self.lastreadtime = time.time()
        self._procpayload(self.rawdata)
        return self.rawdata

    def read_field(self, fieldname, maxage=None):
        """Returns a fields value, gets from the device if to old"""
        return self.read_fields([fieldname], maxage)[0]
    
    def read_fields(self, fieldnames, maxage=None):
        """Returns a list of field values, gets from the device if any are to old"""
        #only get field from network if
        # maxage = None, older than the default from fields
        # maxage = -1, not read before
        # maxage >=0, older than maxage
        # maxage = 0, always
        
        fieldids = [self._fieldnametonum[fieldname] for fieldname in fieldnames if hasattr(self, fieldname) and (maxage == 0 or not getattr(self, fieldname).check_data_fresh(maxage))]
        fieldids = list(set(fieldids)) #remove duplicates, ordering doesn't matter

        if len(fieldids) > 0:
            self._get_fields(fieldids)

        return [self.fieldsbyname[fieldname].get_value() if hasattr(self, fieldname) else None for fieldname in fieldnames]
    
    def get_field_range(self, firstfieldname, lastfieldname=None):
        """gets fieldrange from device
        safe for blocks crossing gaps in dcb"""
        if lastfieldname == None:
            lastfieldname = firstfieldname

        firstfieldid = self._fieldnametonum[firstfieldname]
        lastfieldid = self._fieldnametonum[lastfieldname]
            
        blockstoread = self._get_field_blocks_from_id_range(firstfieldid, lastfieldid)
        fieldstring = firstfieldname.ljust(FIELD_NAME_LENGTH) + " " + lastfieldname.ljust(FIELD_NAME_LENGTH)
        self._get_field_blocks(blockstoread, fieldstring)
    
    def _get_fields(self, fieldids):
        """gets fields from device
        safe for blocks crossing gaps in dcb"""
        blockstoread = self._get_field_blocks_from_id_list(fieldids)
        self._get_field_blocks(blockstoread, self._csvlist_field_names_from_ids(fieldids))
    
    def _get_field_blocks(self, blockstoread, fieldstring):
        """gets field blocks from device
        NOT safe for dcb gaps"""
        #blockstoread list of [field, field, blocklength in bytes]
        estimatedreadtime = self._estimate_blocks_read_time(blockstoread)

        if estimatedreadtime < self.fullreadtime - 0.02: #if to close to full read time, then read all
            try:
                for firstfield, lastfield, blocklength in blockstoread:
                    logging.debug("C%i Reading ui %i to %i len %i, proc %s to %s"%(self.set_address, firstfield.address, lastfield.address, blocklength, firstfield.name, lastfield.name))
                    rawdata = self._adaptor.read_from_device(self.set_address, self.set_protocol, firstfield.address, blocklength)
                    self.lastreadtime = time.time()
                    self._procpartpayload(rawdata, firstfield.name, lastfield.name)
            except serial.SerialException as err:
                logging.warn("C%i Read failed of fields %s, Serial Port error %s"%(self.set_address, fieldstring, str(err)))
                raise
            logging.info("C%i Read fields %s, in %i blocks"%(self.set_address, fieldstring, len(blockstoread)))
        else:
            logging.debug("C%i Read fields %s by read_all, %0.3f %0.3f"%(self.set_address, fieldstring, estimatedreadtime, self.fullreadtime))
            self.read_all()
              
        #data can only be requested from the controller in contiguous blocks
        #functions takes a first and last field and separates out the individual blocks available for the controller type
        #return, fieldstart, fieldend, length of read in bytes
    def _get_field_blocks_from_id_range(self, firstfieldid, lastfieldid):
        """Takes range of fieldids and returns field blocks
        
        Splits by fields by address breaks."""
        blocks = []
        previousfield = None

        for field in self.fields[firstfieldid:lastfieldid + 1]:
            if previousfield is not None and field.address - previousfield.address - previousfield.fieldlength == 0: #if follows previousfield:
                blocks[-1][1] = field
                blocks[-1][2] = field.last_dcb_byte_address() - blocks[-1][0].dcbaddress + 1
            else:
                blocks.append([field, field, field.fieldlength])
            previousfield = field

        return blocks
    
    def _get_field_blocks_from_id_list(self, fieldids):
        """Takes range of fieldids and returns field blocks
        Splits by invalid fields. Uses timing to determine the optimum blocking"""
        #find blocks between lowest and highest field
        fullfieldblock = self._get_field_blocks_from_id_range(min(fieldids), max(fieldids))
        readblocks = []
        for firstfield, lastfield, _ in fullfieldblock:
            #find fields in that block
            inblock = [fieldid for fieldid in fieldids if self._fieldnametonum[firstfield.name] <= fieldid <= self._fieldnametonum[lastfield.name]]
            if len(inblock) > 0:
                #if single read is shorter than individual
                readlen = self.fields[max(inblock)].last_dcb_byte_address() - self.fields[min(inblock)].dcbaddress + 1
                if self._estimate_read_time(readlen) < sum([self._estimate_read_time(self.fields[fieldid].fieldlength) for fieldid in inblock]):
                    readblocks.append([self.fields[min(inblock)], self.fields[max(inblock)], readlen])
                else:
                    for ids in inblock:
                        readblocks.append([self.fields[ids], self.fields[ids], self.fields[ids].fieldlength])
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
        """Process data for a single field storing in relevant."""
        #logging.debug("Processing %s data %s"%(fieldinfo.name, csvlist(data)))
        fieldinfo.update_data(data, self.lastreadtime)

    def _procpartpayload(self, rawdata, firstfieldname, lastfieldname):
        """Wraps procpayload by converting fieldnames to fieldids"""
        #rawdata must be a list
        #converts field names to field numbers to allow process of shortened raw data
        logging.debug("C%i Processing Payload from field %s to %s"%(self.set_address, firstfieldname, lastfieldname))
        firstfieldid = self._fieldnametonum[firstfieldname]
        lastfieldid = self._fieldnametonum[lastfieldname]
        self._procpayload(rawdata, firstfieldid, lastfieldid)
        
    def _procpayload(self, rawdata, firstfieldid=0, lastfieldid=False):
        """Split payload with field information and processes each field"""
        logging.debug("C%i Processing Payload from field %i to %i"%(self.set_address, firstfieldid, lastfieldid))
        if not lastfieldid:
            lastfieldid = len(self.fields)
        
        fullfirstdcbadd = self.fields[firstfieldid].dcbaddress
        
        for field in self.fields[firstfieldid:lastfieldid + 1]:
            length = field.fieldlength
            dcbadd = field.dcbaddress - fullfirstdcbadd #adjust for the start of the request
            
            try:
                self._procfield(rawdata[dcbadd:dcbadd+length], field)
            except HeatmiserResponseError as err:
                logging.warn("C%i Field %s process failed due to %s"%(self.set_address, field.name, str(err)))

        self.rawdata[fullfirstdcbadd:fullfirstdcbadd+len(rawdata)] = rawdata
    
    ## Basic set field functions
    
    def set_field(self, fieldname, values):
        """Set a field (single member of fields) on a device to a state or values. Defined for all known field lengths."""
        #values must not be list for field length 1 or 2
        fieldid = self._fieldnametonum[fieldname]
        field = self.fields[fieldid]
        numericvalues = field.write_value_from_text(values) #convert to numbers if input was text
        
        field.is_writable()
        field.check_values(numericvalues)
        payloadbytes = field.format_data_from_value(numericvalues)
        
        printvalues = numericvalues if isinstance(numericvalues, list) else [numericvalues] #adjust for logging
            
        try:
            self._adaptor.write_to_device(self.set_address, self.set_protocol, field.address, field.fieldlength, payloadbytes)
        except serial.SerialException as err:
            logging.warn("C%i failed to set field %s to %s, due to %s"%(self.set_address, fieldname.ljust(FIELD_NAME_LENGTH), csvlist(printvalues), str(err)))
            raise
        logging.info("C%i set field %s to %s"%(self.set_address, fieldname.ljust(FIELD_NAME_LENGTH), csvlist(printvalues)))
        
        self.lastwritetime = time.time()
        field.update_value(numericvalues, self.lastwritetime)
    
    def set_fields(self, fieldnames, values):
        """Set multiple fields on a device to a state or payload."""
        #It groups adjacent fields and issues multiple sets if required.
        #inputs must be matching length lists
        
        fields = [getattr(self, fieldname) for fieldname in fieldnames if hasattr(self, fieldname)]#Get fields
        outputdata = self._get_payload_blocks_from_list(fields, values)
        try:
            for fields, lengthbytes, payloadbytes, writtenvalues in outputdata:
                logging.debug("C%i Setting ui %i len %i, proc %s to %s"%(self.set_address, fields[0].address, lengthbytes, fields[0].name, fields[-1].name))
                self._adaptor.write_to_device(self.set_address, self.set_protocol, fields[0].address, lengthbytes, payloadbytes)
                self.lastwritetime = time.time()
                self._update_fields_values(writtenvalues, fields)
        except serial.SerialException as err:
            logging.warn("C%i settings failed of fields %s, Serial Port error %s"%(self.set_address, self._csvlist_field_names_from(fields), str(err)))
            raise
        logging.info("C%i set fields %s in %i blocks"%(self.set_address, self._csvlist_field_names_from(fields), len(outputdata)))

    def _update_fields_values(self, values, fields):
        """update the field values once data successfully written"""
        for field, value in zip(fields, values):
            field.update_value(value, self.lastwritetime)
    
    @staticmethod
    def _get_payload_blocks_from_list(fields, values):
        """Converts list of fields and values into groups of payload data"""
        #returns fields, lengthbytes, payloadbytes, values
        sortedfields = sorted(enumerate(fields), key=lambda fielde: fielde[1].address)
        
        valuescopy = copy.deepcopy(values) #force copy of values so doesn't get changed later.
        
        outputdata = []
        previousfield = None
        for orginalindex, field in sortedfields:
            #Check field data and sort values
            field.is_writable()
            field.check_values(valuescopy[orginalindex])
            
            
            if len(outputdata) > 0 and field.dcbaddress - previousfield.last_dcb_byte_address() == 1: #if follows previous field ##Shouldn't this be based on unique address?
                outputdata[-1][0].append(field)
                outputdata[-1][1] += field.fieldlength
                outputdata[-1][2].extend(field.format_data_from_value(valuescopy[orginalindex]))
                outputdata[-1][3].append(valuescopy[orginalindex])

            else:
                outputdata.append([[field], field.fieldlength, field.format_data_from_value(valuescopy[orginalindex]), [valuescopy[orginalindex]]])
            previousfield = field
        return outputdata

DEVICETYPES = {
    None: HeatmiserDevice
}
