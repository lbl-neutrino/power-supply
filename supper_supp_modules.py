from smbus import SMBus   # pmbus command library
import math
import signal
import sys
 
class power_supply:

	def __init__(self, addr, id=1):
		self.bus = SMBus(id)
		self.address = addr
		self.valid_pages = [1, 2, 3, 4] #valid modules to page to assuming 1,2,3 correspond to modules J1012, J1008, J1009 respectively. Should check and adjust as needed

	def set_page(self, page):
		if page not in self.valid_pages:
			raise ValueError(f"Invalid module page {page}.")
		self.bus.write_byte_data(self.address, 0x00, page)
		print(f"PAGE set to Module {page}")  

	def on_mod(self, page):                              #turns on power supply with 0x80
		self.bus.write_byte_data(self.address, 0x01, 0x80)  
		self.set_page(page)		
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

	def close(self):
		self.bus.close()

def Ctrl_C_signal(sig, frame):
	print("Ctrl+C input. Turning off power supply and closing...")
	if power_supp:
		power_supp.off_output()
		power_supp.close()
	sys.exit(0)

addr = 0x50   #the default slave address = 1010000 = 0x50
power_supp = power_supply(addr)
signal.signal(signal.SIGINT, Ctrl_C_signal)

#0x50 is slave address for 1010000 of A6 through A0 (see table 2 in pmbus manual)

if True:
	while True:
		user_input = input("type 'on' to turn on power supply, 'off' to turn off, 'set' to set the voltage, 'read' to read the voltage: ")
		
		if user_input in ['on', 'off', 'set', 'read']:
			page = int(input("Select module (1,2,4): "))

			if user_input == 'on':
				power_supp.on_mod(page)

			elif user_input == 'off':
				power_supp.off_mod(page)

			elif user_input == 'set':
				voltage = float(input("Enter the desired voltage: "))
				power_supp.set_voltage(page, voltage)
		
			elif user_input == 'read':
				voltage = power_supp.read_voltage(page)
				print(f"Current Voltage is {voltage} V")		

			elif user_input == 'quit':
				print("Exiting...")
				break

		else:	
			print("invalid command. enter 'on', 'off', or 'set'.")
	
#finally: 
#	power_supp.off_mod()
#	power_supp.close()







