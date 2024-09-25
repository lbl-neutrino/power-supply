# This program resets all of the register values from an AD7124-8 to
# their default settings, then tailors certain registers for our 
# application. A table is sent to an output file and the terminal 
# promt to confirm register settings
import time

# tabulate formats tabled output which we'll use to check register settings
from tabulate import tabulate

# An SPI (Serial Periphezral Interface bus) transports information to or 
# from the AD7124-8
import spidev
spi = spidev.SpiDev()           # abreviate spidev

######################################################################
# Define functions
######################################################################

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
    # set Ref source = REFIN1(+/-), gain = 16
    address = 0x19                    # register 25 is Config_0
    msg = [address + write*64, 0b0000_0001, 0b1110_0100] 
    spi.xfer2(msg)
    registers[address][3] = '- Gain = 16, bipolar OFF, buffers, REFIN1(+/-) -'

    # set the power mode in the ADC_CONTROL register
    address = 1                     # register 1 is ADC_CONTROL
    msg = [address+write*64, 0, 0b1100_0000] # Chooses power=full
    spi.xfer2(msg)
    registers[address][3] = '------ Power = Full ------'

# create and print out a table of register settings
def table_register_settings():

    for i in range(0,57):
        address = i                         # a register index
        reg_name = registers[i][0]          # register's name
        bits = registers[i][1]              # register's # bits
        reset_val = registers[i][2]         # register's reset value
        setting = registers[i][3]           # a string for registers setting

    # read each register's setting (based on it's number of bits)
    # and convert the setting to a decimal value
        if bits == 8:
            msg = [address+read*64, 0]
            result = spi.xfer2(msg)
            decimal_result = result[1]
        elif bits == 16: 
            msg = [address+read*64, 0, 0]
            result = spi.xfer2(msg)
            decimal_result = result[1]*(2**8) + result[2]
        elif bits ==24:
            msg = [address+read*64, 0, 0, 0]
            result = spi.xfer2(msg)
            decimal_result = result[1]*(2**16) + result[2]*(2**8) + result[3]
        else: print(f'Bits = {bits}. The only choices are 8, 16, or 24')

    # test to see if the register's settings equal the default setting
        if i==9: setting = " - enabled w setup0, pos=Ain0, neg=Ain1 -"
        elif (decimal_result == reset_val): setting = "default"
        elif i==6: 
            setting = "You encountered an error. See page 86 in datasheet"
            print(f"You encountered an error (error code = {result}). See"
                   " page 86 in datasheet to translate error code" )
    # create a table of register information
        row = [i, bits, reg_name, result, decimal_result, reset_val, setting]
        table.append(row)

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

######################################################################
# Main
######################################################################

time.sleep(1)

# initialize the register settings
init_registers()

# print out a table of register settings
table_register_settings()

# open the data file created in gui_larpix_monitor.py
#file1 = open(file_name, 'a')
#print(table, file=file1)
#print(tabulate(table, headers=["Reg", "Bits", "Channel", 
#        "Setting", "Decimal Setting", "Reset Value", 
#        "Register Setting"]), file=file1)

# close the data file
#file1.close()









