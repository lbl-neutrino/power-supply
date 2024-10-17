
import numpy as np
# An SPI (Serial Peripheral Interface bus) transports information to or 
# from the AD7124-8 (temperature sensors)
import spidev
spi = spidev.SpiDev()           # abbreviate spidev
import time
import convert_resistance_to_temperature as ct
# tabulate formats tabled output which we'll use to check register settings
from tabulate import tabulate

# set up the spi (i.e. the mechanism to communicate with the device)
def set_up_spi():

    bus = 0                         # only SPI bus 0 is available
    device = 0                      # chip select pin (either 0 or 1)
    spi.open(bus, device)           # open the specified connection
    spi.max_speed_hz = 50000       # set SPI speed
    spi.mode = 3 # Mode 3 samples on falling edge, shifts out on rising edge

# set the AD7124-8 regsiters for our purposes
def init_registers():

    # set the data rate in the filter_0 register
    address = 0x21                     # register 33 is filter_0
    if data_rate == 'high':            # sets the data rate for setup0
        msg = [address+write*64, 0, 0, 1] 
        registers[address][3] = '- high data rate = 19k Samples/second -'
    elif data_rate == 'medium':
        msg = [address+write*64, 0, 0, 0b0111_1000]
        registers[address][3] = '- medium data rate = 160 Samples/sec --'
    elif data_rate == 'low':
        msg = [address+write*64, 0, 0, 0b1111_1111]
        registers[address][3] = '- low data rate = 9.4k Samples/sec -'
    else:
        registers[address][3] = f'data_rate setting ({data_rate}) was not a valid choice'
    spi.xfer2(msg)

    # enable Channel 0: Ain1 (positive) Ain0 (negative): Cryo Top 
    address = 0x9                         # address 9 is channel 0
    msg = [address + write*64, 0b1000_0000, 0b0010_0000]
    spi.xfer2(msg)
    registers[address][3] = '- enabled w setup0, pos=Ain1, neg=Ain0 -'

    # set current out to Ain7 using an excitation current of 50 micro-A
    address = 3                     # register 3 is IO_Control_1
    msg = [address + write*64, 0, 0b0000_0001, 0b0000_0111]
    spi.xfer2(msg)
    registers[address][3] = f'- Ain7 output, ex current = 50 microA -'

    # set  bipolar OFF, enable buffers for Ain(+/-) and Refin(+/-), 
    # set Ref source = REFIN1(+/-), gain = 8
    address = 0x19                    # register 25 is Config_0
    msg = [address + write*64, 0b0000_0001, 0b1110_0011] 
    spi.xfer2(msg)
    registers[address][3] = '- Gain = 8, bipolar OFF, buffers, REFIN1(+/-) -'

    # set the power mode in the ADC_CONTROL register
    address = 1                     # register 1 is ADC_CONTROL
    msg = [address+write*64, 0, 0b1100_0000] # Chooses power=full
    spi.xfer2(msg)
    registers[address][3] = '------ Power = Full ------'


######################################################################
# Initialize global variables
######################################################################    

#global file_name

test = True
table = []                  # table of register settings
read= 1                     # messages sent to the communications register
write = 0
data_rate = 'low'          # choices are 'high', 'medium' or 'low'
                            # (samples per second) read from the ADC

