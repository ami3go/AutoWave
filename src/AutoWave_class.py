import time
import pyvisa  # PyVisa info @ http://PyVisa.readthedocs.io/en/stable/
import datetime


# It is recommended to use a minimum delay of 250ms between two commands
def delay(time_in_sec=0.25):
    """
    Time delay based on time.sleep().
    It is recommended to use a minimum delay of 250ms between two GPIB commands

    :param time_in_sec: delay time
    :return: None
    """
    time.sleep(time_in_sec)


def range_check(val, min, max, val_name):
    """
    Checking if the value inside the range  min>=val<=max

    :param val: input value
    :param min: minimal value to check with
    :param max: maxinum value to check with
    :param val_name: name of parameter. In case of out of range event the name will be printer to help find an error
    :type val_name: string
    :return: return Val if in the range, val=max if >=max, val=min if val<=min
    """
    if val > max:
        print(f"Wrong {val_name}: {val}. Max value should be less then {max}")
        val = max
    if val < min:
        print(f"Wrong {val_name}: {val}. Should be >= {min}")
        val = min
    return val

def str2dec_array(txt):
    """
    Converting string to decimal array.

    :param txt: text sting input
    :return: decimal array
    """
    cmd = []  # array for formatted command
    for item in txt:
        cmd.append(ord(item))
    return cmd

def dec_array2check_sum(dec_array):
    """
    Calculate a check sum for decimal array

    :param dec_array: binary array
    :return: calclulated check summ according to documentation
    """
    check_sum = sum(dec_array) & 0x00FF
    if check_sum <= 0x20:
        check_sum += 0x20
    return check_sum

def str2check_sum(txt):
    """
    Calculate a check sum for text string

    :param txt: input test string
    :type txt: str
    :return: Check sum. If (sum & 0x00FF) less then 0x20. Return will be Sum + 0x20
    """
    array = str2dec_array(txt)
    return dec_array2check_sum(array)


