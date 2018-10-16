"""Heatmiser Adaptor handles serial connection and basic framing for the Heatmiser Protocol"""

import time
import logging
import serial

from hm_constants import MAX_FRAME_RESP_LENGTH, MIN_FRAME_READ_RESP_LENGTH, DCB_START, FUNC_WRITE, FUNC_READ, BROADCAST_ADDR, FRAME_WRITE_RESP_LENGTH, FR_CONTENTS, RW_LENGTH_ALL, CRC_LENGTH
import framing
from .exceptions import HeatmiserResponseError, HeatmiserResponseErrorCRC

def retryer(max_retries=3):
    """Decorates reading from and writing to devices, rerunning the methods on failure"""
    def wraps(func):
        """Part of decorator"""
        def inner(*args, **kwargs):
            """Part of decorator"""
            lasterror = None
            for i in range(max_retries):
                if i is not 0:
                    logging.warn("Gen retrying due to %s"%str(lasterror))
                try:
                    result = func(*args, **kwargs)
                except HeatmiserResponseError as err:
                    lasterror = err
                    continue
                else:
                    return result
            raise HeatmiserResponseError("Failed after %i retries on %s"%(max_retries, str(lasterror)))
        return inner
    return wraps

class HeatmiserAdaptor(object):
    """Handles configuration serial port and provides low level read and write functions"""
    def __init__(self, setup):

        # Initialize setup and get settings
        self._setup = setup
        settings = self._setup.settings

        self.serport = serial.Serial()
        self.serport.bytesize = serial.EIGHTBITS #COM_SIZE
        self.serport.parity = serial.PARITY_NONE #COM_PARITY
        self.serport.stopbits = serial.STOPBITS_ONE #COM_STOP

        self.lastsendtime = None
        self.creationtime = time.time()

        self._update_settings(settings)

        self.lastreceivetime = self.creationtime - self.serport.COM_BUS_RESET_TIME # so that system will get on with sending straight away
        
        if self.auto_connect:
            self.connect()
        
    def __del__(self):
        self._disconnect()

    def _update_settings(self, settings):
        """Check settings and update if needed."""

        for name, value in settings['controller'].iteritems():
            setattr(self, name, value)

        # Configure serial settings after closing if required
        wasopen = False
        if self.serport.isOpen():
            wasopen = True
            self.serport.close() # close port

        for name, value in settings['serial'].iteritems():
            setattr(self.serport, name, value)

        if not self.serport.isOpen() and wasopen:
            try:
                self.serport.open()
            except serial.SerialException as err:
                logging.error("Could not open serial port %s: %s" % (self.serport.portstr, err))
                raise

### low level serial commands

    def connect(self):
        """If not open, open serial port and log settings"""
        if not self.serport.isOpen():
            try:
                self.serport.open()
            except serial.SerialException as err:
                logging.error("Could not open serial port %s: %s" % (self.serport.portstr, err))
                raise

            logging.info("Gen %s port opened"% (self.serport.portstr))
            logging.debug("Gen %s baud, %s bit, %s parity, with %s stopbits, timeout %s seconds" % (self.serport.baudrate, self.serport.bytesize, self.serport.parity, self.serport.stopbits, self.serport.timeout))
        else:
            logging.warn("Gen serial port was already open")
        
    def _disconnect(self):
        """check if serial port is open and if so close"""
        #shouldn't need to called directly because handled by destructor
        if self.serport.isOpen():
            self.serport.close() # close port
            logging.info("Gen serial port closed")
        else:
            logging.warn("Gen serial port was already closed")
            
    def _send_message(self, message):
        """Send message to serial port and log errors"""
        if not self.serport.isOpen():
            self.connect()

        #check time since last received to make sure bus has settled.
        waittime = self.serport.COM_BUS_RESET_TIME - (time.time() - self.lastreceivetime)
        if waittime > 0:
            logging.debug("Gen waiting before sending %.2f"% (waittime))
            time.sleep(waittime)
        
        # http://stackoverflow.com/questions/180606/how-do-i-convert-a-list-of-ascii-values-to-a-string-in-python
        string = ''.join(map(chr, message))

        try:
            self.serport.write(string)    # Write a string
        except serial.SerialTimeoutException as err:
            self.serport.close() #need to close so that isOpen works correctly.
            logging.warning("Write timeout error: %s, sending %s" % (err, ', '.join(str(x) for x in message)))
            raise
        except serial.SerialException as err:
            self.serport.close() #need to close so that isOpen works correctly.
            logging.warning("Write error: %s, sending %s" % (err, ', '.join(str(x) for x in message)))
            raise
        else:
            self.lastsendtime = time.strftime("%d %b %Y %H:%M:%S +0000", time.localtime(time.time())) #timezone is wrong
            logging.debug("Gen sent %s", ', '.join(str(x) for x in message))

    def _clear_input_buffer(self):
        """Clears input buffer
        
        Used after CRC check wrong; in case more data was sent than expected."""
    
        time.sleep(self.serport.COM_TIMEOUT) #wait for read timeout to ensure slave finished sending
        try:
            if self.serport.isOpen():
                self.serport.reset_input_buffer() #reset input buffer and dump any contents
            logging.warning("Input buffer cleared")
        except serial.SerialException:
            self.serport.close()
            logging.warning("Failed to clear input buffer")
            raise
                    
    def _receive_message(self, length=MAX_FRAME_RESP_LENGTH):
        """Receive message from serial port and log errors
        
        Uses two time outs, one on the first byte and another for full data"""
        if not self.serport.isOpen():
            self.connect()
        logging.debug("Gen listening for %d"%length)
        
        # Listen for the first byte
        timereadstart = time.time()
        self.serport.timeout = self.serport.COM_START_TIMEOUT #wait for start of response
        try:
            firstbyteread = self.serport.read(1)
        except serial.SerialException as err:
            #There is no new data from serial port (or port missing) (Doesn't include no response from stat)
            logging.warning("Gen serial port error: %s" % str(err))
            self.serport.close()
            raise
        else:
            timereadfirstbyte = time.time()-timereadstart
            logging.debug("Gen waited %.2fs for first byte"%timereadfirstbyte)
            if len(firstbyteread) == 0:
                raise HeatmiserResponseError("No Response")
            
            # Listen for the rest of the response
            self.serport.timeout = max(self.serport.COM_MIN_TIMEOUT, self.serport.COM_TIMEOUT - timereadfirstbyte) #wait for full time out for rest of response, but not less than COM_MIN_TIMEOUT)
            try:
                byteread = self.serport.read(length - 1)
            except serial.SerialException as err:
                #There is no new data from serial port (or port missing) (Doesn't include no response from stat)
                logging.warning("Gen serial port error: %s" % str(err))
                self.serport.close()
                raise

            #Convert back to array
            data = map(ord, firstbyteread) + map(ord, byteread)

            return data
        finally:
            self.serport.timeout = self.serport.COM_TIMEOUT #make sure timeout is reverted
            self.lastreceivetime = time.time() #record last read time. Used to manage bus settling.

