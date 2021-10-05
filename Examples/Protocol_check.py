
inputString = "STAT? PSRC"
# inputString = "LCN?"
print(inputString)

sum = 0

cmd = []
# cmd.append(2)

for item in inputString:
    # sum = sum + hex(item.encode('utf-8').hex())
    print(f"Symbol: {item}, value: {ord(item)}")
    sum = sum + int(ord(item))
    cmd.append(ord(item))
check_sum = sum & 0x00FF
print(f"summ: {sum}, check_sum: {check_sum}, cmd: {cmd}")
#  If the checksum is less or equal to 0x20, 0x20 is added again.
#  Thus ensures that the checksum is not interpreted as control character.
if check_sum <= 0x20:
    check_sum += 0x20
# additional protocol requirements
# STX=0x02 + Command + ETX=0x03 + CheckSum
cmd.insert(0, 2)  # insertion of STX
cmd.append(3)     # termination message with ETX
cmd.append(check_sum)  # adding check sum at the end
print(f"protocol cmd: {cmd}")
print(bytearray(cmd))

