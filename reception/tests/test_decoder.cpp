#include "mcz_decoder.h"
#include "mcz_crc.h"
#include <assert.h>
#include <stdio.h>
#include <vector>
#include <random>

// Offline fixture builder only; no GPIO/radio/TX code linked into this executable.
static std::vector<int32_t> capture(const uint8_t* bytes, bool invert = false, int scale = 100,
                                  int corruptWord = -1, int corruptBit = -1) {
    std::vector<int32_t> p;
    auto append = [&](bool high, int us) {
        high ^= invert;
        int32_t d = high ? us : -us;
        if (!p.empty() && (p.back() > 0) == high) p.back() += d;
        else p.push_back(d);
    };
    append(true, 103000);
    for (int repeat = 0; repeat < 5; ++repeat) {
        for (int i = 0; i < 7; ++i) {
            append(false, 414 * scale / 100); append(true, 828 * scale / 100);
            unsigned payload = (unsigned(bytes[i]) << 1) | (i == 0);
            unsigned parity = 0;
            for (unsigned b = payload; b; b >>= 1) parity ^= b & 1;
            unsigned word = 0x801 | (payload << 2) | (parity << 1);
            if (i == corruptWord && corruptBit >= 0) word ^= 1u << corruptBit;
            for (int b = 11; b >= 0; --b) {
                bool one = (word >> b) & 1;
                append(one, 414 * scale / 100); append(!one, 414 * scale / 100);
            }
        }
        append(false, 3712);
    }
    return p;
}
int main() {
    const uint8_t check[] = "123456789";
    assert(crc16Xmodem(check, 9) == 0x31C3);
    uint8_t b[] = {0xA1,0xB2,0xC3,0xCD,0xA0,0,0};
    uint16_t crc = crc16Xmodem(b, 5); b[5] = crc >> 8; b[6] = crc;
    // Independently checked using Python binascii.crc_hqx.
    assert(crc == 0x36C9);
    MCZFrame f;
    assert(parseMCZBytes(b, 7, f));
    assert(f.remoteId == 0xA1B2C3 && f.mode == 1 && f.power == 3 && f.fan1 == 6 && f.fan2 == 4 && f.user == 2);
    assert(!parseMCZBytes(nullptr, 7, f));
    assert(!parseMCZBytes(b, 6, f));
    for (bool inv : {false, true}) for (int scale : {90,100,108}) {
        auto p = capture(b, inv, scale);
        auto frames = decodeMCZFrames(p.data(), p.size());
        assert(frames.size() == 5);
        for (auto& frame : frames) assert(frame.remoteId == 0xA1B2C3 && frame.crcValid);
    }
    for (int bit : {0,1,2,3,11}) {
        auto p = capture(b, false, 100, 0, bit);
        assert(decodeMCZFrames(p.data(), p.size()).empty());
    }
    // RMT omits the final idle level: use its known lower bound at frame end.
    for (bool inv : {false, true}) {
        auto packet = capture(b, inv);
        size_t boundary = 1;
        while (boundary < packet.size() && packet[boundary] < 2500 && packet[boundary] > -2500) ++boundary;
        assert(boundary < packet.size());
        packet.resize(boundary);
        packet.push_back(inv ? 3000 : -3000);
        assert(decodeMCZFrames(packet.data(), packet.size()).size() == 1);
    }
    b[6] ^= 1;
    auto bad = capture(b);
    assert(decodeMCZFrames(bad.data(), bad.size()).empty());
    b[6] ^= 1;
    auto p = capture(b); p.resize(50);
    assert(decodeMCZFrames(p.data(), p.size()).empty());
    assert(decodeMCZFrames(nullptr, 0).empty());
    assert(decodeMCZFrames(p.data(), 2049).empty());
    std::mt19937 rng(42);
    for (int t = 0; t < 100; ++t) {
        std::vector<int32_t> noise(2048);
        for (auto& x : noise) x = int32_t(rng() % 10001) - 5000;
        assert(decodeMCZFrames(noise.data(), noise.size()).empty());
    }
    puts("PASS: CRC, fields, 5 repeats, inversion, timing, parity/start/stop/flag, bad CRC, truncation, bounds, noise");
}
