/* 
        Если это команда к модулю, то s.MODULE_CTRL_MESSAGE + usbPacket
        Если это запрос данных с устройства, то 
*/
/*
   Структура пакета, используемого для обмена между хостом и устройством:
   а) PC -> Mega

        0 ------------------------------------------------------------------------------------> 512 bytes
        +-----------------------------------------------------------------------------------------------+
        | 1 byte | 1 byte | 1 byte  |  2 bytes   | ARG1LEN bytes |  ...  | ARGnLEN bytes |  PYDC bytes  |
        +--------+--------+---------+------------+---------------+-------+---------------+--------------+
        | OPCODE |  ARGC  |  PYDST  |    PYDC    |     ARG1      |  ...  |     ARGn      |   PAYLOAD    |
        +-----------------------------------------------------------------------------------------------+
        * Начало PAYLOAD надо размещать на байтах, кратных 8, для упрощения чтения через V-USB
   
   б) Mega -> PC
        0 -------------------------> 512 bytes
        +--------+------------+--------------+        
        | 1 byte |   2 bytes  |  PYDC bytes  |     
        +--------+------------+--------------+     
        | OPCODE |    PYDC    |   PAYLOAD    |     
        +------------------------------------+        
        * по сути можно взять такой же формат, как на передачу, только не использовать поля для аргументов
        * PYDC, little-endian - младший разряд слева, т.е. [PYDC_L, PYDC_H]
                
   Структура пакета, используемого для радиообмена:
   
        +------------------------------------+
        |   N bytes  |  PYDC bytes | C bytes |               Что в LoRa, что в FSK существует возможность задать
        +------------+-------------+---------+   L1 OSI      длину полезной нагрузки. Таковая содержится в одном
        |  LoRa/FSK  |   PAYLOAD   |   CRC   |               из полей заголовка. См. документацию на LoraRF
        +------------------------------------+
                            |
                            V
                     +------------------------------------------------------------------------------------+
                     |   4 bytes   |   4 bytes   |  1 byte  |  1 byte  |   1 byte   | 1 byte | PYDC bytes |
                     +-------------+-------------+----------+----------+------------+--------+------------+
         L2-L4 OSI   | SRC DevAddr | DST DevAddr |  FragmC  |   Fragm  |  X + AppID |  PYDC  |  Payload   |
                     +---------------------------+----------+----------+------------+--------+------------+
                     |          L2 + L3          |                           L4                           |
                     +------------------------------------------------------------------------------------+          
                                                                                             |
                                                                                             V
         Fragm - для указания текущего номера                             +---------------------------------------+
         фрагмента, напр., для аудиопотока.                               |    1 byte   |     PYDC - 1 bytes      |
         FragC - для указания кол-ва фрагментов            L6 + L7 OSI    +-------------+-------------------------+
                                                                          | ContentType | Encode(Compress(Data))  |
                                                                          +---------------------------------------+
*/


/* wiring settings of module */ 
#define NSSPIN  10
#define RSTPIN  9
#define BUSYPIN 5
#define IRQPIN  3
#define TXENPIN 8
#define RXENPIN 7
#define NOPIN  -1

/* module initial settings */
#define LORA_FREQUENCY 434000000
#define LORA_SPREADING_FACTOR 9
#define LORA_BANDWIDTH 125000
#define LORA_CODERATE 7
#define LORA_PREAMBLE_LENGTH 12
#define LORA_PAYLOAD_LENGTH 15
#define LORA_CRC_ENABLE true

/* Transmission settings of module */
#define LORA_SYNC_WORD 0x34

/* USB control messages types a.k.a OPCODE */
#define USB_M_REQUEST 250
#define PINGPONG 99
#define USB_VOID 255
//#define USB_LED_OFF 255
//#define USB_LED_ON  254
//#define USB_DATA_OUT 253           // Mega -> PC
//#define USB_DATA_WRITE 252         // PC -> Mega
//#define USB_DATA_IN 251            // PC -> Mega ( >4 bytes )
//#define USB_DATA_LONGOUT 250       // Mega -> PC ( >4 bytes )
#define USB_DEBUG 249         // Mega Debug -> PC
#define USB_READ_CONTROL_BUFFER 248
#define USB_RADIO_RETRIEVE_MESSAGE 205 // Mega RINGbuffer -> PC
#define USB_RADIO_READ_BUFFER 206  // Mega buffer -> PC
#define USB_RADIO_GET_RESULT 207 // Получить буфер результата выполнения предыдущей команды (если доступен)
#define USB_GET_DEVINFO 208 // запросить адрес устройства L2 
#define USB_GET_MODULE 209 // вернуть чип, используемый в коде

#define USB_GET_PRIVATE_KEY    211
//#define USB_GET_PUBLIC_KEY    212

#define USB_ENABLE_MODULE 228
#define USB_DISABLE_MODULE 229
//#define USB_RADIO_WRITE_BUFFER 7 // PC -> Mega buffer
//#define USB_RADIO_RRQST 10 // PC -> Mega.receive()
//#define USB_RADIO_TRQST 20 // PC -> Mega.transmit()
//#define USB_RADIO_GET_STATUS 30  // Mega.resBuff -> PC


// Индексы ключевых байт в контрольном сообщении. Основано на формате
#define OPCI   0     // OPCODE Index

#define ARGCI    1   // ArgCount Index
#define PYDST    2   // PayloadStart Index
#define PYDC     3   // little-endian: L
//#define PYDC_L 4   // little-endian: H
#define ASI    5     // ArgStart Index 