class com_interface:
    """
    class for communicating with Autowave generator using GPIB bus
    """
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.res_name = None
        print(self.rm) # check what kind of lib is used for VISA
        self.inst = None
        self.download_dir = None
        self.start_time = None
        self.cmd = storage()  # init command structure

        # self.app = self.rm.open_resource(INSTRUMENT_VISA_ADDRESS)

    def init(self):
        """
        The methods will automatically look at the list of available device and search for AutoWave generator
        """

        rm_list = self.rm.list_resources()
        i = 0
        for item in rm_list:
            if "AutoWave" in item:
                self.res_name = item
        self.inst = self.rm.open_resource(self.res_name)
        self.inst.set_visa_attribute(pyvisa.constants.VI_ATTR_SEND_END_EN, 1)
        self.inst.write_termination = ""
        self.inst.timeout = 2000  # timeout in ms
        # the commands below are not crash safe
        # in case of something will get wrong init() will crash
        # print("Connected to: ", self.inst.query("*IDN?"))
        print("Connected to: ", self.inst.query(self.cmd.idn.req()))
        delay()
        self.inst.query(self.cmd.echo.on.str())
        delay()
        self.inst.query(self.cmd.protocol.on.str())
        delay()
        # move cmd.mode.gen.str() for stable work
        # in manual it should be at "file_run"
        print("Set generator mode: ", self.pquery(self.cmd.mode.gen.str()))
        delay()


    def send(self, txt):
        """
         Sending the regula VISA string

         :param txt: VISA string command
         :return: None
         """

        self.inst.write(txt)
        delay()

    def query(self, cmd_str):
        """
        Query the regula VISA string. It will resend 10 time in case of any error

        :param cmd_str: VISA string command
        :type cmd_str: str

        :return: VISA string replay
        """
        for i in range(10):
            try:
                # debug print to check how may tries
                # print("trying",i)
                return_str = self.inst.query(cmd_str)
                delay()  # regular delay according to datasheet before next command
                return return_str

            except Exception as e:
                print(f"query[{i}]: {cmd_str}, Reply: {return_str}, Error: {e}")
                delay(5)

    def psend(self, txt_cmd):
        """
        Sending protocol command: STX=0x02 + Command + ETX=0x03 + CheckSum
        :param txt_cmd: VISA string command
        :type txt_cmd: str
        :return: None
        """
        cmd = str2dec_array(txt_cmd)
        cmd.insert(0, 2)  # insertion of STX=0x02 to a first place
        cmd.append(3)  # termination message with ETX=0x03
        cmd.append(str2check_sum(txt_cmd))  # adding check sum at the end
        # print(f"protocol cmd: {cmd}")
        # print(bytes(cmd))
        self.inst.write_raw(bytes(cmd))
        delay()

    def pquery(self, cmd_str, err_check=False, p_check=True):
        '''
        Delay and retry in cause of old device with slow processing time
        In case of error a 10 attempts will be made before everything will get crashed.

        :param cmd_str: VISA string command
        :type cmd_str: str
        :return: instument replay string
        :rtype: str
        '''
        for i in range(10):
            try:
                # debug print to check how may tries
                # print("trying",i)
                self.psend(cmd_str)
                delay()  # regular delay according to datasheet before next command
                return_raw = None
                return_raw = self.inst.read_raw()
                # print("read_raw:",return_raw )
                # check return line
                if len(return_raw) == 1:
                    if return_raw == b'\x19':
                        raise Exception("Device: BUSY")
                    if return_raw == b'\x16':
                        raise Exception("Device: NOT READY")
                    if return_raw == b'\x15':
                        raise Exception("Device: Negative ACKnowledge")
                if p_check is True:
                    # TBD: require to add check sum check
                    check_sum = dec_array2check_sum(return_raw[1:-2])
                    if (return_raw[0] == 0x02) and (return_raw[-2] == 0x03) and (check_sum == return_raw[-1]):
                        # #  typical val =  b'\x02TRIG:GEN 1\x03\x9b'
                        # #  x02 - start symbol
                        # #  x03 - stop symbol
                        # #  x9b - check sum
                        # print("p_check:", return_raw)
                        return_raw = return_raw[1:-2]
                        return_str = return_raw.decode("utf-8")
                        if err_check is True:
                            if (return_str.find(":ERR") != -1):
                                raise Exception("Error in replay")
                        return return_str

                    else:
                        raise Exception("Error in start(0x02)/end(0x03) terminator")


                return return_raw.decode("utf-8")

            except Exception as e:
                print(f"Pquery[{i}]: {cmd_str}, Reply: {return_raw}, Error: {e}")
                delay(5)




    def close(self):
        """
        Close the VISA connection

        :return: None
        """
        self.inst.close()

    def run_test_file(self, file_name):
        """
        Run a test file, start generate a test signal form file
        Note: File should be uploaded to device first. After that you may run it form script.
        Use EM test PC software to uploaded test to device.

        :param file_name: File name on Autowave device
        :return: None
        """
        txt = self.pquery(self.cmd.file.get_dir_download.str(), 1)
        self.download_dir = txt.replace("DIR DOWD:","")
        self.download_dir = self.download_dir + "/"
        # print(self.pquery(self.cmd.file.TRLF.path(self.download_dir + file_name), True, True))
        # delay(5)
        # print(self.pquery(self.cmd.file.TRLF_req.path(self.download_dir + file_name)))
        # delay(5)
        # print(self.pquery(self.cmd.mode.gen.str()))
        # delay(1)
        print(self.pquery(self.cmd.file.select.path(file_name), True))
        delay(1)
        print(self.pquery(self.cmd.trigGen.manual_start.str(), True))
        delay(1)
        print(self.pquery(self.cmd.start_test.str(), True))
        delay(1)
        print(self.pquery(self.cmd.start_test.str(), True))
        delay(1)



    def get_test_time(self, file_name, echo=True):
        """
        Ask for duration, channels, events, trigger and master channel of a test file.
        Typical response: "CKLF Ford ES-XW7T-1A278-AC - CI210 -.dsg:31.000000, 1, 1, 3, 0, 0;"
        # Protocol is not working for this command
        # check the start and end termination leads to en error

        :param file_name: Name of file located on AutoWave device
        :type file_name: str
        :param echo: Enable output in terminal
        :type echo: bool
        :return:
        """

        txt = self.pquery(self.cmd.file.check_details.path(file_name), True, True)
        print("file:", txt)
        txt = self.pquery(self.cmd.file.check_details.path(file_name), False, True)
        print("file:", txt)
        if txt != None:
            txt = txt.split(":")  # get text and digits separated
            txt = txt[1]  # select only digits array
            txt = txt.split(",")  # separate digits
            time_in_sec = float(txt[0])  # selec first digit
            if echo == True:
                print(f"Test Duration: {datetime.timedelta(seconds=round(time_in_sec))} , "
                      f"File:{file_name}, Channel:{txt[1]}, "
                      f"Events:{txt[2]}")
        else:
            # !! ONLY FOR DEBUG
            time_in_sec = 360
        return time_in_sec

    def check_test_status(self):
        # responce [['OUT1:', 'finished', '8'], ['OUT2:', 'finished', '8'], ['OUT3:', 'finished', '8'], ['OUT4:', 'finished', '8'], ['IN 1:', 'fast', '4'], ['IN 1:', 'fast', '4'], ['DUT:', 'stopped', '0']]
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
                             "not defined",
                             "file processing", ]
        return_val = [  ["OUT1:", "", ""],
                        ["OUT2:", "", ""],
                        ["OUT3:", "", ""],
                        ["OUT4:", "", ""],
                        ["IN 1:", "", ""],
                        ["IN 1:", "", ""],
                        [" DUT:", "", ""],
        ]
        #replay "STAT TEST:13,13,13,13,13,13,0"
        status_rep = self.pquery(self.cmd.status.read_test_status.str())
        print("check_test_status :", status_rep)
        if status_rep != None:
            st = status_rep.replace("STAT TEST:", "")
            st = st.split(",")
            # print("st:", st)
            i = 0
            for code in st:
                return_val[i][1] = code
                return_val[i][2] = status_code_array[int(code)]
                i = i + 1
            # return status_rep
            return return_val
        else:
            return "No replay"

    def disconnect(self):
        self.send(self.cmd.go_to_local.str())

    def reboot(self):
        self.send(self.cmd.reboot.str())

    def set_dc_voltage(self, volt=13.5, ch=1):
        """
        Enable DC voltage in IDE state, when test is not running.

        :param volt: target voltage in rage of 0V - 60V.
        :param ch: number of output channel. Check that VDS200 is connected to it .
        :type ch: int.
        :return: None.
        """
        ch = int(range_check(ch, 1, 4, "select channel"))
        volt = range_check(volt, 0, 60, "Setting DC voltage")
        if ch == 1:
            self.psend(self.cmd.setVoltage.out1.val(volt))
        elif ch == 2:
            self.psend(self.cmd.setVoltage.out2.val(volt))
        elif ch == 3:
            self.psend(self.cmd.setVoltage.out3.val(volt))
        elif ch == 4:
            self.psend(self.cmd.setVoltage.out4.val(volt))
        else:
            raise Exception("Something went wrong. Func: set_dc_voltage(self, volt, ch=1) ")

    def set_dc_offset(self, volt=0, ch=1):
        """
        Enable offset for DC voltage.

        :param volt: target voltage in rage of 0V - 60V.
        :param ch: number of output channel. Check that VDS200 is connected to it .
        :type ch: int.
        :return: None.
        """
        ch = int(range_check(ch, 1, 4, "select channel"))
        volt = range_check(volt, -60, 60, "Offset voltage ")
        if ch == 1:
            self.psend(self.cmd.setOffset.out1.val(volt))
        elif ch == 2:
            self.psend(self.cmd.setOffset.out2.val(volt))
        elif ch == 3:
            self.psend(self.cmd.setOffset.out3.val(volt))
        elif ch == 4:
            self.psend(self.cmd.setOffset.out4.val(volt))
        else:
            raise Exception("Something went wrong. Func: sset_dc_offset(self, volt, ch=1) ")

    def got_to_local(self):
        self.psend(self.cmd.go_to_local.str())

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


