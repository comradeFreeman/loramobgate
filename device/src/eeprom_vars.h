struct DEVICE { // записать это в EERPOM
    uint32_t devAddr;
    uint16_t loraSyncWord; // пока так. подумать
    uint16_t country; // ISO3166-1, UKRAINE (804)
};

DEVICE EEMEM di = {0x12345678, 0x0034, 0x324};

uint8_t EEMEM privateKey[28] = {
                                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00 0x00,
                                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00 0x00,
                                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00 0x00,
                                  0x00, 0x00, 0x00, 0x00, 0x00, 0x00 0x00 }; // приватный ключ


// создаётся .eep файл с этими данными
// передача на ПК идёт в little-endian, но это если usb, приватный ключ тут передаётся нормально.
