from smbus import SMBus   # pmbus command library
#import math
import sys
import time
import csv
from datetime import datetime
import threading


def twos_comp(val, bits):
        if (val & (1 << (bits - 1))) != 0:
                val = val - (1 << bits)
        return val
 
class power_supply:

	def __init__(self, addr, id=1):
		self.bus = SMBus(id)
		self.address = addr
		self.valid_pages = [1, 2, 3, 4] #valid modules to page to assuming 1,2,3 correspond to modules J1012, J1008, J1009 respectively. Should check and adjust as needed

	def set_page(self, page):
		if page not in self.valid_pages:
			raise ValueError(f"Invalid module page {page}.")
		self.bus.write_byte_data(self.address, 0x00, page)
	#	print(f"PAGE set to Module {page}")  

	def on_mod(self, page):                              #turns on power supply with 0x80
		self.set_page(page)		
		self.bus.write_byte_data(self.address, 0x01, 0x80)  
		print(f"Module {page} is ON")

	def off_mod(self, page):                              #turns off power supply with 0x00
		self.set_page(page)
		self.bus.write_byte_data(self.address, 0x01, 0x00)  
		print(f"Module {page} is OFF")

	def set_voltage(self, page, voltage):                    #sets output voltage
		self.set_page(page)	
		exp = -8                                   #exponent typically used in CoolX series, pg 14 of manual, and exp value can be found using VOUT_MODE command
		vout_command = int(voltage * (2 ** -exp))  #converts voltage to format for PMBus
		self.bus.write_word_data(self.address, 0x21, vout_command)  #sends 16-bit voltage command to vout command (0x21)
		print(f"Voltage for Module {page} set to {voltage}V")

	def read_voltage(self, page):
		self.set_page(page)
		exp = -8
		data = self.bus.read_word_data(self.address, 0x8B)
		voltage = data * (2 ** exp)
		return voltage

	def read_temperature(self, page):
		self.set_page(page)
		data = self.bus.read_word_data(self.address, 0x8D) #reading from 0x8D whihc is temp1 (from manual)
		temp = data
		return temp

	def set_temp_fault_lim(self, page, limit):
		self.set_page(page)
		exp = 0
		temp_com = int(limit * (2 ** exp))
		self.bus.write_word_data(self.address, 0x4F, temp_com)

	def set_current_limit(self, page, current_limit):
		self.set_page(page)
		exp = -8
		current_val = int(current_limit * (2 ** -exp))
		self.bus.write_word_data(self.address, 0x24, current_val)

	def read_current(self, page):
		self.set_page(page)
		data = self.bus.read_word_data(self.address, 0x8C)
		exp = twos_comp( data // 2**11, 5 )
		cur = data % 2**11
		current = cur * (2 ** exp)
		return current

	def close(self):
		self.bus.close()

	def adjust_voltage(self, page, voltage, increment = 0.1):
		current_voltage = voltage
		self.set_voltage(page, current_voltage + increment)

	def read_power(self, page):
		self.set_page(page)
		voltage = self.read_voltage(page)
		current = self.read_current(page)
		power = current * voltage
		return power

import numpy as np
"""	
class power_adjust:

	def __init__(self, modules, sleep_dt=1, n_samples=20):
		addr = 0x50
		self.modules=modules
		self.sleep_dt = sleep_dt
		self.power_supp = power_supply(addr)
		self.power = {}
		for p in modules: self.power[p] = np.zeros(n_samples)
		
	def update(self):
		for page in modules:
			P = self.power_supp.read_power(page)
			self.power[page] = np.roll(power[page], -1)
			self.power[page][-1] = P 
		
	def integ(self):
		i={}
		for page in self.modules:
			i[page] = np.sum(self.temp[page] * self.sleep_dt))
		return i
		
	def curr(self):
		i={}
		for page in self.modules:
			i[page] = self.power[page][-1]
		return i
		
	def derr(self):
		i={}
		for page in self.modules:
			i[page] = np.mean( np.diff( self.powers[page] ) / self.sleep_dt )
		return i
		
	def control(self):
		while True:
			time.sleep(self.sleep_dt)
			self.update() # read new data point
			
			i, d, c = self.integ(), self.derr(), self.curr()
			
			self.set_new_power( i, d, c )
			"""
			
		
	
	

#def adjust_voltage(self, page, volt_inc = 0.1):
#	self.get_voltage
#	while True:
#		for module in modules:
#			voltage = power_supp.read_voltage(module)
#			if voltage < v_min:
#				current_v = power_supp.read_voltage(module)
#				self.set_voltage(page, self.read_voltage(page) + 2)
#			elif: voltage > v_max:
#				current_v = power_supp.read_voltage(module)
#				self.set_voltage(page, self.read_voltage(page) - 2)
#		time.sleep(5)

def mod_log(modules, filename, interval = 5):
	addr = 0x50
	power_supp = power_supply(addr)
	
	with open(filename, 'w', newline = '') as csvfile:
		csvwriter = csv.writer(csvfile)
		header = ["Time"]
		for page in modules:
			header.append(f"Module {page} Temp ")
			header.append(f"Module {page} Voltage ")
			header.append(f"Module {page} Current ")
			header.append(f"Module {page} Power ")
		csvwriter.writerow(header)
		try:
			while True:
				now = datetime.now()
				timestamp = now.strftime('%d-%m-%Y  %H:%M:%S')
				data = []
				for page in modules:
					temp = power_supp.read_temperature(page)
					voltage = power_supp.read_voltage(page)
					current = power_supp.read_current(page)
					power = power_supp.read_power(page)
					data.append(temp)
					data.append(voltage)
					data.append(current)
					data.append(power)
					#print(f"Module {page}: {temp} °C, {voltage} V, {current} A, {power} W")
				csvwriter.writerow([timestamp] + data)
				csvfile.flush()
				time.sleep(interval)
		except KeyboardInterrupt:
			power_supp.close()
			
#0x50 is slave address for 1010000 of A6 through A0 (see table 2 in pmbus manual)
addr = 0x50   #the default slave address = 1010000 = 0x50
power_supp = power_supply(addr)
#signal.signal(signal.SIGINT, Ctrl_C_signal)
mods = [1, 2, 3, 4]
log_file = "module_log.csv"	
#mod_log(mods, log_file, interval = 5)	
thread_log = threading.Thread(target = mod_log, args = (mods, log_file, 5))
thread_log.start()


try:
	while True:
		user_input = input("type 'on' to turn on power supply module, 'off' to turn off module, 'set volt' to set the voltage, 'set current' to set the current, 'read volt' to read the voltage, 'read temp' to read the temp, 'read power' to read the power, 'quit' to exit the program: ")
		
		if user_input in ['on', 'off', 'set volt', 'set current', 'read volt', 'read power', 'read temp', 'quit']:
			page = int(input("Select module (1,2,4): "))

			if user_input == 'on':
				power_supp.on_mod(page)

			elif user_input == 'off':
				power_supp.off_mod(page)

			elif user_input == 'set volt':
				voltage = float(input("Enter the desired voltage: "))
				power_supp.set_voltage(page, voltage)
		
			elif user_input == 'set current':
				current_limit = float(input("Enter the current limit: "))
				power_supp.set_current_limit(page, current_limit)		
		
			elif user_input == 'read volt':
				voltage = power_supp.read_voltage(page)
				print(f"Current Voltage is {voltage} V")		

			elif user_input == 'quit':
				print("Exiting...")
				break

			elif user_input == 'read temp':
				temp = power_supp.read_temperature(page)
				print(f"Current temp of module {page} is {temp} °C")
				
			elif user_input == 'read power':
				power = power_supp.read_power(page)
				print(f"Current temp of module {page} is {power} W")
				
		else:	
			print("invalid command. enter 'on', 'off', 'set volt', 'read volt', 'read temp', 'quit'.")

finally:  
	for page in power_supp.valid_pages:
		power_supp.off_mod(page)
	power_supp.close()