# class str_and_req:
#     def __init__(self, prefix):
#         self.prefix = prefix
#         self.cmd = self.prefix
#
#     def str(self, ):
#         return self.cmd
#
#     def req(self):
#         return self.cmd + "?"


class req_on_off(req3):
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix
        # self.req = req3(self.prefix)
        self.on = str3(self.prefix + "ON")
        self.off = str3(self.prefix + "OFF")


# class dig_param:
#     def __init__(self):
#         self.cmd = None  # this value to be inherited for high order class
#         self.max = None  # this value to be inherited for high order class
#         self.min = None  # this value to be inherited for high order class
#
#     def val(self, count=0):
#         count = range_check(count, self.min, self.max, "MAX count")
#         txt = f'{self.cmd} {count}'
#         return txt


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
        self.start_test = str3("STAR")
        self.break_test = str3("BREAK")
        self.mode = mode("MOD")
        self.setVoltage = set_voltage("VSET")
        self.setOffset = set_voltage("VOFS")
        self.display = str_param3("DISP")
        self.set_date = str_param3("DAT")
        self.req_date = req3("DAT")
        self.file = file("")
        self.trigGen = trig_gen("")


class mode(req3):
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix
        # self.req = req3(self.prefix)
        self.gen = str3(self.prefix + " GEN")
        self.rec = str3(self.prefix + " REC")
        self.gen_and_rec = str3(self.prefix + " GNRC")


