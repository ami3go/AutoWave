import os
import sys
import ctypes
from visatype import *
# dll = ctypes.cdll.LoadLibrary(r'C:\Program Files\IVI Foundation\IVI\Bin\Ag34410_64.dll')
# session = ViSession()
# resourceName = ctypes.create_string_buffer('1001C'.encode('windows-1251'))
# optionString = ctypes.create_string_buffer('Simulate=1,RangeCheck=1,QueryInstrStatus=0,Cache=1'.encode())
# channel = ctypes.create_string_buffer('CH1'.encode())
# dll.Ag34410_InitWithOptions("USB0::0x0957::0x0A07::MY48001027::0::INSTR", VI_TRUE, VI_TRUE, "Simulate=false, DriverSetup= Model=34410A", session);
# dll.Ag34410_Beeper()
# reading = 0
# print(dll.Ag34410_Read())


if __name__ == '__main__':
    dll_lib = ctypes.cdll.LoadLibrary(r"C:\\Users\\achestni\\Desktop\\PycharmProjects\\Libraries\\AutoWave\\src\\64bit\\AutoWave.dll")
    # dll_lib = ctypes.cdll.LoadLibrary(r"C:\\Users\\achestni\\Desktop\\PycharmProjects\\Libraries\\AutoWave\\src\\AutoWave.dll")
    session = ViSession()
    print(session)
    resource_name = "USB0::0x03EB::0x2065::_IDN_EM_TEST__AutoWave__0__5.10.08__2__0::INSTR"
    resourceName = ctypes.create_string_buffer(resource_name.encode('windows-1251'))
    print("resourceName:", resourceName)
    optionString = ctypes.create_string_buffer('Simulate=0,RangeCheck=1,QueryInstrStatus=0,Cache=1'.encode())
    channel = ctypes.create_string_buffer('CH1'.encode())
    txt_str = "Hello form python dll"
    disp_string = ctypes.create_string_buffer(txt_str.encode('windows-1251'))
    # dll_lib = ctypes.WinDLL(r"C:\\Users\\achestni\\Desktop\\PycharmProjects\\Libraries\\AutoWave\\src\\64bit\\AutoWave.dll")
    #autowave_lib = ctypes.cdll.LoadLibrary(r"C:\Users\achestni\Desktop\PycharmProjects\Libraries\AutoWave\src\AutoWave.dll")
    #autowave_lib = ctypes.cdll.LoadLibrary(r"AutoWave.dll")
    print(dll_lib)
    ST = dll_lib.AutoWave_init(resourceName, VI_TRUE, VI_TRUE, ctypes.pointer(session))
    # status = dll_lib.AutoWave_InitWithOptions(resourceName,  VI_TRUE, VI_TRUE, optionString, ctypes.pointer(session))
    # AutoWave_InitWithOptions (ViRsrc resourceName, ViBoolean IDQuery, ViBoolean resetDevice, ViConstString optionString, ViSession *newVi);
    dll_lib.AutoWave_SetDisplay(ctypes.pointer(session),disp_string)