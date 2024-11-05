Lights Out
==========

This repository contains the tools and memory dumps shared as a part of the ["Lights Out: Covertly turning off the ThinkPad webcam LED indicator"](https://docs.google.com/presentation/d/1NSS2frdiyRVr-5vIjAU-2wf_agzpdiMR1DvVhz2eDwc/edit?usp=sharing) talk I gave at PoC 2024.

These tools allow getting software control of the webcam LED on ThinkPad X230.


## Tools

- [srom.py](srom.py) — reads and writes the SROM part of the firwmware of a Ricoh R5U8710–based webcam module over USB;

- [patch_srom.py](patch_srom.py) — patches the SROM image from the FRU `63Y0248` webcam module to add the universal implant (see the talk slides for details).
The resulting image can be flashed onto the original X230 webcam module as well;

- [fetch.py](fetch.py) — fetches `IRAM`, `XDATA`, or `CODE` memory space over USB via the universal implant;

- [led.py](led.py) — turns the webcam LED on or off via the universal implant.


## Memory dumps

- [srom/x230.bin](srom/x230.bin) — SROM contents of the original X230 webcam module (FRU unknown; `19N1L1NVRA0H` marking on the board);

- [srom/63Y0248.bin](srom/63Y0248.bin) — SROM contents of the FRU `63Y0248` webcam module;

- [code/63Y0248.bin](code/63Y0248.bin) — Contents of the `CODE` memory space leaked from the FRU `63Y0248` webcam module.
(Boot ROM is below the offset `0xb000`, and it is identical to the Boot ROM on the original X230 webcam module.)
