/*
Loramobgate is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

Loramobgate is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Loramobgate; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
*/

/*
   loRaRF + V-USB
*/

////#ifndef FULL_COMMAND_SET
//#define FULL_COMMAND_SET
//#define FSK_SUPPORT
////#endif

// DEFINITIONS

#define SX126X
//#define DEBUG

#if !defined(SX126X) || !defined(SX127X)
#define SX126X
#endif
//

#ifdef SX126X
#include <SX126x.h>
SX126x module;
#else
#include <SX127X.h>
SX127x module;
#endif

//#include <Arduino.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <avr/eeprom.h>
#include <util/delay.h>
#include <math.h>
#include "settings.h"
#include "eeprom_vars.h"
#include "RingBuffer.h"

#define BUFFLEN 512
#define CONTROLBUFFLEN 70


extern "C" {
#include <usbdrv.h>
}

static uint8_t volatile msgBuffer[BUFFLEN] = {0,}; // кольцевой буфер на приём
static uint8_t controlBuf[CONTROLBUFFLEN] = {0,}; // буфер на входящие команды
#ifdef DEBUG
static uint8_t debugBuf[80] = "DEBUG.";
#endif
static uint8_t volatile usb_opCode = 0;
static uint16_t volatile avail = 0;
static bool volatile ready, lock, ledEnabled = false;
static uint16_t dataSent, pydst, dataReceived = 0, dataLength = 0;
static uint8_t message_size, flag;
static RINGBUF_t ringbuf;

DEVICE deviceInfo;
uint8_t *diPtr;

USB_PUBLIC usbMsgLen_t usbFunctionSetup(uchar data[8])
{
  usbRequest_t *rq = (void *)data;
  usb_opCode = rq->bRequest;
  uint16_t i;
  switch (rq->bRequest) // ОБЪЯВЛЕНИЙ ПЕРЕМЕННЫХ НЕ ДЕЛАТЬ!
  {
#ifdef DEBUG
    case USB_DEBUG:
      usbMsgPtr = debugBuf;
      return sizeof(debugBuf);
#endif

    case USB_RADIO_READ_BUFFER:
      usbMsgPtr = msgBuffer;
      return sizeof(msgBuffer);

    case USB_READ_CONTROL_BUFFER:
      usbMsgPtr = controlBuf;
      return sizeof(controlBuf);

    case USB_RADIO_GET_RESULT:
      usbMsgPtr = controlBuf;
      return *(uint16_t*)&controlBuf[RET_PYDC] + 3; // длина полезной нагрузки + формат возвращаемых данных

    case USB_GET_DEVINFO:
      eeprom_read_block((void *)&controlBuf[RET_PYD], (const void *)&di, sizeof(di));
      controlBuf[OPCI] = USB_GET_DEVINFO;
      *(uint16_t*)&controlBuf[RET_PYDC] = sizeof(di);
      usbMsgPtr = controlBuf; // переписать, чтобы читало из указателя, а не из буфера!
      return *(uint16_t*)&controlBuf[RET_PYDC] + 3;

    case USB_GET_PRIVATE_KEY:
      eeprom_read_block((void *)&controlBuf[RET_PYD], (const void *)&privateKey, sizeof(privateKey));
      controlBuf[OPCI] = USB_GET_PRIVATE_KEY;
      *(uint16_t*)&controlBuf[RET_PYDC] = sizeof(privateKey);
      usbMsgPtr = controlBuf; // переписать, чтобы читало из указателя, а не из буфера!
      return *(uint16_t*)&controlBuf[RET_PYDC] + 3;

    case USB_GET_MODULE:
      controlBuf[OPCI] = USB_GET_MODULE;
      *(uint16_t*)&controlBuf[RET_PYDC] = 0x01;
#ifdef SX126X
      controlBuf[RET_PYD] = 6;
#else
      controlBuf[RET_PYD] = 7;
#endif
      usbMsgPtr = controlBuf;
      return *(uint16_t*)&controlBuf[RET_PYDC] + 3;
    
    case USB_ENABLE_MODULE:
      PORTD |= 1 << 1;
      return 0;
      
    case USB_DISABLE_MODULE:
      PORTD &= ~(1 << 1);
      return 0;

    case USB_LED_ENABLE:
      ledEnabled = true;
      return 0;
      
    case USB_LED_DISABLE:
      ledEnabled = false;
      return 0;

    case USB_RADIO_RETRIEVE_MESSAGE: // Mega -> PC
      if (ready) { // подумать?
        RingBuf_Available(&avail, &ringbuf);
        if (avail > 1) {
          lock = true;
          RingBuf_ByteRead(&message_size, &ringbuf);
          dataSent = 0;
          return USB_NO_MSG; // usbFunctionRead will be called now
        }
      }
      return 0;

    case MODULE_CTRL_MESSAGE:
      dataLength  = (int)rq->wLength.word;
      dataReceived = 0;
      pydst = dataLength;
      flag = true;
      return USB_NO_MSG; // usbFunctionWrite will be called now
  }
  // Если все нормально, то сюда мы никогда не должны попадать:
  return 0;
}

