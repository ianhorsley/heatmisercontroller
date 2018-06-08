
[ serial ]
    baudrate = integer()
	timeout = integer(0, 32)
	write_timeout = integer(0, 32)
	
	COM_TIMEOUT = float(default=1) #time to wait for full response
	COM_START_TIMEOUT = float(default=0.1) #time to wait for start of response
	COM_MIN_TIMEOUT = float(default=0.1) # min remaining time after first byte read
	COM_SEND_MIN_TIME = float(default=1)  #minimum time between sending commands to a device (broadcast only??)
	COM_BUS_RESET_TIME = float(default=0.1)


[ devices ]
  [[ __many__ ]]
    address = integer(0, 32)
    displayorder = integer(0, 32, default=32)
    longname = string(max=25, default=)
    protocol = integer(default=3)
    expectedtype = string(default=prt_e_model)
    programmode = option('day','week',default='day')
    controlmode = option('auto','manual',default='auto')
    frosttemperature = integer(0, 32, default=10)