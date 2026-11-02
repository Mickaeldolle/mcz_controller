#include "mcz_encoder.h"
#include "mcz_decoder.h"

bool encodeMCZCommand(const uint8_t raw[7], std::vector<int32_t>& p) {
    p.clear();
    MCZFrame f;
    if (!parseMCZBytes(raw, 7, f) || f.remoteId != 0xC8CC02) return false;
    auto add = [&](int32_t d) {
        if (!p.empty() && ((p.back() > 0) == (d > 0))) p.back() += d;
        else p.push_back(d);
    };
    add(103000);
    for (unsigned repeat = 0; repeat < 5; ++repeat) {
        for (unsigned n = 0; n < 7; ++n) {
            add(-414); add(828); // Preamble on EVERY byte, including first.
            const unsigned data = (unsigned(raw[n]) << 1) | (n == 0);
            unsigned parity = 0;
            for (unsigned b = 0; b < 9; ++b) parity ^= (data >> b) & 1;
            const unsigned word = 0x801 | (data << 2) | (parity << 1);
            for (int b = 11; b >= 0; --b) {
                const bool one = (word >> b) & 1;
                add(one ? 414 : -414); add(one ? -414 : 414);
            }
        }
        add(-3712);
    }
    return true;
}
