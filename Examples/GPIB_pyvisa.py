##
##
##

import sys
import pyvisa
import time

AG_status = ["stopped",
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
            "file processing",]


def delay_cmd(time_s=2):
    time.sleep(time_s)

def psend(txt_cmd):
    print("Psend input:", txt_cmd)
    sum = 0 # variable for check summ
    cmd = [] # array for formatted command

    for item in txt_cmd:
        # sum = sum + hex(item.encode('utf-8').hex())
        #print(f"Symbol: {item}, value: {ord(item)}")
        sum = sum + int(ord(item))
        cmd.append(ord(item))
    check_sum = sum & 0x00FF
    print(f"sum: {sum}, check_sum: {check_sum}, cmd: {cmd}")
    #  If the checksum is less or equal to 0x20, 0x20 is added again.
    #  Thus ensures that the checksum is not interpreted as control character.
    if check_sum <= 0x20:
        check_sum += 0x20
    # additional protocol requirements
    # STX=0x02 + Command + ETX=0x03 + CheckSum
    cmd.insert(0, 2)  # insertion of STX=0x02 to a first place
    cmd.append(3)  # termination message with ETX=0x03
    cmd.append(check_sum)  # adding check sum at the end
    print(f"protocol cmd: {cmd}")
    print(bytearray(cmd))
    return (bytes(cmd))
    # return ((cmd))





rm = pyvisa.ResourceManager()
rm_list = rm.list_resources()
i = 0
resource_name = ""
for item in rm_list:
     if "AutoWave" in item:
         resource_name = item
     # print(f"{i} : {item}")
     i = i+1
# resource_name = "USB0::0x03EB::0x2065::_IDN_EM_TEST__AutoWave__0__5.10.08__2__0::INSTR"
if resource_name != "":
    inst = rm.open_resource(resource_name)
    print(inst)
inst.set_visa_attribute(pyvisa.constants.VI_ATTR_SEND_END_EN, 1)
print(f'VI_ATTR_SEND_END_EN={inst.get_visa_attribute(pyvisa.constants.VI_ATTR_SEND_END_EN)}')
#print(f'VI_ATTR_ASRL_END_OUT={inst.get_visa_attribute(pyvisa.constants.VI_ATTR_ASRL_END_OUT)}')
# print("write_termination:", inst.write_termination)
inst.write_termination = ""
print("write_termination:", inst.write_termination)
# inst.read_termination = '\n'
# inst.write_termination = '\n'
#inst.baud_rate = 9600

inst.write("*PRCL:ON")
print("Session:", inst.session)
delay_cmd()
print(inst.query("*IDN?"))
delay_cmd()
print(inst.query("*PRCL?"))
delay_cmd()
print(inst.query("*ECHO:ON"))
delay_cmd()
# print(inst.query_binary_values(b'\x02STAT? SYST\x03\xee'))
print(inst.write_raw(psend("STAT? SYST")))
print(inst.read_raw())
delay_cmd()
# inst.write("DISP Python control")
# delay_cmd()
print("*** TESTING INIT ***")
file_list = inst.write_raw(psend("DIR? /home/guest/DowFiles"))
print(file_list)
file_list_array = file_list.split(",")
number = 0
for item in file_list_array:
    print(f'{number} : {item}')
    number = number +1
delay_cmd()
test_file_name = "Ford ES-XW7T-1A278-AC - CI210 -.dsg"
print("TEST file:", inst.query(f"CKLF? {test_file_name}"))
delay_cmd()
print(inst.query(f"TRFL home/guest/DowFiles/{test_file_name}"))
delay_cmd()
print(inst.query("MOD GEN"))
delay_cmd()
print(inst.query(f"SOUR SEGM {test_file_name}"))
delay_cmd()
delay_cmd()
print(inst.query("TRIG:GEN 1")) # 1 is for a manual stat on cmd
delay_cmd()
##requires to send double start.. to trigger genetation
print(inst.query("STAR")) #trigger the test start
delay_cmd()
print(inst.query("STAR")) #trigger the test start


delay_cmd()
for i in range(10):
    delay_cmd()
    delay_cmd()
    status = inst.query("STAT? TEST")
    st = status.replace("STAT TEST:", "")
    st = st.split(",")
    print("st:", st)
    for code in st:

        print(AG_status[int(code)])

# IDN = str(inst.query("*IDN?"))
# print(f': Connected to: {IDN}')

# print(app.query("OUT?"))
#
# app.write("OUT ON")
# time.sleep(0.25)
# print(app.query("OUT?"))
# time.sleep(0.25)
# app.write("ISET 10A")
# time.sleep(2)
# app.write("VSET 13.5V")
# print(app.query("VSET?"))
# time.sleep(2)
# app.write("OUT OFF")
# print(app.query("OUT?"))