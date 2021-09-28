`import AutoWave_class
import time
import Timer_class

timer = Timer_class.Timer()




inst_folder = "/home/guest/DowFiles"

WaveFormA = [
            "JLC_CI256_WFA_20000ms.dpt",
            "JLR_CI265_WFA_1000ms.dpt",
            "JLR_CI265_WFA_200ms.dpt",
            "JLR_CI265_WFA_100ms.dpt",
            "JLR_CI265_WFA_60ms.dpt",
            "JLR_CI265_WFA_48ms.dpt",
            "JLR_CI265_WFA_35ms.dpt",
            "JLR_CI265_WFA_24ms.dpt",
            "JLR_CI265_WFA_18ms.dpt",
            "JLR_CI265_WFA_12ms.dpt",
            "JLR_CI265_WFA_9ms.dpt",
            "JLR_CI265_WFA_6ms.dpt",
            "JLR_CI265_WFA_3ms.dpt",
]


inst = AutoWave_class.com_interface()


for test in WaveFormA:
    inst.init()
    test_time = inst.get_test_time(test)
    timer.start(round(test_time)+20)
    time.sleep(1)
    print(f'*** Test: {test} is Started')
    inst.run_test_file(test)
    while True:
        if timer.is_finihed():
            timer.stop()
            break

    test_status = inst.check_test_status()
    print(f'*** Test: {test} is {test_status[0][1]}')
    inst.disconnect()
    #inst.reboot()
    time.sleep(5)


# for i in range(10):
#     timer.check_time()
#     print(inst.check_test_status())
#     time.sleep(5)
timer.stop()

