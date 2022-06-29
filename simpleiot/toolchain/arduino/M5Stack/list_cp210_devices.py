import serial.tools.list_ports

#device: /dev/cu.SLAB_USBtoUART
#name: cu.SLAB_USBtoUART
#description: CP2104 USB to UART Bridge Controller
#hwid: USB VID:PID=10C4:EA60 SER=02042965 LOCATION=2-4.1
#vid: 4292
#pid: 60000

FILTER_VID = [0x1a86, 0x10c4]
FILTER_PID = [0x55d4, 0xea60]


devices = []

for item in serial.tools.list_ports.comports():
  if item.vid in FILTER_VID and item.pid in FILTER_PID:
    devices.append(item)


for dev in devices:
  print(f"Found CP210 device: {dev.name} - at port: {dev.device}")

