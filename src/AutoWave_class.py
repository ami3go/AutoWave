
import time
import pyvisa # PyVisa info @ http://PyVisa.readthedocs.io/en/stable/


#It is recommended to use a minimum delay of 250ms between two commands
def delay(time_in_sec=0.25):
    time.sleep(time_in_sec)

## Number of Points to request
USER_REQUESTED_POINTS = 1000
    ## None of these scopes offer more than 8,000,000 points
    ## Setting this to 8000000 or more will ensure that the maximum number of available points is retrieved, though often less will come back.
    ## Average and High Resolution acquisition types have shallow memory depth, and thus acquiring waveforms in Normal acq. type and post processing for High Res. or repeated acqs. for Average is suggested if more points are desired.
    ## Asking for zero (0) points, a negative number of points, fewer than 100 points, or a non-integer number of points (100.1 -> error, but 100. or 100.0 is ok) will result in an error, specifically -222,"Data out of range"

## Initialization constants
INSTRUMENT_VISA_ADDRESS = 'USB0::0x0957::0x0A07::MY48001027::0::INSTR' # Get this from Keysight IO Libraries Connection Expert
    ## Note: sockets are not supported in this revision of the script (though it is possible), and PyVisa 1.8 does not support HiSlip, nor do these scopes.
    ## Note: USB transfers are generally fastest.
    ## Video: Connecting to Instruments Over LAN, USB, and GPIB in Keysight Connection Expert: https://youtu.be/sZz8bNHX5u4

GLOBAL_TOUT =  10 # IO time out in milliseconds



def range_check(val, min, max, val_name):
    if val > max:
        print(f"Wrong {val_name}: {val}. Max value should be less then {max}")
        val = max
    if val < min:
        print(f"Wrong {val_name}: {val}. Should be >= {min}")
        val = min
    return val



class com_interface:
    def __init__(self):
        # Commands Subsystem
        # this is the list of Subsystem commands
        # super(communicator, self).__init__(port="COM10",baudrate=115200, timeout=0.1)
        self.rm = pyvisa.ResourceManager()
        self.res_name = None
        print(self.rm)
        self.inst = None

        #self.app = self.rm.open_resource(INSTRUMENT_VISA_ADDRESS)

    def init(self):
        rm_list = self.rm.list_resources()
        i = 0
        for item in rm_list:
            if "AutoWave" in item:
                self.res_name = item
        self.inst = self.rm.open_resource(self.res_name)
        self.inst.set_visa_attribute(pyvisa.constants.VI_ATTR_SEND_END_EN, 1)
        self.inst.write_termination = ""
        print("Connected to: ", self.inst.query("*IDN?"))
        print("Protocol OFF: ",self.inst.query("*PRCL:OFF"))
        print(self.inst.query("*ECHO:ON"))


    def send(self, txt):
        # will put sending command here
        # print(f'Sending: {txt}')
        self.inst.write(txt)

    def query(self, cmd_srt):
        return_val = self.inst.query(cmd_str)
        return return_val

    def close(self):
        self.ser.close()
        self.ser = None

    def __get_staus_code(self, error_num):
        error_number = int(error_num)
        error_number = range_check(error_number,0, 13)
        status_code_array = ["stopped",
                             "ready",
                             "started",
                             "fail",
                             "fast",
                             "DSP not ok",
                             "break",
                             "not ready",
                             "finished",
                             "iterate",
                             "undefined",
                             "write to file",
                             "file processing", ]
        return status_code_array[error_number]







class req3:
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix

    def req(self):
        return self.cmd + "?"



class str3:
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix

    def str(self, ):
        return self.cmd


class str_and_req:
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix

    def str(self, ):
        return self.cmd

    def req(self):
        return self.cmd + "?"

class req_on_off(req3):
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix
        # self.req = req3(self.prefix)
        self.on = str3(self.prefix + "ON")
        self.off = str3(self.prefix + "OFF")



class dig_param:
    def __init__(self):
        self.cmd = None  # this value to be inherited for high order class
        self.max = None  # this value to be inherited for high order class
        self.min = None  # this value to be inherited for high order class

    def val(self, count=0):
        count = range_check(count, self.min, self.max, "MAX count")
        txt = f'{self.cmd} {count}'
        return txt

class dig_param3:
    def __init__(self, prefix, min, max):
        self.prefix = prefix
        self.cmd = self.prefix
        self.max = max
        self.min = min

    def val(self, count=0):
        count = range_check(count, self.min, self.max, "MAX count")
        txt = f'{self.cmd} {count}'
        return txt

class str_param3:
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix

    def path(self, str=""):
        txt = f'{self.cmd} {str}'
        return txt







