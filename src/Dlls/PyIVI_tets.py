import ctypes
from visatype import *
dll = ctypes.cdll.LoadLibrary(r'C:\Program Files\IVI Foundation\IVI\Bin\Ag34410_64.dll')
session = ViSession()
resourceName = ctypes.create_string_buffer('1001C'.encode('windows-1251'))
optionString = ctypes.create_string_buffer('Simulate=1,RangeCheck=1,QueryInstrStatus=0,Cache=1'.encode())
channel = ctypes.create_string_buffer('CH1'.encode())
dll.Ag34410_InitWithOptions("USB0::0x0957::0x0A07::MY48001027::0::INSTR", VI_TRUE, VI_TRUE, "Simulate=false, DriverSetup= Model=34410A", session);
dll.Ag34410_Beeper()
reading = 0
print(dll.Ag34410_Read())

