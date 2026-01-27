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

    
#Main function to manage PID control, real-time plotting of power, and temperature
def main():
    addr = 0x50
    power_supp = power_supply(addr)
    # Identify the InfluxDB account name (org), password (token), InfluxDB portal (url), and the 
    # InfluxDB path for your piece of data (tagged with bucket, measurement and field)
    lmp.init_registers()
    ORG = "lbl-neutrino"
    URL = "http://localhost:8086"
     
    TOKEN = "n0zRzLJ8R7aPGVmgQnnowHA0ADJuoleFp25maal7qDTXDsB3uK56ZxgLem-YrzvUpd0cr3m1Esqm9xVRabqLcA=="
    bucket = "purifier-sensors"
    measurement = "larpix_slow_controls"
    # sign into the lbl account
    client = influxdb_client.InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    # set up InfluxDB to accept data
    write_api = client.write_api(write_options=SYNCHRONOUS)
    # create a point (p) by: (i) assign a new or preexisting “measurement” name (in this example 
    # measurement was previously assigned as “larpix_slow_controls”), (ii) assign a new or 
    # pre-existing “field” name (in this example “level”) and (iii) identify the value you wish to push to 
    # influxDB (in this example your_value)
    t_labels = ["t_sensor_1", "t_sensor_2", "t_sensor_3", "t_sensor_4", "t_sensor_5"] 
    record_time = time.time()
    mod_labels_voltage = ["module_1_voltage","module_2_voltage","module_3_voltage"]
    mod_labels_current = ["module_1_current","module_2_current","module_3_current"]
    h = [3,0,1,2,0]
    while True:
        try:
            temps = read_temps()
        except:
            print(f'error reading temps')
            temps = read_temps()
        curr_time = time.time()
        
        for i in range(5):
            current_temp = temps[i]
            if h[i] > 0:
                try:
                    voltage = power_supp.read_voltage(h[i])
                except:
                    print('Error reading voltage')
                try:    
                    current = power_supp.read_current(h[i])
                    print(f'Module{h[i]} = {voltage}V , {current}A')
                except:
                    print(f'error reading voltage/current')
            print(f'RTD{i} = {current_temp}K')
        time.sleep(0.5)

        if True: #curr_time - record_time >= record_pause:
            for i in range(5):
                p = influxdb_client.Point(measurement).field(t_labels[i], temps[i])
        #try/except is used in case the InfluxDB write command times out. 
                try:
        # push the point p into the identified InfluxDB account. 
                    write_api.write(bucket=bucket, org=ORG, record=p)
                except urllib3.exceptions.ReadTimeoutError:
                    
                    print('!!!!! \nerror pushing temp measurement!!!')
                    continue

            for i in range(3):
                try:
                    voltage = power_supp.read_voltage(i+1)
                    p = influxdb_client.Point(measurement).field(mod_labels_voltage[i], voltage)
                except:
                    continue
        #try/except is used in case the InfluxDB write command times out. 
                try:
        # push the point p into the identified InfluxDB account. 
                    write_api.write(bucket=bucket, org=ORG, record=p)
                except urllib3.exceptions.ReadTimeoutError:
                    
                    print('!!!!! \nerror pushing voltage measurement!!!')
                    continue

            for i in range(3):
                try:
                    
                    current = power_supp.read_current(i+1)
                    p = influxdb_client.Point(measurement).field(mod_labels_current[i], current)
                except:
                    try:
                        current = power_supp.read_current(i+1)
                        p = influxdb_client.Point(measurement).field(mod_labels_current[i], current)
                    except:
                        pass
        #try/except is used in case the InfluxDB write command times out. 
                try:
        # push the point p into the identified InfluxDB account. 
                    write_api.write(bucket=bucket, org=ORG, record=p)
                except urllib3.exceptions.ReadTimeoutError:
                    
                    print('!!!!! \nerror pushing current measurement!!!')
                    continue
    time.sleep(0.1)
        
        
if __name__ == '__main__':
    main()      










