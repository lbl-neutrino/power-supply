from smbus import SMBus   # pmbus command library
#import math
import sys
import time
import csv
from datetime import datetime
import threading
import numpy as np


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