// PC -> Mega
USB_PUBLIC uchar usbFunctionWrite(uchar *data, uchar len)
{
  uint16_t i;
  // Обязательно в случае командных пакетов с Payload нужно чтобы pydst был кратен 8!
  for (i = 0; dataReceived < pydst && i < len; i++, dataReceived++) {
    if (dataReceived == 0 && *(uint16_t*)&data[PYDC] > 0) { // PYDC_L в little-endian находится первым слева
      // если это первый блок данных и есть полезная нагрузка
      pydst = data[PYDST]; // ставим ограничение чтения до индекса начала полезной нагрузки
    }
    controlBuf[dataReceived] = data[i]; // всё равно читаем всё в буфер команды
  }
  // теперь у нас в буфере есть какая-то команда с аргументами и (если надо) индекс начала полезной нагрузки
  if (i == 0) // после окончания чтение опкода команды и аргументов в буфер для команд с полезной нагрузкой идёт загрузка порциями сразу в модуль
  { // && dataReceived == 8?
    //  switch (controlBuf[OPCI]){
    //    case M_WRITE: // write() method must be placed between beginPacket() and endPacket()
    if (flag) {
      module.beginPacket();
      flag = false;
    }
    module.write((uint8_t*)data, len);

    dataReceived += len;
    i = len;
    //      break;
    //  }
    // подумать над тем, как перенести аргумент из setFskSyncWord в полезную нагрузку
  }
  // когда всё прочитали и это случай без Payload
  if (i && dataReceived == dataLength) {
    *(uint16_t*)&controlBuf[RET_PYDC] = sizeof(uint8_t);
    switch (controlBuf[OPCI]) // OPCODE
    {
      case M_NOTHING:
        break;

      //      case M_BEGIN: // int8_t(255) = -1;
      //        if(controlBuf[ARGCI] == 0) {
      //          bool a = module.begin();
      //          controlBuf[RET_PYD] = a;
      //          debugBuf[25] = a;
      //        }
      //        else
      //        #if defined(SX126X)
      //          controlBuf[RET_PYD] = module.begin((int8_t)controlBuf[ASI], (int8_t)controlBuf[ASI + 1], (int8_t)controlBuf[ASI + 2], (int8_t)controlBuf[ASI + 3], (int8_t)controlBuf[ASI + 4], (int8_t)controlBuf[ASI + 5]);
      //        #elif defined(SX127X)
      //          controlBuf[RET_PYD] = module.begin((int8_t)controlBuf[ASI], (int8_t)controlBuf[ASI + 1], (int8_t)controlBuf[ASI + 2], (int8_t)controlBuf[ASI + 3], (int8_t)controlBuf[ASI + 4]);
      //        #endif
      //        // этот прикол с приведением типа сделан, чтобы можно было передать -1, хотя при передаче используется uint8_t
      //        break;
      //
      //      case M_END:
      //        module.end();
      //        break;

      case M_RESET:
        controlBuf[RET_PYD] = module.reset();
        break;

      case M_SETFREQUENCY:
        module.setFrequency(*(uint32_t*)&controlBuf[ASI]); // 434000000
        break;

      case M_SETTXPOWER:
        module.setTxPower(controlBuf[ASI], controlBuf[ASI + 1]);
        break;

      case M_SETRXGAIN:
        module.setRxGain(controlBuf[ASI]);
        break;

      case M_SETLORAMODULATION:
        module.setLoRaModulation(controlBuf[ASI], *(uint32_t*)&controlBuf[ASI + 1], controlBuf[ASI + 5], controlBuf[ASI + 6]);
        break;

      case M_SETLORAPACKET:
        module.setLoRaPacket(controlBuf[ASI], *(uint16_t*)&controlBuf[ASI + 1], controlBuf[ASI + 3], controlBuf[ASI + 4], controlBuf[ASI + 5]);
        break;

      case M_SETSYNCWORD:
        module.setSyncWord(*(uint16_t*)&controlBuf[ASI]);
        break;

#ifdef FSK_SUPPORT
      case M_SETFSKMODULATION:
        module.setFskModulation(*(uint32_t*)&controlBuf[ASI], controlBuf[ASI + 4], controlBuf[ASI + 5], *(uint32_t*)&controlBuf[ASI + 6]);
        break;

      case M_SETFSKPACKET:
        module.setFskPacket(*(uint16_t*)&controlBuf[ASI], controlBuf[ASI + 2], controlBuf[ASI + 3], controlBuf[ASI + 4], controlBuf[ASI + 5], controlBuf[ASI + 6], controlBuf[ASI + 7], controlBuf[ASI + 8]);
        break;

      case M_SETFSKSYNCWORD:
        module.setFskSyncWord(controlBuf + ASI, 4); // assume SyncWorld is 4 bytes
        break;

      case M_SETFSKADRESS:
        module.setFskAdress(controlBuf[ASI], controlBuf[ASI + 1]);
        break;
#endif
      case M_BEGINPACKET:
        module.beginPacket();
        break;

      case M_ENDPACKET:
        if (controlBuf[ARGCI] == 0) controlBuf[RET_PYD] = module.endPacket(); // 1x default param
        else  controlBuf[RET_PYD] = module.endPacket(); // 1x param //if(controlBuf[ARGCI] == 1)
        break;

      case M_WRITE:
        module.endPacket();
        module.wait();
        break;

      case M_REQUEST:
        if (controlBuf[ARGCI] == 0) controlBuf[RET_PYD] = module.request();
        else controlBuf[RET_PYD] = module.request(*(uint32_t*)&controlBuf[ASI]); //, controlBuf[ASI + 4]);
        break;

      case M_LISTEN:
        controlBuf[RET_PYD] = module.listen(*(uint32_t*)&controlBuf[ASI], *(uint32_t*)&controlBuf[ASI + 4]);
        break;

      case M_AVAILABLE:
        controlBuf[RET_PYD] = module.available();
        break;

      case M_READ:
        if (controlBuf[ARGCI] == 0) controlBuf[RET_PYD] = module.read();
        //else module.read(controlBuf + ASI, controlBuf[ASI + 4]);
        // подумать
        break;

      case M_WAIT:
        if (controlBuf[ARGCI] == 0) controlBuf[RET_PYD] = module.wait();
        else controlBuf[RET_PYD] = module.wait(*(uint32_t*)&controlBuf[ASI]);
        break;

      case M_STATUS:
        controlBuf[RET_PYD] = module.status();
        break;

      case M_TRANSMITTIME:
        *(uint16_t*)&controlBuf[RET_PYDC] = sizeof(uint32_t);
        *(uint32_t*)&controlBuf[RET_PYD] = module.transmitTime();
        break;

      case M_DATARATE:
        *(uint16_t*)&controlBuf[RET_PYDC] = sizeof(float);
        *(uint32_t*)&controlBuf[RET_PYD] = module.dataRate();
        break;

      case M_PACKETRSSI: // ??? uint -> int?
        *(uint16_t*)&controlBuf[RET_PYDC] = sizeof(int16_t);
        *(int16_t*)&controlBuf[RET_PYD] = module.packetRssi();
        break;

      case M_SNR: // ?
        *(uint16_t*)&controlBuf[RET_PYDC] = sizeof(float);
        *(uint32_t*)&controlBuf[RET_PYD] = module.snr();
        break;

      case M_SIGNALRSSI: // ??? uint -> int?
        *(uint16_t*)&controlBuf[RET_PYDC] = sizeof(int16_t);
        *(int16_t*)&controlBuf[RET_PYD] = module.signalRssi();
        break;

#ifdef FULL_COMMAND_SET

      case M_SETPINS:
        if (controlBuf[ARGCI] == 0) {
#if defined(SX126X)
          module.setPins(NSSPIN, RSTPIN, BUSYPIN, IRQPIN, TXENPIN, RXENPIN);
#elif defined(SX127X)
          module.setPins(NSSPIN, RSTPIN, IRQPIN, TXENPIN, RXENPIN);
#endif
        }
        // else
        break;
      case M_SLEEP:
        if (controlBuf[ARGCI] == 0) module.sleep();
        else module.sleep(controlBuf[ASI]);
        break;

      case M_WAKE:
        module.wake();
        break;

      case M_STANDBY:
        if (controlBuf[ARGCI] == 0) module.standby();
        else module.standby(controlBuf[ASI]);
        break;

      case M_SETACTIVE:
        module.setActive();
        break;

      case M_BUSYCHECK:
        if (controlBuf[ARGCI] == 0) controlBuf[RET_PYD] = module.busyCheck();
        else controlBuf[RET_PYD] = module.busyCheck(*(uint32_t*)&controlBuf[ASI]);
        break;

      case M_SETFALLBACKMODE:
        module.setFallbackMode(controlBuf[ASI]);
        break;

      case M_GETMODE:
        controlBuf[RET_PYD] = module.getMode();
        break;

      case M_SETMODEM:
        if (controlBuf[ARGCI] == 0) module.setModem();
        else module.setModem(controlBuf[ASI]);
        break;

      case M_SETSPREADINGFACTOR:
        module.setSpreadingFactor(controlBuf[ASI]);
        break;

      case M_SETBANDWIDTH:
        module.setBandwidth(*(uint32_t*)&controlBuf[ASI]);
        break;

      case M_SETCODERATE:
        module.setCodeRate(controlBuf[ASI]);
        break;

      case M_SETLDROENABLE:
        if (controlBuf[ARGCI] == 0) module.setLdroEnable();
        else module.setLdroEnable(controlBuf[ASI]);
        break;

      case M_SETHEADERTYPE:
        module.setHeaderType(controlBuf[ASI]);
        break;

      case M_SETPREAMBLELENGTH:
        module.setPreambleLength(*(uint16_t*)&controlBuf[ASI]);
        break;

      case M_SETPAYLOADLENGTH:
        module.setPayloadLength(controlBuf[ASI]);
        break;

      case M_SETCRCENABLE:
        if (controlBuf[ARGCI] == 0) module.setCrcEnable();
        else module.setCrcEnable(controlBuf[ASI]);
        break;

      case M_SETINVERTIQ:
        if (controlBuf[ARGCI] == 0) module.setInvertIq();
        else module.setInvertIq(controlBuf[ASI]);
        break;

      case M_SETFSKCRC:
        module.setFskCrc(*(uint16_t*)&controlBuf[ASI], *(uint16_t*)&controlBuf[ASI + 2]);
        break;

      case M_SETFSKWHITENING:
        module.setFskWhitening(*(uint16_t*)&controlBuf[ASI]);
        break;

      case M_PURGE:
        if (controlBuf[ARGCI] == 0) module.purge();
        else module.purge(controlBuf[ASI]);
        break;

      case M_RSSIINST:
        *(uint16_t*)&controlBuf[RET_PYDC] = sizeof(int16_t);
        *(int16_t*)&controlBuf[RET_PYD] = module.rssiInst();
        break;

      case M_RANDOM:
        *(uint16_t*)&controlBuf[RET_PYDC] = sizeof(uint32_t);
        *(uint32_t*)&controlBuf[RET_PYD] = module.random();
        break;
#endif
    }
  }
  // вернем 1, если приняли все, иначе 0:
  return (dataReceived == dataLength);
}

