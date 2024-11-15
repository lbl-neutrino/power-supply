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

    def __init__(self, Kp=1.0, Ki=0.0, Kd=0.0, setpoint=488, sample_time = 1.0, output_limits=(0, 40), auto_mode=True, proportional_on_measurement=False, differential_on_measurement=True, error_map=None, time_fn=None, starting_output=0.0):
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
    
class Scope():
    def __init__(self, ax, maxt=10, dt=0.1, modules=3, title="Power of Modules", ylabel="Power (W)", legend_prefix="Module", ylim=(0,100)):
        self.ax = ax
        self.dt = dt
        self.maxt = maxt
        self.modules = modules
        self.tdata = np.array([])
        self.ydatas = [np.array([]) for _ in [1,2,3]]  
        self.t0 = time.perf_counter()
        self.colors = ['r', 'g', 'b']
        self.lines = [Line2D([], [], color=self.colors[i], label=f'{legend_prefix} {i+1}') for i in range(modules)]
        for line in self.lines:
            self.ax.add_line(line)
        self.ax.set_ylim(ylim)  
        self.ax.set_xlim(0, self.maxt)
        self.ax.set_title(title)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel(ylabel)
        self.ax.legend(loc='upper left')

    def update(self, data):
        t, values = data
        self.tdata = np.append(self.tdata, t)
        time_filter = self.tdata > (t - self.maxt)
        self.tdata = self.tdata[time_filter]
        for i, value in enumerate(values):
            self.ydatas[i] = np.append(self.ydatas[i], value)
            self.ydatas[i] = self.ydatas[i][time_filter]   
        for i, line in enumerate(self.lines):
            line.set_data(self.tdata, self.ydatas[i])
        self.ax.set_xlim(self.tdata[0], self.tdata[0] + self.maxt)
        self.ax.figure.canvas.draw()
        return self.lines
'''
#Emitter function for plotting power and temperature values
def emitter_power(pid_controllers, power_supply, modules=3):
    start_time = time.perf_counter()
    while True:
        t = time.perf_counter() - start_time
        powers = []
        for i in range(modules):
            current_temp = read_temps()[i]  # Reading current temperature
            power = pid_controllers[i].update(current_temp)
            power_supply.set_voltage(i + 1, power)
            powers.append(power)  # Collect power values for each module
        yield t, powers
'''

def emitter_power(power_supply):
    start_time = time.perf_counter()
    while True:
        t = time.perf_counter() - start_time
     #   powers = [power_supply.read_power(page=i + 1) for i in ]  #reads power from 3 modules
        powers = [power_supply.read_power(page=3)]
        yield t, powers        
        
def emitter_temp():
    start_time = time.perf_counter()
    while True:
        t = time.perf_counter() - start_time
        temps = read_temps()  #Directly get the current temperatures from RTDs
        yield t, temps

#Main function to manage PID control, real-time plotting of power, and temperature
def main():
    addr = 0x50
    power_supp = power_supply(addr)
    setpoint = 330 #this vlaue is in K, equals 215 C
    lmp.init_registers()
    #pid_controllers are the 3 RTD temps that are being used. This should be adjusted to 4 when we decide how to use 4th RTD
    pid_controllers = [PID(Kp=1.0, Ki=1.0, Kd=1.0, setpoint=setpoint), PID(Kp=1.0, Ki=1.0, Kd=1.0, setpoint=setpoint), PID(Kp=6.5, Ki=1., Kd=7.0, setpoint=setpoint)]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    #Create scope for power plot
#    power_scope = Scope(ax1, maxt=20, dt=0.1, modules=3, title="Power of Modules", ylabel="Power (W)", legend_prefix="Module", ylim=(0,100))
    #Create scope for temperature plot
#    temp_scope = Scope(ax2, maxt=20, dt=0.1, modules=3, title="Temperature of RTDs", ylabel="Temperature (K)", legend_prefix="RTD", ylim=(250,450))
    #Power and Temperature animations
#    power_ani = animation.FuncAnimation(fig, power_scope.update, emitter_power(power_supp), interval=100, blit=True)
#    temp_ani = animation.FuncAnimation(fig, temp_scope.update, emitter_temp(), interval=100, blit=True)
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
    
    ts, T, V = [], [], []
    while True:
        ax1.clear()
        ax2.clear()
        ts.append(time.time())
        temps = read_temps()
    #    for i in range(3):
        current_temp = temps[1]
        T.append(current_temp)
        p = influxdb_client.Point(measurement).field("temp", T)
        #try/except is used in case the InfluxDB write command times out. 
        try:
        # push the point p into the identified InfluxDB account. 
            write_api.write(bucket=bucket, org=ORG, record=p)
        except urllib3.exceptions.ReadTimeoutError:
            continue  
        v = pid_controllers[2].update(current_temp)
        power_supp.set_voltage(4, v)
        V.append(v)
        p = influxdb_client.Point(measurement).field("voltage", V)
        #try/except is used in case the InfluxDB write command times out. 
        try:
        # push the point p into the identified InfluxDB account. 
            write_api.write(bucket=bucket, org=ORG, record=p)
        except urllib3.exceptions.ReadTimeoutError:
            continue  
        ax1.plot(ts, T, label='T')
        ax2.plot(ts, V, label='V')
        ax1.legend()
        ax2.legend()
        plt.tight_layout()
        #plt.show()
        plt.savefig('test.png')
        time.sleep(1)
     #   plt.tight_layout()
      #  plt.show()
        print(f'T = {current_temp} ; V = {v}')
if __name__ == '__main__':
    main()        
        
        