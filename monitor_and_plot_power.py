from smbus import SMBus   # pmbus command library
import sys
import time
import csv
from datetime import datetime
import threading
import numpy as np


def read_power(self, page):
	self.set_page(page)
	voltage = self.read_voltage(page)
	current = self.read_current(page)
	power = current * voltage
	return power
	
def read_temps():
	return read_tempers()

#def adjust_power(module, power_supply, pid, current_temp):
#	power = pid.update(current_temp)
#	power_supply.set_voltage(module, power)
	
class power_supply:

	def __init__(self, addr, id=1):
		self.bus = SMBus(id)
		self.address = addr	

	def set_page(self, page):
		if page not in self.valid_pages:
			raise ValueError(f"Invalid module page {page}.")
		self.bus.write_byte_data(self.address, 0x00, page)
	#	print(f"PAGE set to Module {page}")
			
	def set_voltage(self, page, voltage):                    #sets output voltage
		self.set_page(page)	
		exp = -8                                   #exponent typically used in CoolX series, pg 14 of manual, and exp value can be found using VOUT_MODE command
		vout_command = int(voltage * (2 ** -exp))  #converts voltage to format for PMBus
		self.bus.write_word_data(self.address, 0x21, vout_command)  #sends 16-bit voltage command to vout command (0x21)


class PID:

    def __init__(self, Kp=1.0, Ki=1.0, Kd=1.0, setpoint=210, sample_time = 1.0, output_limits=(0, 100), auto_mode=True, proportional_on_measurement=False, differential_on_measurement=True, error_map=None, time_fn=None, starting_output=0.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.sample_time = sample_time
       # self.min_output_limit=None
        #self.max_output_limit=None
        self.output_limits = output_limits
        self.auto_mode=auto_mode
        self.proportional_on_measurement=proportional_on_measurement
        self.differential_on_measurement=differential_on_measurement
        self.error_map=error_map
        self.proportional=0
        self.integral=0
        self.derivative=0
        self.last_time=None
        self.last_error=None
        self.last_output=None
        self.last_input=None
        
	def update(self, current_value):

        '''if not self.auto_mode:
            return self._last_output

        now = self.time_fn()
        if dt is None:
            dt = now - self._last_time if (now - self._last_time) else 1e-16
        elif dt <= 0:
            raise ValueError('dt has negative value {}, must be positive'.format(dt))

        if self.sample_time is not None and dt < self.sample_time and self._last_output is not None:
            # Only update every sample_time seconds
            return self._last_output'''
        # Compute error terms (setpoint - measured temp)
        error = self.setpoint - current_value
        #proportional term
        proportional = self.Kp * error
        #integral term
        self.integral += error
		integral = self.Ki * self.integral
		#derivative term
		derivative = self.Kd * (error - self.last_error)
		#PID control output
        output = proportional + integral + derivative
        output = max(self.output_limits[0], min(output, self.output_limits[1]))
        #getting error for next calculation
        self.last_error = error		
		return output


def main():
	addr = 0x50
	power_supp = power_supply(addr)
	setpoint = 215
	pid_controllers = [PID, PID, PID]
	while True:
		temps = read_temps()
		for i in range(3):
			current_temps = temps[i]
			power = pid_controllers[i].update(current_temps)
			power_supp.set_voltage(i + 1, power)
		time.sleep(1)

main()



