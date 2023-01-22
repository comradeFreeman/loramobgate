NSSPIN = 10
RSTPIN = 9
BUSYPIN = 5
IRQPIN = 3
TXENPIN = 8
RXENPIN = 7
NOPIN = -1
LORA_FREQUENCY = 434000000
LORA_SPREADING_FACTOR = 9
LORA_BANDWIDTH = 125000
LORA_CODERATE = 7
LORA_PREAMBLE_LENGTH = 12
LORA_PAYLOAD_LENGTH = 15
LORA_CRC_ENABLE = True
LORA_SYNC_WORD = 52
USB_M_REQUEST = 250
PINGPONG = 99
USB_VOID = 255
USB_DEBUG = 249
USB_READ_CONTROL_BUFFER = 248
USB_RADIO_RETRIEVE_MESSAGE = 205
USB_RADIO_READ_BUFFER = 206
USB_RADIO_GET_RESULT = 207
USB_GET_DEVINFO = 208
USB_GET_MODULE = 209
USB_GET_PRIVATE_KEY = 211
OPCI = 0
ARGCI = 1
PYDST = 2
PYDC = 3
ASI = 5
RET_PYDC = 1
RET_PYD = 3
MODULE_CTRL_MESSAGE = 100
M_SETPINS = 109
M_NOTHING = 101
M_BEGIN = 110
M_END = 111
M_RESET = 112
M_SLEEP = 113
M_WAKE = 114
M_STANDBY = 115
M_SETACTIVE = 116
M_BUSYCHECK = 117
M_SETFALLBACKMODE = 118
M_GETMODE = 119
M_SETMODEM = 120
M_SETFREQUENCY = 121
M_SETTXPOWER = 122
M_SETRXGAIN = 123
M_SETLORAMODULATION = 124
M_SETLORAPACKET = 125
M_SETSPREADINGFACTOR = 126
M_SETBANDWIDTH = 127
M_SETCODERATE = 128
M_SETLDROENABLE = 129
M_SETHEADERTYPE = 130
M_SETPREAMBLELENGTH = 131
M_SETPAYLOADLENGTH = 132
M_SETCRCENABLE = 133
M_SETINVERTIQ = 134
M_SETSYNCWORD = 135
M_SETFSKMODULATION = 136
M_SETFSKPACKET = 137
M_SETFSKSYNCWORD = 138
M_SETFSKADRESS = 139
M_SETFSKCRC = 140
M_SETFSKWHITENING = 141
M_BEGINPACKET = 142
M_ENDPACKET = 143
M_WRITE = 144
M_REQUEST = 145
M_LISTEN = 146
M_AVAILABLE = 147
M_READ = 148
M_PURGE = 149
M_WAIT = 150
M_STATUS = 151
M_TRANSMITTIME = 152
M_DATARATE = 153
M_PACKETRSSI = 154
M_SNR = 155
M_SIGNALRSSI = 156
M_RSSIINST = 157
M_GETERROR = 158
M_RANDOM = 159
FSK_MODEM = 0
LORA_MODEM = 1
LORA_RX_GAIN_POWER_SAVING = 0
LORA_RX_GAIN_BOOSTED = 1
LORA_HEADER_EXPLICIT = 0
LORA_HEADER_IMPLICIT = 1
LORA_TX_SINGLE = 0
LORA_RX_SINGLE = 0
LORA_RX_CONTINUOUS = 16777215
LORA_STATUS_DEFAULT = 0
LORA_STATUS_TX_WAIT = 1
LORA_STATUS_TX_TIMEOUT = 2
LORA_STATUS_TX_DONE = 3
LORA_STATUS_RX_WAIT = 4
LORA_STATUS_RX_CONTINUOUS = 5
LORA_STATUS_RX_TIMEOUT = 6
LORA_STATUS_RX_DONE = 7
LORA_STATUS_HEADER_ERR = 8
LORA_STATUS_CRC_ERR = 9
LORA_STATUS_CAD_WAIT = 10
LORA_STATUS_CAD_DETECTED = 11
LORA_STATUS_CAD_DONE = 12
SX126X_REG_FSK_WHITENING_INITIAL_MSB = 1720
SX126X_REG_FSK_CRC_INITIAL_MSB = 1724
SX126X_REG_FSK_SYNC_WORD_0 = 1728
SX126X_REG_FSK_NODE_ADDRESS = 1741
SX126X_REG_IQ_POLARITY_SETUP = 1846
SX126X_REG_LORA_SYNC_WORD_MSB = 1856
SX126X_REG_RANDOM_NUMBER_GEN = 2073
SX126X_REG_TX_MODULATION = 2185
SX126X_REG_RX_GAIN = 2220
SX126X_REG_TX_CLAMP_CONFIG = 2264
SX126X_REG_OCP_CONFIGURATION = 2279
SX126X_REG_RTC_CONTROL = 2306
SX126X_REG_XTA_TRIM = 2321
SX126X_REG_XTB_TRIM = 2322
SX126X_REG_EVENT_MASK = 2372
SX126X_SLEEP_COLD_START = 0
SX126X_SLEEP_WARM_START = 4
SX126X_SLEEP_COLD_START_RTC = 1
SX126X_SLEEP_WARM_START_RTC = 5
SX126X_STANDBY_RC = 0
SX126X_STANDBY_XOSC = 1
SX126X_TX_SINGLE = 0
SX126X_RX_SINGLE = 0
SX126X_RX_CONTINUOUS = 16777215
SX126X_REGULATOR_LDO = 0
SX126X_REGULATOR_DC_DC = 1
SX126X_CAL_IMG_430 = 107
SX126X_CAL_IMG_440 = 111
SX126X_CAL_IMG_470 = 117
SX126X_CAL_IMG_510 = 129
SX126X_CAL_IMG_779 = 193
SX126X_CAL_IMG_787 = 197
SX126X_CAL_IMG_863 = 215
SX126X_CAL_IMG_870 = 219
SX126X_CAL_IMG_902 = 225
SX126X_CAL_IMG_928 = 233
SX126X_TX_POWER_SX1261 = 1
SX126X_TX_POWER_SX1262 = 2
SX126X_TX_POWER_SX1268 = 8
SX126X_FALLBACK_FS = 64
SX126X_FALLBACK_STDBY_XOSC = 48
SX126X_FALLBACK_STDBY_RC = 32
SX126X_IRQ_TX_DONE = 1
SX126X_IRQ_RX_DONE = 2
SX126X_IRQ_PREAMBLE_DETECTED = 4
SX126X_IRQ_SYNC_WORD_VALID = 8
SX126X_IRQ_HEADER_VALID = 16
SX126X_IRQ_HEADER_ERR = 32
SX126X_IRQ_CRC_ERR = 64
SX126X_IRQ_CAD_DONE = 128
SX126X_IRQ_CAD_DETECTED = 256
SX126X_IRQ_TIMEOUT = 512
SX126X_IRQ_ALL = 1023
SX126X_IRQ_NONE = 0
SX126X_DIO2_AS_IRQ = 0
SX126X_DIO2_AS_RF_SWITCH = 1
SX126X_DIO3_OUTPUT_1_6 = 0
SX126X_DIO3_OUTPUT_1_7 = 1
SX126X_DIO3_OUTPUT_1_8 = 2
SX126X_DIO3_OUTPUT_2_2 = 3
SX126X_DIO3_OUTPUT_2_4 = 4
SX126X_DIO3_OUTPUT_2_7 = 5
SX126X_DIO3_OUTPUT_3_0 = 6
SX126X_DIO3_OUTPUT_3_3 = 7
SX126X_TCXO_DELAY_2_5 = 320
SX126X_TCXO_DELAY_5 = 640
SX126X_TCXO_DELAY_10 = 1376
SX126X_RF_FREQUENCY_XTAL = 32000000
SX126X_RF_FREQUENCY_SHIFT = 25
SX126X_FSK_MODEM = 0
SX126X_LORA_MODEM = 1
SX126X_PA_RAMP_10U = 0
SX126X_PA_RAMP_20U = 1
SX126X_PA_RAMP_40U = 2
SX126X_PA_RAMP_80U = 3
SX126X_PA_RAMP_200U = 4
SX126X_PA_RAMP_800U = 5
SX126X_PA_RAMP_1700U = 6
SX126X_PA_RAMP_3400U = 7
SX126X_BW_7800 = 0
SX126X_BW_10400 = 8
SX126X_BW_15600 = 1
SX126X_BW_20800 = 9
SX126X_BW_31250 = 2
SX126X_BW_41700 = 10
SX126X_BW_62500 = 3
SX126X_BW_125000 = 4
SX126X_BW_250000 = 5
SX126X_BW_500000 = 6
SX126X_CR_4_4 = 0
SX126X_CR_4_5 = 1
SX126X_CR_4_6 = 2
SX126X_CR_4_7 = 3
SX126X_CR_4_8 = 4
SX126X_LDRO_OFF = 0
SX126X_LDRO_ON = 0
SX126X_PULSE_NO_FILTER = 0
SX126X_PULSE_GAUSSIAN_BT_0_3 = 8
SX126X_PULSE_GAUSSIAN_BT_0_5 = 9
SX126X_PULSE_GAUSSIAN_BT_0_7 = 10
SX126X_PULSE_GAUSSIAN_BT_1 = 11
SX126X_BW_4800 = 31
SX126X_BW_5800 = 23
SX126X_BW_7300 = 15
SX126X_BW_9700 = 30
SX126X_BW_11700 = 22
SX126X_BW_14600 = 14
SX126X_BW_19500 = 29
SX126X_BW_23400 = 21
SX126X_BW_29300 = 13
SX126X_BW_39000 = 28
SX126X_BW_46900 = 20
SX126X_BW_58600 = 12
SX126X_BW_78200 = 27
SX126X_BW_93800 = 19
SX126X_BW_117300 = 11
SX126X_BW_156200 = 26
SX126X_BW_187200 = 18
SX126X_BW_234300 = 10
SX126X_BW_312000 = 25
SX126X_BW_373600 = 17
SX126X_BW_467000 = 9
SX126X_HEADER_EXPLICIT = 0
SX126X_HEADER_IMPLICIT = 1
SX126X_CRC_OFF = 0
SX126X_CRC_ON = 1
SX126X_IQ_STANDARD = 0
SX126X_IQ_INVERTED = 1
SX126X_PREAMBLE_DET_LEN_OFF = 0
SX126X_PREAMBLE_DET_LEN_8 = 4
SX126X_PREAMBLE_DET_LEN_16 = 5
SX126X_PREAMBLE_DET_LEN_24 = 6
SX126X_PREAMBLE_DET_LEN_32 = 7
SX126X_ADDR_COMP_OFF = 0
SX126X_ADDR_COMP_NODE = 1
SX126X_ADDR_COMP_ALL = 2
SX126X_PACKET_KNOWN = 0
SX126X_PACKET_VARIABLE = 1
SX126X_CRC_0 = 1
SX126X_CRC_1 = 0
SX126X_CRC_2 = 2
SX126X_CRC_1_INV = 4
SX126X_CRC_2_INV = 6
SX126X_WHITENING_OFF = 0
SX126X_WHITENING_ON = 1
SX126X_CAD_ON_1_SYMB = 0
SX126X_CAD_ON_2_SYMB = 1
SX126X_CAD_ON_4_SYMB = 2
SX126X_CAD_ON_8_SYMB = 3
SX126X_CAD_ON_16_SYMB = 4
SX126X_CAD_EXIT_STDBY = 0
SX126X_CAD_EXIT_RX = 1
SX126X_STATUS_DATA_AVAILABLE = 4
SX126X_STATUS_CMD_TIMEOUT = 6
SX126X_STATUS_CMD_ERROR = 8
SX126X_STATUS_CMD_FAILED = 10
SX126X_STATUS_CMD_TX_DONE = 12
SX126X_STATUS_MODE_STDBY_RC = 32
SX126X_STATUS_MODE_STDBY_XOSC = 48
SX126X_STATUS_MODE_FS = 64
SX126X_STATUS_MODE_RX = 80
SX126X_STATUS_MODE_TX = 96
SX126X_RC64K_CALIB_ERR = 1
SX126X_RC13M_CALIB_ERR = 2
SX126X_PLL_CALIB_ERR = 4
SX126X_ADC_CALIB_ERR = 8
SX126X_IMG_CALIB_ERR = 16
SX126X_XOSC_START_ERR = 32
SX126X_PLL_LOCK_ERR = 64
SX126X_PA_RAMP_ERR = 256
SX126X_LORA_SYNC_WORD_PUBLIC = 13380
SX126X_LORA_SYNC_WORD_PRIVATE = 1857
SX126X_RX_GAIN_POWER_SAVING = 0
SX126X_RX_GAIN_BOOSTED = 1
SX126X_POWER_SAVING_GAIN = 148
SX126X_BOOSTED_GAIN = 150
SX126X_PIN_NSS = 10
SX126X_PIN_RESET = 4
SX126X_PIN_BUSY = 5
SX126X_BUSY_TIMEOUT = 5000
SX126X_STATUS_DEFAULT = 0
SX126X_STATUS_TX_WAIT = 1
SX126X_STATUS_TX_TIMEOUT = 2
SX126X_STATUS_TX_DONE = 3
SX126X_STATUS_RX_WAIT = 4
SX126X_STATUS_RX_CONTINUOUS = 5
SX126X_STATUS_RX_TIMEOUT = 6
SX126X_STATUS_RX_DONE = 7
SX126X_STATUS_HEADER_ERR = 8
SX126X_STATUS_CRC_ERR = 9
SX126X_STATUS_CAD_WAIT = 10
SX126X_STATUS_CAD_DETECTED = 11
SX126X_STATUS_CAD_DONE = 12
SX126X_PIN_RF_IRQ = 1
SX127X_REG_FIFO = 0
SX127X_REG_OP_MODE = 1
SX127X_REG_FRF_MSB = 6
SX127X_REG_FRF_MID = 7
SX127X_REG_FRF_LSB = 8
SX127X_REG_PA_CONFIG = 9
SX127X_REG_OCP = 11
SX127X_REG_LNA = 12
SX127X_REG_FIFO_ADDR_PTR = 13
SX127X_REG_FIFO_TX_BASE_ADDR = 14
SX127X_REG_FIFO_RX_BASE_ADDR = 15
SX127X_REG_FIFO_RX_CURRENT_ADDR = 16
SX127X_REG_IRQ_FLAGS = 18
SX127X_REG_RX_NB_BYTES = 19
SX127X_REG_PKT_SNR_VALUE = 25
SX127X_REG_PKT_RSSI_VALUE = 26
SX127X_REG_RSSI_VALUE = 27
SX127X_REG_MODEM_CONFIG_1 = 29
SX127X_REG_MODEM_CONFIG_2 = 30
SX127X_REG_SYMB_TIMEOUT = 31
SX127X_REG_PREAMBLE_MSB = 32
SX127X_REG_PREAMBLE_LSB = 33
SX127X_REG_PAYLOAD_LENGTH = 34
SX127X_REG_MODEM_CONFIG_3 = 38
SX127X_REG_FREQ_ERROR_MSB = 40
SX127X_REG_FREQ_ERROR_MID = 41
SX127X_REG_FREQ_ERROR_LSB = 42
SX127X_REG_RSSI_WIDEBAND = 44
SX127X_REG_DETECTION_OPTIMIZE = 49
SX127X_REG_INVERTIQ = 51
SX127X_REG_DETECTION_THRESHOLD = 55
SX127X_REG_SYNC_WORD = 57
SX127X_REG_INVERTIQ2 = 59
SX127X_REG_DIO_MAPPING_1 = 64
SX127X_REG_VERSION = 66
SX127X_REG_TCXO = 75
SX127X_REG_PA_DAC = 77
SX127X_FSK_MODEM = 0
SX127X_LORA_MODEM = 1
SX127X_OOK_MODEM = 2
SX127X_LONG_RANGE_MODE = 128
SX127X_MODULATION_OOK = 32
SX127X_MODULATION_FSK = 0
SX127X_MODE_SLEEP = 0
SX127X_MODE_STDBY = 1
SX127X_MODE_TX = 3
SX127X_MODE_RX_CONTINUOUS = 5
SX127X_MODE_RX_SINGLE = 6
SX127X_MODE_CAD = 7
SX127X_RX_SINGLE = 0
SX127X_RX_CONTINUOUS = 16777215
SX127X_TX_POWER_RFO = 0
SX127X_TX_POWER_PA_BOOST = 128
SX127X_RX_GAIN_POWER_SAVING = 0
SX127X_RX_GAIN_BOOSTED = 1
SX127X_RX_GAIN_AUTO = 0
SX127X_HEADER_EXPLICIT = 0
SX127X_HEADER_IMPLICIT = 1
SX127X_SYNCWORD_LORAWAN = 52
SX127X_OSC_CRYSTAL = 0
SX127X_OSC_TCXO = 16
SX127X_DIO0_RX_DONE = 0
SX127X_DIO0_TX_DONE = 64
SX127X_DIO0_CAD_DONE = 128
SX127X_IRQ_CAD_DETECTED = 1
SX127X_IRQ_FHSS_CHANGE = 2
SX127X_IRQ_CAD_DONE = 4
SX127X_IRQ_TX_DONE = 8
SX127X_IRQ_HEADER_VALID = 16
SX127X_IRQ_CRC_ERR = 32
SX127X_IRQ_RX_DONE = 64
SX127X_IRQ_RX_TIMEOUT = 128
SX127X_RSSI_OFFSET_LF = 164
SX127X_RSSI_OFFSET_HF = 157
SX1272_RSSI_OFFSET = 139
SX127X_STATUS_DEFAULT = 0
SX127X_STATUS_TX_WAIT = 1
SX127X_STATUS_TX_TIMEOUT = 2
SX127X_STATUS_TX_DONE = 3
SX127X_STATUS_RX_WAIT = 4
SX127X_STATUS_RX_CONTINUOUS = 5
SX127X_STATUS_RX_TIMEOUT = 6
SX127X_STATUS_RX_DONE = 7
SX127X_STATUS_HEADER_ERR = 8
SX127X_STATUS_CRC_ERR = 9
SX127X_STATUS_CAD_WAIT = 10
SX127X_STATUS_CAD_DETECTED = 11
SX127X_STATUS_CAD_DONE = 12
SX127X_PIN_NSS = 10
SX127X_PIN_RESET = 4
