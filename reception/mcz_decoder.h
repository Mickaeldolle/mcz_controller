#pragma once
#include <stddef.h>
#include <stdint.h>
#include <vector>
struct MCZFrame {
    uint32_t remoteId = 0;
    uint8_t mode = 0, power = 0, fan1 = 0, fan2 = 0, user = 0, reserved = 0;
    uint8_t raw[7] = {};
    bool crcValid = false;
};
bool parseMCZBytes(const uint8_t* bytes, size_t size, MCZFrame& out);
// Signed durations: positive HIGH, negative LOW. Input bounded to 2048 pulses.
std::vector<MCZFrame> decodeMCZFrames(const int32_t* pulses, size_t count);
