#include "cc1101_radio.h"
#include "mcz_profiles.h"
#include "radio_config.h"
#include <Arduino.h>
#include <SPI.h>

namespace {
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
// STX is used only by the shared command handler.
bool command(uint8_t c) {
    if (c != 0x30 && c != 0x35 && c != 0x36) return false;
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
uint8_t radioState() {
    uint8_t state;
    return readReg(0x35, state) ? (state & 0x1F) : 0xFF;
}
bool waitState(uint8_t state) {
    const uint32_t t = millis();
    do { if (radioState() == state) return true; delay(1); } while (millis() - t < 100);
    return false;
}
}
bool startTransmit() { return command(0x35) && waitState(0x13); }
bool stopTransmit() { return command(0x36) && waitState(1); }
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
    constexpr uint32_t freq = (uint64_t(MCZ_FREQUENCY_HZ) * 65536 + 13000000) / 26000000;
    const uint8_t regs[][2] = {
        {0x00,0x2E}, {0x01,0x2E}, {0x02,0x2E}, // Disable GDO outputs before the ESP32 drives GDO0.
        {0x03,0x47}, // TI DN022: ADC retention setting for RX BW <=325 kHz
        {0x07,0x00}, {0x08,0x30}, // no packet processing, async serial
        {0x0A,0x00}, {0x0B,0x06}, {0x0C,0x00},
        {0x0D,uint8_t(freq >> 16)}, {0x0E,uint8_t(freq >> 8)}, {0x0F,uint8_t(freq)},
        {0x10,0xC6}, {0x11,0x83}, // ~2399 baud at 26 MHz
        {0x12,0x30}, // ASK/OOK, no Manchester hardware or sync detection
        {0x13,0x00}, {0x14,0x00}, {0x17,0x00}, {0x18,0x18}, // autocal IDLE->TX
        {0x19,0x16}, {0x1B,0x03}, {0x1C,0x00}, {0x1D,0x91},
        {0x21,0xB6}, {0x22,0x11}, {0x23,0xE9}, {0x24,0x2A}, {0x25,0x00}, {0x26,0x1F},
        {0x2C,0x81}, {0x2D,0x35} // TI DN022: TEST2/TEST1 for RX BW <=325 kHz
    };
    for (auto& r : regs) {
        uint8_t actual;
        if (!writeReg(r[0], r[1]) || !readReg(r[0], actual) || actual != r[1]) return false;
    }
    // TI PATABLE: OOK off=0, on=nominal 0 dBm at 433 MHz.
    if (!selectRadio()) return false;
    SPI.transfer(0x7E); SPI.transfer(0); SPI.transfer(0x60); releaseRadio();
    if (!selectRadio()) return false;
    SPI.transfer(0xFE); const uint8_t off = SPI.transfer(0), on = SPI.transfer(0); releaseRadio();
    return off == 0 && on == 0x60 && stopTransmit();
}