/*
  Ёбаный рот это казино, блядь! (с)
  Ты должен помнить, что эта функция вызывается многоразово!
  А точнее - каждые 8 байт!
  Поэтому объявлять тут переменные, которые ссылаются на что-то в буфере,
  равно как и трогать n-ый индекс data - БЕСПОЛЕЗНО!!!
  Делай это, если надо, в свитче для нужного кейса!
*/

// Mega -> PC
USB_PUBLIC uchar usbFunctionRead(uchar *data, uchar len)
{
  uint16_t i;
  switch (usb_opCode) // не забыть вписать терминатор строки и вернуть кол-во записанных байт
  {
    case USB_RADIO_RETRIEVE_MESSAGE:
      for (i = 0; dataSent < message_size && i < len; i++, dataSent++) {
        RingBuf_ByteRead(&data[i], &ringbuf);
      }
      lock = false;
      break;
  }
  return i; // i равно количеству записанных байт

}
void storeMessage() {
  if (!lock) {
    PORTC |= ((1 & ledEnabled) << 2);
    ready = false;
    uint16_t portion_size = 8, a, temp = 0; // <= 8 byte portion to read every transaction
    uint8_t smallbuff[portion_size] = {0,};
    // убедимся, что в буфере достаточно места для самого сообщения и сопутствующих данных
    RingBuf_Available(&a, &ringbuf); // ЗАПОЛНЕННОСТЬ буфера!
    if (module.available() + 1 <= BUFFLEN - a) // + PYDC = 1 byte
    {
      RingBuf_BytePut(module.available(), &ringbuf);
      while (portion_size > 0) { // module.available
        temp = module.read(smallbuff, portion_size);
        RingBuf_DataPut(smallbuff, portion_size, &ringbuf);
        portion_size = temp;
      }
    }
    PORTC &= ~((1 & ledEnabled) << 2);
    ready = true;
  }
}

