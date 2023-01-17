### DISCLAIMER
### This is an example Makefile and it MUST be configured to suit your needs.
### For detailed explanations about all of the available options, please refer
### to https://github.com/sudar/Arduino-Makefile/blob/master/arduino-mk-vars.md
### Original project where this Makefile comes from: https://github.com/WeAreLeka/Bare-Arduino-Project

### PROJECT_DIR
### This is the path to where you have created/cloned your project
PROJECT_DIR       = .
#/media/amnesia/Data/labs/diplom/loramobgate/device/src

### ARDMK_DIR
### Path to the Arduino-Makefile directory.
ARDMK_DIR         = /usr/share/arduino

### ARDUINO_DIR
### Path to the Arduino application and resources directory.
### or on Linux: (remove the one you don't want)
ARDUINO_DIR       = ../libs
#/home/amnesia/.arduino15/packages/MiniCore
BOARDS_TXT        = $(ARDUINO_DIR)/minicore/avr/boards.txt
#$(ARDUINO_DIR)/hardware/avr/2.1.3/boards.txt
ARDUINO_VAR_PATH  = $(ARDUINO_DIR)/minicore/avr/variants
#$(ARDUINO_DIR)/hardware/avr/2.1.3/variants
ARDUINO_CORE_PATH  = ../libs/minicore/avr/cores/MCUdude_corefiles
#/home/amnesia/.arduino15/packages/MiniCore/hardware/avr/2.1.3/cores/MCUdude_corefiles
#ARDUINO_PACKAGE_DIR = $(HOME)/.arduino15/packages
ARDUINO_PLATFORM_LIB_PATH = ../libs/minicore/avr/libraries
#/home/amnesia/.arduino15/packages/MiniCore/hardware/avr/2.1.3/libraries
ARDUINO_LIBS = usbdrv lorarf ringbuffer SPI

### USER_LIB_PATH
### Path to where the your project's libraries are stored.
USER_LIB_PATH    =  $(PROJECT_DIR)/../libs
### BOARD_TAG
### It must be set to the board you are currently using. (i.e uno, mega2560, etc.)
BOARD_TAG         = 168
#168
#BOARD_SUB         = atmega168
#nano
#BOARD_SUB         = AVR_ATmega168
#atmega168
VARIANT           = standard
BOARD_CLOCK       = 16MHz_external
MCU               = atmega168p
F_CPU             = 16000000L

### MONITOR_BAUDRATE
### It must be set to Serial baudrate value you are using.
MONITOR_BAUDRATE  = 115200

### AVR_TOOLS_DIR
### Path to the AVR tools directory such as avr-gcc, avr-g++, etc.
### or on Linux: (remove the one you don't want)
AVR_TOOLS_DIR     = /usr

### AVRDUDE
### Path to avrdude directory.
### or on Linux: (remove the one you don't want)
AVRDUDE          = /usr/local/bin/avrdude

### CFLAGS_STD
### Set the C standard to be used during compilation. Documentation (https://github.com/WeAreLeka/Arduino-Makefile/blob/std-flags/arduino-mk-vars.md#cflags_std)
CFLAGS_STD        = -std=gnu11

### CXXFLAGS_STD
### Set the C++ standard to be used during compilation. Documentation (https://github.com/WeAreLeka/Arduino-Makefile/blob/std-flags/arduino-mk-vars.md#cxxflags_std)
CXXFLAGS_STD      = -std=gnu++11

### CXXFLAGS
### Flags you might want to set for debugging purpose. Comment to stop.
CXXFLAGS         += -pedantic -Wall -Wextra

### MONITOR_PORT
### The port your board is connected to. Using an '*' tries all the ports and finds the right one.
#MONITOR_PORT      = /dev/ttyUSB0

### CURRENT_DIR
### Do not touch - used for binaries path
CURRENT_DIR       = $(shell basename $(CURDIR))

### OBJDIR
### This is where you put the binaries you just compile using 'make'
OBJDIR            = $(PROJECT_DIR)/bin/$(BOARD_TAG)/$(CURRENT_DIR)

### Do not touch - the path to Arduino.mk, inside the ARDMK_DIR
include $(ARDMK_DIR)/Arduino.mk


ISP_PROG          = usbasp
ISP_EEPROM        = 1
AVRDUDE_ISP_BAUDRATE = 375000
