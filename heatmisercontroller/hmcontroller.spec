[ setup ]
  retry_time_interval = integer(default = 5)
  check_time_interval = integer(default = 1)

[ controller ]
  auto_connect = boolean(default = True)
  write_max_retries = integer()
  read_max_retries = integer()
  my_master_addr = integer()

[ serial ]
  baudrate = integer()
	timeout = integer(0, 32)
	write_timeout = integer(0, 32)

	
	COM_TIMEOUT = float(default=1) #time to wait for full response
	COM_START_TIMEOUT = float(default=0.1) #time to wait for start of response
	COM_MIN_TIMEOUT = float(default=0.1) # min remaining time after first byte read
	COM_SEND_MIN_TIME = float(default=1)  #minimum time between sending commands to a device (broadcast only??)
	COM_BUS_RESET_TIME = float(default=0.1)

[ devicesgeneral ]
  autoreadall = boolean(default = True)
  autocorrectime = boolean(default = True)
  max_age_variables = integer(default = 60) #variables like holidaymins, etc.
  max_age_time = integer(default = 86400) #time tends to drift very slowly, so it shouldn't need checking very often
  max_age_temp = integer(default = 10) #temperature is something that might be sampled very regularly
  
[ devices ]
  [[ __many__ ]]
    address = integer(0, 32)
    display_order = integer(0, 32, default=32)
    long_name = string(max=25, default=)
    protocol = integer(default=3)
    expected_model = string(default=prt_e_model)
    expected_prog_mode = option('day','week',default='day')
    control_mode = option('auto','manual',default='auto')
    frost_temperature = integer(0, 32, default=10)