class trig_gen():
    def __init__(self, prefix):
        self.prefix = "TRIG:GEN"
        self.cmd = self.prefix
        self.off = str3(self.prefix + " 0")
        self.manual_start = str3(self.prefix + " 1")
        self.trigIn_start = str3(self.prefix + " 2")
        self.auto = str3(self.prefix + " 3")
        self.manual_event = str3(self.prefix + " 4")
        self.trigIn_event = str3(self.prefix + " 5")
        self.manual_iter = str3(self.prefix + " 6")
        self.trigIn_iter = str3(self.prefix + " 7")


class set_voltage():
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix
        # self.req = req3(self.prefix)
        self.out1 = dig_param3(self.prefix + ":OUT1", 0, 60)
        self.out2 = dig_param3(self.prefix + ":OUT2", 0, 60)
        self.out3 = dig_param3(self.prefix + ":OUT3", 0, 60)
        self.out4 = dig_param3(self.prefix + ":OUT4", 0, 60)


class file():
    """
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

    """
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix
        self.delete = str_param3("DEL")
        self.get_file_list = str_param3("DIR?")
        self.get_dir_download = str3("DIR? DOWD")
        self.get_dir_record = str3("DIR? RECD")
        self.get_dir_upgrade = str3("DIR? UPGD")
        self.get_dir_upgrade = str3("DIR? LOGD")
        self.get_file_size = str_param3("SIZ?")
        self.TRLF = str_param3("TRFL")
        self.TRLF_req = str_param3("TRFL?")
        self.check_file_exist = str_param3("CKFL?")
        self.check_details = str_param3("CKLF?")
        self.check_total_duration = str_param3("CKFD?")
        self.select = str_param3("SOUR SEGM")


class status:
    def __init__(self):
        print("INIT Status")
        self.cmd = "STAT?"
        self.prefix = "STAT?"
        self.sys_ver = str3(self.prefix + " SYST")
        self.read_mac = str3(self.prefix + " MAC")
        self.read_out1_status = str3(self.prefix + " OUT1")
        self.read_out2_status = str3(self.prefix + " OUT2")
        self.read_out3_status = str3(self.prefix + " OUT3")
        self.read_out4_status = str3(self.prefix + " OUT4")
        self.read_in1_status = str3(self.prefix + " IN1")
        self.read_in2_status = str3(self.prefix + " IN2")
        self.read_test_status = str3(self.prefix + " TEST")


if __name__ == '__main__':
    # dev = LOG_34970A()
    # dev.init("COM10")
    # dev.send("COM10 send")
    cmd = storage()
    # print("")
    # print("TOP LEVEL")
    # print(cmd.idn.req())
    # print(cmd.protocol.off.str())
    # print(cmd.reset.str())
    # print(cmd.echo.on.str())
    # print(cmd.echo.req())
    # print(cmd.echo.off.str())
    # print(cmd.mode.req())
    # print(cmd.mode.gen.str())
    # print(cmd.setVoltage.out1.val(10.5))
    # print(cmd.setVoltage.out4.val(10.5))
    # print(cmd.setOffset.out1.val(2))
    # print(cmd.file.get_file_size.path("txt.file"))
    # print(cmd.file.get_file_list.path("inst_folder"))

    # cmd_list = []
    # # cmd_list.append(cmd.file.file_transmit.path("file_name"))
    # cmd_list.append(cmd.mode.gen.str())
    # cmd_list.append(cmd.file.select.path("JLR_CI265_WFA_PC.dsg"))
    # cmd_list.append(cmd.trigGen.manual_start.str())
    # cmd_list.append(cmd.start_test.str())
    # cmd_list.append(cmd.start_test.str())
    # print(cmd_list)

    autowave = com_interface()
    autowave.init()
    autowave.pquery(cmd.mode.gen.str())
    autowave.run_test_file("JLR_CI265_WFB_PC.dsg")
    autowave.pquery(cmd.file.select.path("JLR_CI265_WFA_PC.dsg"))
    autowave.pquery(cmd.trigGen.manual_start.str())
    autowave.pquery(autowave.r)
    autowave.pquery(cmd.start_test.str())