# list of AD7124-8 register names, number of bits, reset values, and note
registers = [
    ["Status",8, 0x00, ''],
    ["ADC Control", 16, 0x0000, ''],
    ["Data", 24, 0x000000, ''],
    ["IO Control 1", 24, 0x000000, ''],
    ["IO Control 2", 16, 0x0000, ''],
    ["ID", 8, 0x17, ''],
    ["Error", 24, 0x000000, ''],
    ["ERROR_EN", 24, 0x000040, ''],
    ["MCLK_COUNT", 8, 0x00, ''],
    ["CHANNEL_0", 16, 0x8001, ''],
    ["CHANNEL_1", 16, 0x0001, ''],
    ["CHANNEL_2", 16, 0x0001, ''],
    ["CHANNEL_3", 16, 0x0001, ''],
    ["CHANNEL_4", 16, 0x0001, ''],
    ["CHANNEL_5", 16, 0x0001, ''],
    ["CHANNEL_6", 16, 0x0001, ''],
    ["CHANNEL_7", 16, 0x0001, ''],
    ["CHANNEL_8", 16, 0x0001, ''],
    ["CHANNEL_9", 16, 0x0001, ''],
    ["CHANNEL_10", 16, 0x0001, ''],
    ["CHANNEL_11", 16, 0x0001, ''],
    ["CHANNEL_12", 16, 0x0001, ''],
    ["CHANNEL_13", 16, 0x0001, ''],
    ["CHANNEL_14", 16, 0x0001, ''],
    ["CHANNEL_15", 16, 0x0001, ''],
    ["CONFIG_0", 16, 0x0860, ''],
    ["CONFIG_1", 16, 0x0860, ''],
    ["CONFIG_2", 16, 0x0860, ''],
    ["CONFIG_3", 16, 0x0860, ''],
    ["CONFIG_4", 16, 0x0860, ''],
    ["CONFIG_5", 16, 0x0860, ''],
    ["CONFIG_6", 16, 0x0860, ''],
    ["CONFIG_7", 16, 0x0860, ''],
    ["FILTER_0", 24, 0x060180, ''],
    ["FILTER_1", 24, 0x060180, ''],
    ["FILTER_2", 24, 0x060180, ''],
    ["FILTER_3", 24, 0x060180, ''],
    ["FILTER_4", 24, 0x060180, ''],
    ["FILTER_5", 24, 0x060180, ''],
    ["FILTER_6", 24, 0x060180, ''],
    ["FILTER_7", 24, 0x060180, ''],
    ["OFFSET_0", 24, 0x800000, ''],
    ["OFFSET_1", 24, 0x800000, ''],
    ["OFFSET_2", 24, 0x800000, ''],
    ["OFFSET_3", 24, 0x800000, ''],
    ["OFFSET_4", 24, 0x800000, ''],
    ["OFFSET_5", 24, 0x800000, ''],
    ["OFFSET_6", 24, 0x800000, ''],
    ["OFFSET_7", 24, 0x800000, ''],
    ["GAIN_0", 24, 0x000001, ''],
    ["GAIN_1", 24, 0x000001, ''],
    ["GAIN_2", 24, 0x000001, ''],
    ["GAIN_3", 24, 0x000001, ''],
    ["GAIN_4", 24, 0x000001, ''],
    ["GAIN_5", 24, 0x000001, ''],
    ["GAIN_6", 24, 0x000001, ''],
    ["GAIN_7", 24, 0x000001, '']]

######################################################################
# Initialize global assets
######################################################################

# set up the ability to read and write to the registers. Reset all registers
set_up_spi()

# reset all adc registers to their default values
msg = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
spi.xfer2(msg)



# get a new temperature reading from the ADC
def read_tempers():

    # initialize variables
    write = 0
    read = 1            # command to read from ADC
    address_status = 0  # ADC status is available on register 0
    address_data = 2	# ADC Data is available on register 2
    address_ch0 = 9
    decimal_result = 0
    temperatures = [0,0,0,0]

    # 4 sensor register settings: enable, Ain positive, Ain negative
    sensor_inputs = [0b1000_0011, # sensor pin 3-4 
                     0b0110_0010,  # pin 2-3
                     0b0100_0001,  # pin 1-2
                     0b0010_0000]  # pin 0-1

    # used to calibrate ADC readings to degree C
    adc_910 =  11054300               # ADC reading for 920 Ohm
    adc_429 =  1660520              # ADC reading for 429 Ohm

    for sensor in range(0,4):

        # enable channel 0 to read the desired sensor's inputs
        msg = [address_ch0 + write*64, 0b1000_0000, sensor_inputs[sensor]]
        spi.xfer2(msg)

        # read the status register
        msg = [address_status + read*64, 0]
        status_result = spi.xfer2(msg)

        # keep reading the status register until there is new data 
        # (i.e. highest bit=0)
        while status_result[1] > 0b0111_111:
            status_result = spi.xfer2(msg)
            
        # read the new adc measurement
        msg = [address_data + read*64, 0, 0, 0]
        data_result = spi.xfer2(msg)
        
        # convert the 24 bit adc reading into a decimal value
        decimal_result = data_result[1]*(2**16) + data_result[2]*(2**8) + data_result[3]
        temperatures[sensor]=decimal_result
        # Determine resistance for the sensor reading
        resistance = 199.5 + (29.98 - 199.5) * (decimal_result - adc_910) / (adc_429 - adc_910)
        
        # Convert resistance to temperature in Celcius (via interpolation
        # function from convert_resistance_to_termperature.py, and 
        # convert celcius to kelvin. First check range(19,390) which 
        # is necessary for the conversion function to work
        if resistance <= 19 or resistance >= 390:
            # this eroneous value is intended to alert user to a problem
            temperatures[sensor] = float(0.00)
            
        else:
            temperatures[sensor] = ct.interp_resist_to_temp(resistance) + 273.15

    return temperatures



