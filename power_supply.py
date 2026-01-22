from smbus import SMBus   # pmbus command library
#import math
import sys
import time
import csv
from datetime import datetime
import threading


#0x50 is slave address for 1010000 of A6 through A0 (see table 2 in pmbus manual)
addr = 0x50   #the default slave address = 1010000 = 0x50
mods = [1, 2, 3]


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
			


