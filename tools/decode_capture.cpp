#include "mcz_decoder.h"
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <cstdio>
#include <climits>
int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "Usage: decode_capture capture.log\n"; return 2; }
    std::ifstream input(argv[1]);
    if (!input) { std::cerr << "Cannot open capture\n"; return 2; }
    std::string line;
    std::vector<int32_t> pulses;
    bool active = false;
    size_t found = 0;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line == "RX_BURST_BEGIN") { pulses.clear(); active = true; continue; }
        if (line == "RX_BURST_END" && active) {
            for (auto& f : decodeMCZFrames(pulses.data(), pulses.size())) {
                std::printf("ID=%06lX CRC=OK Raw:", (unsigned long)f.remoteId);
                for (auto b : f.raw) std::printf(" %02X", b);
                std::puts(""); ++found;
            }
            active = false; continue;
        }
        if (active) {
            try {
                size_t used;
                long long value = std::stoll(line, &used);
                if (used != line.size() || !value || value < -1000000 || value > 1000000 || pulses.size() >= 2048)
                    throw std::out_of_range("pulse");
                pulses.push_back(int32_t(value));
            } catch (...) { std::cerr << "Malformed/oversized capture\n"; return 2; }
        }
    }
    if (active) { std::cerr << "Truncated capture\n"; return 2; }
    std::printf("Valid frames: %zu\n", found);
    return found ? 0 : 1;
}