### protocol functions
    
    @retryer(max_retries=3)
    def write_to_device(self, network_address, protocol, unique_address, length, payload):
        """Forms write frame and sends to serial link checking the acknowledgement"""
        #Payload must be list
        msg = framing.form_frame(network_address, protocol, self.my_master_addr,
                                 FUNC_WRITE, unique_address, length, payload)
        try:
            self._send_message(msg)
        except Exception:
            logging.warn("C%i writing to address, no message sent"%(network_address))
            raise
        else:
            logging.debug("C%i written to address %i length %i payload %s"%(network_address, unique_address, length, ', '.join(str(x) for x in payload)))
            if network_address == BROADCAST_ADDR:
                self.lastreceivetime = time.time() + self.serport.COM_SEND_MIN_TIME - self.serport.COM_BUS_RESET_TIME # if broadcasting force it to wait longer until next send
            else:
                response = self._receive_message(FRAME_WRITE_RESP_LENGTH)
                try:
                    framing.verify_write_ack(protocol, network_address, self.my_master_addr, response)
                except HeatmiserResponseErrorCRC:
                    self._clear_input_buffer()
                    raise
                    
    def min_time_between_reads(self):
        """Computes the minimum time that adaptor leaves between read commands"""
        return self.serport.COM_BUS_RESET_TIME

    @retryer(max_retries=2)
    def read_from_device(self, network_address, protocol, unique_start_address, expected_length, readall=False):
        """Forms read frame and sends to serial link checking the response"""
        if readall:
            msg = framing.form_read_frame(network_address, protocol, self.my_master_addr, DCB_START, RW_LENGTH_ALL)
            logging.debug("C %i read request to address %i length %i"%(network_address, DCB_START, RW_LENGTH_ALL))
        else:
            msg = framing.form_read_frame(network_address, protocol, self.my_master_addr, unique_start_address, expected_length)
            logging.debug("C %i read request to address %i length %i"%(network_address, unique_start_address, expected_length))
        
        try:
            self._send_message(msg)
        except:
            logging.warn("C%i address, read message not sent"%(network_address))
            raise
        else:
            time1 = time.time()

            try:
                response = self._receive_message(MIN_FRAME_READ_RESP_LENGTH + expected_length)
            except Exception as err:
                logging.warn("C%i read failed from address %i length %i due to %s"%(network_address, unique_start_address, expected_length, str(err)))
                raise
            else:
                logging.debug("C%i read in %.2f s from address %i length %i response %s"%(network_address, time.time()-time1, unique_start_address, expected_length, ', '.join(str(x) for x in response)))
            
                try:
                    framing.verify_response(protocol, network_address, self.my_master_addr, FUNC_READ, expected_length, response)
                except HeatmiserResponseErrorCRC:
                    self._clear_input_buffer()
                    raise
                return response[FR_CONTENTS:-CRC_LENGTH]

    def read_all_from_device(self, network_address, protocol, expected_length):
        """Forms read all frame using read_from_device"""
        return self.read_from_device(network_address, protocol, DCB_START, expected_length, True)
        

