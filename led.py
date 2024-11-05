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

status = sys.argv[1]

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

def arbitrary_write(addr, value):
	request_write(0x42, value, addr, '')

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

if status == 'on':
	arbitrary_write(0x80, 0x02)
elif status == 'off':
	arbitrary_write(0x80, 0x00)
else:
	raise ValueError('Invalid area')
