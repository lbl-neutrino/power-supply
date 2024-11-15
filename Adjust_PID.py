from smbus import SMBus   # pmbus command library
import sys
import time
import csv
from datetime import datetime
import threading
import numpy as np
import larpix_monitor_vac_pressure as lmp
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.lines import Line2D
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
 #       if page not in self.valid_pages:
 #           raise ValueError(f"Invalid module page {page}.")
        self.bus.write_byte_data(self.address, 0x00, page)

    def set_voltage(self, page, voltage):                    #sets output voltage
        self.set_page(page)	
        exp = -8                                   #exponent typically used in CoolX series, pg 14 of manual, and exp value can be found using VOUT_MODE command
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

    def __init__(self, Kp=1.0, Ki=0.0, Kd=0.0, setpoint=400, sample_time = 1.0, output_limits=(0, 40), auto_mode=True, proportional_on_measurement=False, differential_on_measurement=True, error_map=None, time_fn=None, starting_output=0.0):
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
        self.integral_values = np.array([0] * 1000)
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
        self.update_integral(error)
        integral = self.Ki * self.integral
        #derivative term
        derivative = self.Kd * (error - self.last_error)
        #PID control output
        output = proportional + integral + derivative
        output = max(self.output_limits[0], min(output, self.output_limits[1]))
        #getting error for next calculation
        self.last_error = error
        return output

    def update_integral(self, current_value):
        self.integral_values = np.roll(self.integral_values, 1)
        self.integral_values[0] = current_value
        self.integral = np.sum(self.integral_values)




#Main function to manage PID control, real-time plotting of power, and temperature
def main():
    addr = 0x50
    power_supp = power_supply(addr)
    setpoint = 390 #this vlaue is in K, equals 215 C
    lmp.init_registers()
    #pid_controllers are the 3 RTD temps that are being used. This should be adjusted to 4 when we decide how to use 4th RTD
    pid_controllers = [PID(Kp=6.5, Ki=1.0, Kd=7.0, setpoint=setpoint), PID(Kp=1.0, Ki=1.0, Kd=1.0, setpoint=setpoint), PID(Kp=1.0, Ki=0.1, Kd=0.1, setpoint=setpoint)]
    # Identify the InfluxDB account name (org), password (token), InfluxDB portal (url), and the 
    # InfluxDB path for your piece of data (tagged with bucket, measurement and field)
    ORG = "lbl-neutrino"
    TOKEN = "-IkZYxHAAahMAM_11tBbmtxr3tKpF7gC4wMlRZgw2rW6Fm-Ifykrt8ZgOo3c_h2jUYD3hNSp5FHr_IqtuXlCgw=="
    URL = "http://labpix.lbl.gov:8086"
    bucket = "purifier-sensors"
    measurement = "purifier-sensors"
    # sign into the lbl account
    client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    # set up InfluxDB to accept data
    write_api = client.write_api(write_options=SYNCHRONOUS)
    # create a point (p) by: (i) assign a new or preexisting “measurement” name (in this example 
    # measurement was previously assigned as “larpix_slow_controls”), (ii) assign a new or 
    # pre-existing “field” name (in this example “level”) and (iii) identify the value you wish to push to 
    # influxDB (in this example your_value)

#    ts, T, V = [], [], []
    start_time = time.time()
    elapsed_time = 1.0
    while True:
 #       ax1.clear()
 #       ax2.clear()
#        ts.append(time.time())
 #       print(time.time())
        curr_time = time.time()
        temps = read_temps()
 #       print(time.time())
    #    for i in range(3):
        current_temp = temps[1]
#        T.append(current_temp)
        v = pid_controllers[2].update(current_temp)
        power_supp.set_voltage(1,v)
        voltages = power_supp.read_voltage(1)
        print(f'T = {current_temp} ; V = {voltages}')
        if curr_time - start_time >= elapsed_time:
            p = influxdb_client.Point(measurement).field("current_temp", current_temp)
        #try/except is used in case the InfluxDB write command times out. 
            try:
        # push the point p into the identified InfluxDB account. 
                write_api.write(bucket=bucket, org=ORG, record=p)
            except urllib3.exceptions.ReadTimeoutError:
                continue 
#        v = pid_controllers[2].update(current_temp)
#        print(time.time())
#        power_supp.set_voltage(3, v)
#        print(time.time())
#        voltages = power_supp.read_voltage(3)
#        V.append(v)
            p = influxdb_client.Point(measurement).field("voltages", voltages)
        #try/except is used in case the InfluxDB write command times out. 
            try:
         #push the point p into the identified InfluxDB account. 
                write_api.write(bucket=bucket, org=ORG, record=p)
            except urllib3.exceptions.ReadTimeoutError:
                continue
            start_time = curr_time
        
#        ax1.plot(ts, T, label='T')
#        ax2.plot(ts, V, label='V')
#        ax1.legend()
#        ax2.legend()
#        plt.tight_layout()
        #plt.show()
#        plt.savefig('test.png')
#        print(time.time())
#        print(f'T = {current_temp} ; V = {v}')
        time.sleep(0.1)
     #   plt.tight_layout()
      #  plt.show()

if __name__ == '__main__':
    main()        
        

