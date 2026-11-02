#include "mcz_encoder.h"
#include "mcz_decoder.h"
#include "mcz_crc.h"
#include <cassert>
#include <cstdio>
int main() {
    uint8_t raw[] = {0xC8,0xCC,0x02,0x4F,0xB8,0x98,0x42};
    std::vector<int32_t> p;
    assert(encodeMCZCommand(raw, p));
    assert(p.size() < 1024);
    int64_t duration = 0;
    for (auto v : p) duration += v < 0 ? -v : v;
    assert(duration == 512790); // 103000 + 5 * (189*414 + 3712)
    const auto frames = decodeMCZFrames(p.data(), p.size());
    assert(frames.size() == 5);
    for (auto& f : frames) for (int i=0;i<7;++i) assert(f.raw[i] == raw[i]);
    raw[6] ^= 1;
    assert(!encodeMCZCommand(raw, p) && p.empty());
    assert(!encodeMCZCommand(nullptr, p));
    uint8_t off[] = {0xC8,0xCC,0x02,0x8C,0xB8,0xDB,0x45};
    assert(encodeMCZCommand(off, p));
    const auto stopped = decodeMCZFrames(p.data(), p.size());
    assert(stopped.size() == 5 && stopped[0].mode == 0);
    off[0] = 0xA1;
    const uint16_t crc = crc16Xmodem(off, 5);
    off[5] = crc >> 8; off[6] = crc;
    assert(!encodeMCZCommand(off, p)); // valid CRC, wrong remote
    puts("encoder tests PASS");
}
