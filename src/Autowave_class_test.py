import AutoWave_class
import time
inst_folder = "/home/guest/DowFiles"
inst_test_file = "Ford ES-XW7T-1A278-AC - CI210 -.dsg"
cmd = AutoWave_class.storage()
inst = AutoWave_class.com_interface()
inst.init()
inst.run_test_file(inst_test_file)
for i in range(10):
    print(inst.check_test_status())
    time.sleep(5)


