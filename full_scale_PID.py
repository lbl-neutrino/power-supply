from smbus import SMBus   # pmbus command library
import sys
import time
import csv
from datetime import datetime
import threading
import numpy as np
import larpix_monitor_vac_pressure as lmp
import matplotlib.pyplot as plt
# import python commands used to send data into InfluxDB
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
# urllib3 has functions to help with url timeout problems
import urllib3


def read_temps():
    temperatures = lmp.read_tempers()
    return temperatures
    
def twos_comp(val, bits):
    if (val & (1 << (bits - 1))) != 0:
        val = val - (1 << bits)
        return val

class power_supply:

    def __init__(self, addr, id=1):
        self.bus = SMBus(id)
        self.address = addr

    def set_page(self, page):
        self.bus.write_byte_data(self.address, 0x00, page)

    def set_voltage(self, page, voltage):                    #sets output voltage
        self.set_page(page)	
        exp = -8      #exponent typically used in CoolX series, pg 14 of manual, and exp value can be found using VOUT_MODE command
        vout_command = int(voltage * (2 ** -exp))  #converts voltage to format for PMBus
        self.bus.write_word_data(self.address, 0x21, vout_command)  #sends 16-bit voltage command to vout command (0x21)

    def read_power(self, page):
        self.set_page(page)
        voltage = self.read_voltage(page)
        current = self.read_current(page)
        power = current * voltage
        return power
    
    def read_voltage(self, page):
        self.set_page(page)
        exp = -8
        data = self.bus.read_word_data(self.address, 0x8B)
        voltage = data * (2 ** exp)
        return voltage

    def read_current(self, page):
        self.set_page(page)
        data = self.bus.read_word_data(self.address, 0x8C)
        exp = twos_comp(data // 2**11, 5)
        cur = data % 2**11
        current = cur * (2 ** exp)
        return current

class PID:

    def __init__(self, Kp=1.0, Ki=0.0, Kd=0.0, setpoint=488, sample_time = 1.0, output_limits=(0, 40), auto_mode=True, proportional_on_measurement=False, differential_on_measurement=True, error_map=None, time_fn=None, starting_output=0.0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.sample_time = sample_time
        self.output_limits = output_limits
        self.auto_mode=auto_mode
        self.proportional_on_measurement=proportional_on_measurement
        self.differential_on_measurement=differential_on_measurement
        self.error_map=error_map
        self.proportional=0
        self.integral=0
        self.derivative=0
        self.last_time=None
        self.last_error=0
        self.last_output=None
        self.last_input=None
        
    def update(self, current_value):
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
    
#Main function to manage PID control, real-time plotting of power, and temperature
def main():
    addr = 0x50
    power_supp = power_supply(addr)
    setpoint = 330 #this vlaue is in K, equals 215 C
    lmp.init_registers()
    #pid_controllers are the 3 RTD temps that are being used. This should be adjusted to 4 when we decide how to use 4th RTD
    pid_controllers = [PID(Kp=1.0, Ki=1.0, Kd=1.0, setpoint=setpoint), PID(Kp=1.0, Ki=1.0, Kd=1.0, setpoint=setpoint), PID(Kp=6.5, Ki=1., Kd=7.0, setpoint=setpoint)]
    # Identify the InfluxDB account name (org), password (token), InfluxDB portal (url), and the 
    # InfluxDB path for your piece of data (tagged with bucket, measurement and field)
    ORG = "lbl-neutrino"
    TOKEN = "-IkZYxHAAahMAM_11tBbmtxr3tKpF7gC4wMlRZgw2rW6Fm-Ifykrt8ZgOo3c_h2jUYD3hNSp5FHr_IqtuXlCgw=="
    URL = "http://labpix.dhcp.lbl.gov:8086"
    bucket = "purifier-sensors"
    measurement = “larpix_slow_controls”
    # sign into the lbl account
    client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    # set up InfluxDB to accept data
    write_api = client.write_api(write_options=SYNCHRONOUS)
    # create a point (p) by: (i) assign a new or preexisting “measurement” name (in this example 
    # measurement was previously assigned as “larpix_slow_controls”), (ii) assign a new or 
    # pre-existing “field” name (in this example “level”) and (iii) identify the value you wish to push to 
    # influxDB (in this example your_value)
    t_labels = ["t_sensor_1", "t_sensor_2", "t_sensor_3", "t_sensor_4"] 
    mod_labels = ["module_1","module_2","module_3"]
    record_time = time.time()
    record_pause = 1.0
    while True:
        temps = read_temps()
        curr_time = time.time()
        for i in range(3):
            current_temp = temps[i]
            v = pid_controllers[i].update(current_temp)
            power_supp.set_voltage(i+1, v)
            voltage = power_supp.read_voltage(i+1)
            print(f'RTD{i+1} = {current_temp}K ; Module{i+1} = {voltage}V')
        print(f'RTD4 = {temps[3]}K')

        if curr_time - record_time >= record_pause:
            for i in range(4):
                p = influxdb_client.Point(measurement).field(t_labels[i], temps[i])
        #try/except is used in case the InfluxDB write command times out. 
                try:
        # push the point p into the identified InfluxDB account. 
                    write_api.write(bucket=bucket, org=ORG, record=p)
                except urllib3.exceptions.ReadTimeoutError:
                    continue

            for i in range(3):
                voltage = power_supp.read_voltage(i+1)
                p = influxdb_client.Point(measurement).field(mod_labels[i], voltage)
        #try/except is used in case the InfluxDB write command times out. 
                try:
        # push the point p into the identified InfluxDB account. 
                    write_api.write(bucket=bucket, org=ORG, record=p)
                except urllib3.exceptions.ReadTimeoutError:
                    continue 

            record_time = curr_time #reset the time when data recorded to influx

        time.sleep(0.1)
        print(f'RTD{i+1} = {current_temp}K ; Module{i+1} = {voltage}V')
        
if __name__ == '__main__':
    main()      










