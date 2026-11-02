#pragma once
#include <stdint.h>
bool initRadio();
bool startReceive();
uint8_t radioState();
// Approximate RSSI in half-dBm, using TI's typical 74 dB offset. False on SPI error.
bool radioRssiHalfDb(int16_t& value);
// Fixed RX-only profiles: 0=MCZ, 1..3=Chamberlain exploratory frequencies.
bool selectReceiveProfile(uint8_t profile);
uint32_t radioFrequencyHz();
// Caller must stop RX and release GDO0 before driving it.
bool prepareTransmit();
bool startTransmit();
bool stopTransmit();
bool finishTransmit();