void setup() {
  //PORTD |= 1 << 1; // enable 3.3 V supply on module
  uint16_t i;
  RingBuf_Init(msgBuffer, BUFFLEN, sizeof(uint8_t), &ringbuf);
  RingBuf_Clear(&ringbuf);
  // Разрешить работу сторожевого таймера с периодом 1 сек:
  wdt_enable(WDTO_4S);
  /* If you want to use interrupt operation,
    you can connect DIO0 for SX127x series
    and one of DIO1, DIO2, or DIO3 pin for SX126x series */
#if defined(SX126X)
  module.setPins(NSSPIN, RSTPIN, BUSYPIN, IRQPIN, TXENPIN, RXENPIN);
#elif defined(SX127X)
  module.setPins(NSSPIN, RSTPIN, IRQPIN, TXENPIN, RXENPIN);
#endif
    
  if (!module.begin()) {
    while (1);
  }

  module.onReceive(storeMessage);
  PORTC |= (1 << 2);
  _delay_ms(100);
  PORTC &= ~(1 << 2);
  _delay_ms(50);
  PORTC |= (1 << 2);
  _delay_ms(50);
  PORTC &= ~(1 << 2);
  _delay_ms(50);
  PORTC |= (1 << 2);
  _delay_ms(100);
  PORTC &= ~(1 << 2);
  usbInit();
  usbDeviceDisconnect();  // принудительная повторная энумерация
  for (i = 0; i < 250; i++)
  {
    // ожидание 500 мс
    wdt_reset();  // сброс сторожевого таймера
    _delay_ms(2);
  }
  usbDeviceConnect();
  // Разрешить прерывания после повторной енумерации:

  sei();
}

void loop() {
  wdt_reset();  // сброс сторожевого таймера
  usbPoll();
}
