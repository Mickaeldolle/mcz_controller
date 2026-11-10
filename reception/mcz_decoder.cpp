#include "mcz_decoder.h"
#include "mcz_crc.h"
#include <string.h>

bool parseMCZBytes(const uint8_t* bytes, size_t size, MCZFrame& out) {
    if (!bytes || size != 7) return false;
    MCZFrame f;
    memcpy(f.raw, bytes, 7);
    f.remoteId = (uint32_t(bytes[0]) << 16) | (uint32_t(bytes[1]) << 8) | bytes[2];
    f.mode = bytes[3] & 3;
    f.power = (bytes[3] >> 2) & 7;
    f.fan1 = bytes[3] >> 5;
    f.fan2 = (bytes[4] >> 3) & 7;
    f.user = bytes[4] >> 6;
    f.reserved = bytes[4] & 7;
    f.crcValid = crc16Xmodem(bytes, 5) == ((uint16_t(bytes[5]) << 8) | bytes[6]);
    if (!f.crcValid) return false;
    out = f;
    return true;
}

static bool readFrame(const std::vector<int8_t>& h, size_t pos, bool invert, MCZFrame& f) {
    if (pos + 186 > h.size()) return false;
    auto level = [&](size_t i) { return h[i] < 0 ? -1 : (int(h[i]) ^ int(invert)); };
    uint8_t bytes[7];
    for (int n = 0; n < 7; ++n) {
        if (n) {
            if (level(pos) != 0 || level(pos + 1) != 1 || level(pos + 2) != 1) return false;
            pos += 3;
        }
        uint16_t word = 0;
        for (int b = 0; b < 12; ++b) {
            int a = level(pos++), c = level(pos++);
            if (a < 0 || c < 0 || a == c) return false;
            word = (word << 1) | a;
        }
        if ((word & 0x801) != 0x801 || ((word >> 2) & 1) != (n == 0)) return false;
        unsigned parity = 0;
        for (int b = 1; b <= 10; ++b) parity ^= (word >> b) & 1;
        if (parity) return false;
        bytes[n] = (word >> 3) & 255;
    }
    return parseMCZBytes(bytes, 7, f);
}

std::vector<MCZFrame> decodeMCZFrames(const int32_t* pulses, size_t count) {
    std::vector<MCZFrame> frames;
    if (!pulses || count > 2048) return frames;
    std::vector<int8_t> halves;
    halves.reserve(count * 3);
    for (size_t i = 0; i < count; ++i) {
        const int64_t d = pulses[i] < 0 ? -int64_t(pulses[i]) : pulses[i];
        const int8_t high = pulses[i] > 0;
        if (d >= 2500) {
            // A long idle can include the last LOW half of the stop bit.
            halves.push_back(high);
            halves.push_back(-1);
            continue;
        }
        int n = int((d + 207) / 414);
        int64_t err = d - n * 414;
        if (err < 0) err = -err;
        if (n < 1 || n > 3 || err > n * 104) halves.push_back(-1);
        else for (int j = 0; j < n; ++j) halves.push_back(high);
    }
    for (size_t i = 0; i + 186 <= halves.size(); ++i) {
        MCZFrame f;
        if (readFrame(halves, i, false, f) || readFrame(halves, i, true, f)) {
            frames.push_back(f);
            i += 185;
        }
    }
    return frames;
}