class storage:
    def __init__(self):
        self.cmd = ""
        self.prefix = ""
        self.idn = req3("*IDN")
        self.reset = str3("*RST")
        self.go_to_local = str3("*GTL")
        self.echo = req_on_off("*ECHO:")
        self.reboot = str3("REB")
        self.protocol = req_on_off("*PRCL:")
        self.status = status()
        self.stop_test = str3("STOP")
        self.start_test = str3("START")
        self.break_test = str3("BREAK")
        self.mode = mode("MOD")
        self.setVoltage = set_voltage("VSET")
        self.setOffset = set_voltage("VOFS")
        self.sel_file = str_param3("SOUR SEGM")
        self.display = str_param3("DISP")
        self.set_date = str_param3("DAT")
        self.req_date = req3("DAT")
        self.file = file("")



class mode(req3):
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix
        # self.req = req3(self.prefix)
        self.gen = str3(self.prefix + ":GEN")
        self.rec = str3(self.prefix + ":REC")
        self.gen_and_rec = str3(self.prefix + ":GNRC")

class set_voltage():
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix
        # self.req = req3(self.prefix)
        self.out1 = dig_param3(self.prefix + ":OUT1", 0,60)
        self.out2 = dig_param3(self.prefix + ":OUT2", 0, 60)
        self.out3 = dig_param3(self.prefix + ":OUT3", 0, 60)
        self.out4 = dig_param3(self.prefix + ":OUT4", 0, 60)

class file():
    # Command   # Syntax # Description
    # SIZE      # SIZ?   # SIZ? <filePath>    # Ask for file size
    # TRANSMIT  # TRFL   # TRFL <filePath>    # Initialise a file download. (not sending the file) # Return ERR if the file already exists on target.
    #           # TRFL?  # TRFL? <filePath>   # Initialise a file upload. (not loading the file)            # Return ERR if the file doesn't exist on target
    # DELETE    # DEL    # DEL <filePath>     # Delete a file on target.    # Return ERR if the file doesn't exist
    # DIR?      # DIR?   # DIR? <dirPath>     # Get the absolute paths of default directory or the content of the give directory path
    # CHECK     # CKFL?  # CKFL? <filePath>   # Check if file exists on target (ex.: after download)
    #           # CKLF?  # CKLF? <FileName>   # Ask for duration, channels, events, trigger and master channel of a test file
    #           # CKFD?  # CKFD? <FileName>   # Ask for total duration, events of a test file
    #           # CKHD?  # CKHD? <filePath.dpt> # Save header from < filePath.dpt> under </home/ guest/LogFiles/header.hpt> (point file only)
    # FLNM?     # FLNM?  # FLNM? DUTM         # Get the file path of the DUT Events log file # FLNM? ERR  # Get the file path of process errors log file
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix
        self.delete = str_param3("DEL")
        self.get_dir_download = str3("DIR? DOWD")
        self.get_dir_record = str3("DIR? RECD")
        self.get_dir_upgrade = str3("DIR? UPGD")
        self.get_dir_upgrade = str3("DIR? LOGD")
        self.get_file_size = str_param3("SIZ?")
        self.file_transmit = str_param3("TRFL")
        self.file_upload = str_param3("TRFL?")
        self.check_file_exist = str_param3("CKFL?")
        self.check_file_details = str_param3("CKLF?")
        self.check_total_duration = str_param3("CKFD?")

class status:
    def __init__(self):
        print("INIT Status")
        self.cmd = "STAT?"
        self.prefix = "STAT?"
        self.sys_ver = str3(self.prefix + "SYST")
        self.read_mac = str3(self.prefix + "MAC")
        self.read_out1_status = str3(self.prefix + "OUT1")
        self.read_out2_status = str3(self.prefix + "OUT2")
        self.read_out3_status= str3(self.prefix + "OUT3")
        self.read_out4_status= str3(self.prefix + "OUT4")
        self.read_in1_status = str3(self.prefix + "IN1")
        self.read_in2_status = str3(self.prefix + "IN2")
        self.read_test_status = str3(self.prefix + "TEST")




if __name__ == '__main__':
    # dev = LOG_34970A()
    # dev.init("COM10")
    # dev.send("COM10 send")
    cmd = storage()
    print("")
    print("TOP LEVEL")
    print(cmd.idn.req())
    print(cmd.reset.str())
    print(cmd.echo.on.str())
    print(cmd.echo.req())
    print(cmd.echo.off.str())
    print(cmd.mode.req())
    print(cmd.mode.gen.str())
    print(cmd.setVoltage.out1.val(10.5))
    print(cmd.setVoltage.out4.val(10.5))
    print(cmd.setOffset.out1.val(2))
    print(cmd.file.get_file_size.path("txt.file"))