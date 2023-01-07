struct DEVICE { // записать это в EERPOM
    uint32_t devAddr;
    uint16_t loraSyncWord; // пока так. подумать
    uint16_t country; // ISO3166-1, UKRAINE (804)
    // придумать ещё атрибуты, связанные с L2/L3 OSI.
};

//
//    uint32_t EEMEM devAddr=0xabcdf987;
//    uint16_t EEMEM loraSyncWord = 0xabcd; // пока так. подумать
//    uint16_t EEMEM country = 0x324; // ISO3166-1, UKRAINE (804)
//    // придумать ещё атрибуты, связанные с L2/L3 OSI.

DEVICE EEMEM di = {0xabcdf987, 0x0034, 0x324}; // 0xffffaaaa

uint8_t EEMEM privateKey[28] = { // 0xabcdf987 = 0x5f2839e5021fe8000794cfa8bd085c25c5c82ee8d14b6ecf68228338
                                  0x5f, 0x28, 0x39, 0xe5, 0x02, 0x1f, 0xe8,
                                  0x00, 0x07, 0x94, 0xcf, 0xa8, 0xbd, 0x08,
                                  0x5c, 0x25, 0xc5, 0xc8, 0x2e, 0xe8, 0xd1,
                                  0x4b, 0x6e, 0xcf, 0x68, 0x22, 0x83, 0x38 };


                               //{ // 0xffffaaaa = 0xf062df16fd63d99ece4e5f442654bb632b0a9b4329773225d6f5d586
                               //   0xf0, 0x62, 0xdf, 0x16, 0xfd, 0x63, 0xd9, 
                               //   0x9e, 0xce, 0x4e, 0x5f, 0x44, 0x26, 0x54, 
                               //   0xbb, 0x63, 0x2b, 0x0a, 0x9b, 0x43, 0x29, 
                               //   0x77, 0x32, 0x25, 0xd6, 0xf5, 0xd5, 0x86 }; // приватный ключ


// создаётся .eep файл с этими данными
// передача на ПК идёт в little-endian, но это если usb, приватный ключ тут передаётся нормально.
