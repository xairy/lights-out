#!/usr/bin/env python3
#
# https://github.com/xairy/lights-out
#
# Author: Andrey Konovalov

import array
import binascii
import sys
import time

import usb.core
import usb.util

command = sys.argv[1]
filename = sys.argv[2]

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

# 0x01: Unlock SROM.
def unlock_srom():
	request_write(0x01, 0, 0, '')
	time.sleep(0.1)

# 0x03: Lock SROM.
def lock_srom():
	request_write(0x03, 0, 0, '')
	time.sleep(0.1)

# 0x02: Write SROM at offset.
# Overwrites a whole 4 KB block.
# Can be done in chunks of 64 bytes at most (buffer overflow?).
def write_srom_once(offset, data):
	request_write(0x02, 0, offset, data)
	time.sleep(0.1)

# 0x07: Read SROM.
# Can be done in chunks of 64 bytes at most (buffer overflow?).
def read_srom_once(offset, length):
	return request_read(0x07, 0, offset, length)

def read_srom(filename, length):
	with open(filename, 'wb') as f:
		for i in range(length // 64):
			part = read_srom_once(i * 64, 64)
			f.write(part)

def write_srom(filename, length):
	data = None
	with open(filename, 'rb') as f:
		data = f.read()

	assert(len(data) == length)

	unlock_srom()
	for i in range(0, len(data) // 64):
		write_srom_once(i * 64, data[i * 64 : (i + 1) * 64])
	lock_srom()

if command == 'read':
	read_srom(filename, 0x10000)
elif command == 'write':
	write_srom(filename, 0x10000)
else:
	raise ValueError('Unknown command')
