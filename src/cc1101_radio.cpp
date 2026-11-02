#include "cc1101_radio.h"
#include "radio_config.h"
#include <Arduino.h>
#include <SPI.h>

namespace {
uint32_t currentFrequency = 434500000;
bool selectRadio() {
    SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
    digitalWrite(PIN_CS, LOW);
    uint32_t t = micros();
    while (digitalRead(PIN_MISO)) {
        if (uint32_t(micros() - t) > 10000) {
            digitalWrite(PIN_CS, HIGH); SPI.endTransaction(); return false;
        }
    }
    return true;
}
void releaseRadio() { digitalWrite(PIN_CS, HIGH); SPI.endTransaction(); }
bool writeReg(uint8_t a, uint8_t v) {
    if (!selectRadio()) return false;
    SPI.transfer(a); SPI.transfer(v); releaseRadio(); return true;
}
bool readReg(uint8_t a, uint8_t& v) {
    if (!selectRadio()) return false;
    SPI.transfer(a | (a >= 0x30 ? 0xC0 : 0x80));
    v = SPI.transfer(0); releaseRadio(); return true;
}
// STX is used only by the explicit USB command handler.
bool command(uint8_t c) {
    if (c != 0x30 && c != 0x34 && c != 0x35 && c != 0x36) return false;
    if (!selectRadio()) return false;
    SPI.transfer(c);
    if (c == 0x30) {
        uint32_t t = micros();
        while (digitalRead(PIN_MISO)) {
            if (uint32_t(micros() - t) > 10000) { releaseRadio(); return false; }
        }
    }
    releaseRadio(); return true;
}
}
uint32_t radioFrequencyHz() { return currentFrequency; }
static bool waitState(uint8_t state) {
    const uint32_t t = millis();
    do { if (radioState() == state) return true; delay(1); } while (millis() - t < 100);
    return false;
}
bool prepareTransmit() {
    if (currentFrequency != 434500000 || !command(0x36) || !waitState(1)) return false;
    // Disable the CC1101 output BEFORE the ESP32 starts driving this wire.
    uint8_t actual;
    if (!writeReg(0x02, 0x2E) || !readReg(0x02, actual) || actual != 0x2E) return false;
    if (!writeReg(0x22, 0x11) || !readReg(0x22, actual) || actual != 0x11) return false;
    // TI PATABLE: OOK off=0, on=nominal 0 dBm at 433 MHz.
    if (!selectRadio()) return false;
    SPI.transfer(0x7E); SPI.transfer(0); SPI.transfer(0x60); releaseRadio();
    if (!selectRadio()) return false;
    SPI.transfer(0xFE); const uint8_t off = SPI.transfer(0), on = SPI.transfer(0); releaseRadio();
    return off == 0 && on == 0x60;
}
bool startTransmit() { return command(0x35) && waitState(0x13); }
bool stopTransmit() { return command(0x36) && waitState(1); }
bool finishTransmit() {
    if (!stopTransmit()) return false;
    // GDO0 must already be an ESP32 input before restoring its RX output.
    uint8_t actual;
    return writeReg(0x02, 0x0D) && readReg(0x02, actual) && actual == 0x0D;
}
bool selectReceiveProfile(uint8_t profile) {
    const uint32_t frequencies[] = {434500000, 868300000, 868950000, 869850000};
    if (profile >= 4 || !command(0x36)) return false;
    uint32_t started = millis();
    while (radioState() != 0x01) {
        if (millis() - started >= 100) return false;
        delay(1);
    }
    const uint32_t freq = uint32_t((uint64_t(frequencies[profile]) * 65536 + 13000000) / 26000000);
    for (uint8_t i = 0; i < 3; ++i) {
        const uint8_t expected = uint8_t(freq >> (16 - 8 * i));
        uint8_t actual;
        if (!writeReg(0x0D + i, expected) || !readReg(0x0D + i, actual) || actual != expected) return false;
    }
    if (!startReceive()) return false;
    currentFrequency = frequencies[profile];
    return true;
}
uint8_t radioState() {
    uint8_t s = 0xFF;
    return readReg(0x35, s) ? (s & 0x1F) : 0xFF;
}
bool radioRssiHalfDb(int16_t& value) {
    uint8_t raw;
    if (!readReg(0x34, raw)) return false;
    value = (raw >= 128 ? int16_t(raw) - 256 : int16_t(raw)) - 148;
    return true;
}
bool startReceive() {
    if (!command(0x34)) return false;
    uint32_t t = millis();
    while (millis() - t < 100) { if (radioState() == 0x0D) return true; delay(1); }
    return false;
}
bool initRadio() {
    pinMode(PIN_CS, OUTPUT); digitalWrite(PIN_CS, HIGH);
    SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_CS);
    // TI reset sequence, then SRES; every SPI operation has a ready timeout.
    delayMicroseconds(5); digitalWrite(PIN_CS, LOW); delayMicroseconds(10);
    digitalWrite(PIN_CS, HIGH); delayMicroseconds(41);
    if (!command(0x30)) return false;
    delay(2);
    uint8_t part, version;
    if (!readReg(0x30, part) || !readReg(0x31, version) || part != 0 || version == 0 || version == 255) return false;
    Serial.printf("CC1101 PART=%02X VERSION=%02X\n", part, version);
    // 26 MHz crystal assumed; round(434.50e6 * 65536 / 26e6).
    const uint32_t freq = 1095207;
    const uint8_t regs[][2] = {
        {0x00,0x2E}, {0x01,0x2E}, {0x02,0x0D}, // GDO0 async RX, others high-Z
        {0x03,0x47}, // TI DN022: ADC retention setting for RX BW <=325 kHz
        {0x07,0x00}, {0x08,0x30}, // no packet processing, async serial
        {0x0A,0x00}, {0x0B,0x06}, {0x0C,0x00},
        {0x0D,uint8_t(freq >> 16)}, {0x0E,uint8_t(freq >> 8)}, {0x0F,uint8_t(freq)},
        {0x10,RX_MDMCFG4}, {0x11,0x83}, // BW 101.6 kHz, ~2399 baud at 26 MHz
        {0x12,0x30}, // ASK/OOK, no Manchester hardware or sync detection
        {0x13,0x00}, {0x14,0x00}, {0x17,0x00}, {0x18,0x18}, // autocal IDLE->RX
        {0x19,0x16}, {0x1B,0x03}, {0x1C,0x00}, {0x1D,0x91},
        {0x21,RX_FREND1}, {0x23,0xE9}, {0x24,0x2A}, {0x25,0x00}, {0x26,0x1F},
        {0x2C,0x81}, {0x2D,0x35} // TI DN022: TEST2/TEST1 for RX BW <=325 kHz
    };
    for (auto& r : regs) {
        uint8_t actual;
        if (!writeReg(r[0], r[1]) || !readReg(r[0], actual) || actual != r[1]) return false;
    }
    Serial.printf("RX_CONFIG FREQ_WORD=%06lX MDMCFG4=%02X FREND1=%02X BW_kHz=%.1f\n",
        (unsigned long)freq, RX_MDMCFG4, RX_FREND1,
        26000.0 / (8 * (4 + ((RX_MDMCFG4 >> 4) & 3)) * (1 << (RX_MDMCFG4 >> 6))));
    return true;
}