#define RET_PYDC 1   // little-endian: L
//#define RET_PYDC_L 2  little-endian: H
#define RET_PYD  3


// LoRaRF

#define MODULE_CTRL_MESSAGE   100

// Hardware configuration methods

#define M_SETPINS             109

// Common Operational methods

#define M_NOTHING 101
#define M_BEGIN               110   // bool begin(int8_t nss, int8_t reset, int8_t busy, int8_t irq=-1, int8_t txen=-1, int8_t rxen=-1);
#define M_END                 111   // void end();
#define M_RESET               112   // bool reset();
#define M_SLEEP               113   // void sleep(uint8_t option=SX126X_SLEEP_WARM_START);
#define M_WAKE                114   // void wake();
#define M_STANDBY             115   // void standby(uint8_t option=SX126X_STANDBY_RC);
#define M_SETACTIVE           116   // void setActive();
#define M_BUSYCHECK           117   // bool busyCheck(uint32_t timeout=SX126X_BUSY_TIMEOUT);
#define M_SETFALLBACKMODE     118   // void setFallbackMode(uint8_t fallbackMode);
#define M_GETMODE             119   // uint8_t getMode();
          
        
// Modem, modulation parameter, and packet parameter setup methods

#define M_SETMODEM            120   // void setModem(uint8_t modem=SX126X_LORA_MODEM);
#define M_SETFREQUENCY        121   // void setFrequency(uint32_t frequency);
#define M_SETTXPOWER          122   // void setTxPower(uint8_t txPower, uint8_t version=SX126X_TX_POWER_SX1262);
#define M_SETRXGAIN           123   // void setRxGain(uint8_t boost);
#define M_SETLORAMODULATION   124   // void setLoRaModulation(uint8_t sf, uint32_t bw, uint8_t cr, bool ldro=false);
#define M_SETLORAPACKET       125   // void setLoRaPacket(uint8_t headerType, uint16_t preambleLength, uint8_t payloadLength, bool crcType=false, bool invertIq=false);
#define M_SETSPREADINGFACTOR  126   // void setSpreadingFactor(uint8_t sf);
#define M_SETBANDWIDTH        127   // void setBandwidth(uint32_t bw);
#define M_SETCODERATE         128   // void setCodeRate(uint8_t cr);
#define M_SETLDROENABLE       129   // void setLdroEnable(bool ldro=true);
#define M_SETHEADERTYPE       130   // void setHeaderType(uint8_t headerType);
#define M_SETPREAMBLELENGTH   131   // void setPreambleLength(uint16_t preambleLength);
#define M_SETPAYLOADLENGTH    132   // void setPayloadLength(uint8_t payloadLength);
#define M_SETCRCENABLE        133   // void setCrcEnable(bool crcType=true);
#define M_SETINVERTIQ         134   // void setInvertIq(bool invertIq=true);
#define M_SETSYNCWORD         135   // void setSyncWord(uint16_t syncWord);
#define M_SETFSKMODULATION    136   // void setFskModulation(uint32_t br, uint8_t pulseShape, uint8_t bandwidth, uint32_t Fdev);
#define M_SETFSKPACKET        137   // void setFskPacket(uint16_t preambleLength, uint8_t preambleDetector, uint8_t syncWordLength, uint8_t addrComp, uint8_t packetType, uint8_t payloadLength, uint8_t crcType, uint8_t whitening);
#define M_SETFSKSYNCWORD      138   // void setFskSyncWord(uint8_t* sw, uint8_t swLen);
#define M_SETFSKADRESS        139   // void setFskAdress(uint8_t nodeAddr, uint8_t broadcastAddr);
#define M_SETFSKCRC           140   // void setFskCrc(uint16_t crcInit, uint16_t crcPolynom);
#define M_SETFSKWHITENING     141   // void setFskWhitening(uint16_t whitening);

// Transmit related methods

#define M_BEGINPACKET         142   // void beginPacket();
#define M_ENDPACKET           143   // bool endPacket(uint32_t timeout=SX126X_TX_SINGLE, bool intFlag=true); | bool endPacket(bool intFlag);
#define M_WRITE               144   // void write(uint8_t data); | void write(uint8_t* data, uint8_t length); | void write(char* data, uint8_t length);
// для write можем читать всё вплоть с длиной полезной нагрузки, а на неё кидать указатель в саму ф. так сэкономим много памяти

// Receive related methods

#define M_REQUEST             145   // bool request(uint32_t timeout=SX126X_RX_SINGLE, bool intFlag=true);
#define M_LISTEN              146   // bool listen(uint32_t rxPeriod, uint32_t sleepPeriod, bool intFlag=true);
#define M_AVAILABLE           147   // uint8_t available();
#define M_READ                148   // uint8_t read(); | uint8_t read(uint8_t* data, uint8_t length); | uint8_t read(char* data, uint8_t length); 
#define M_PURGE               149   // void purge(uint8_t length=0);

// Wait, operation status, and packet status methods

#define M_WAIT                150   // bool wait(uint32_t timeout=0);
#define M_STATUS              151   // uint8_t status();
#define M_TRANSMITTIME        152   // uint32_t transmitTime();
#define M_DATARATE            153   // float dataRate();
#define M_PACKETRSSI          154   // int16_t packetRssi();
#define M_SNR                 155   // float snr();
#define M_SIGNALRSSI          156   // int16_t signalRssi();
#define M_RSSIINST            157   // int16_t rssiInst();
#define M_GETERROR            158   // uint16_t getError();
#define M_RANDOM              159   // uint32_t random();
