def str2dec_array(txt):
    cmd = []  # array for formatted command
    for item in txt:
        cmd.append(ord(item))
    return cmd
def array2str2check_sum(array_var):
    check_sum = sum(array_var) & 0x00FF
    if check_sum <= 0x20:
        check_sum += 0x20
    return check_sum

def str2check_sum(txt):
    '''
    Calculate a check sum for text string
    :param txt: input test string
    :type txt: str
    :return: if (sum & 0x00FF) less then 0x20. Return will be Sum + 0x20
    '''
    array = str2dec_array(txt)
    return array2str2check_sum(array)


var = b'\x02TRFL /home/guest/DowFiles/JLR_CI265_WFA_35ms.dpt:ERR\x03\xef'
var2 = var[1:-2]
print(var2.decode("utf-8"))
print(str2check_sum(var2.decode("utf-8")))
print(str2check_sum(var2.decode("utf-8")) == var[-1] )