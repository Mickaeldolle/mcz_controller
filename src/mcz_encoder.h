#pragma once
#include <stdint.h>
#include <vector>
// Exact replay of a CRC-validated frame from the known remote. No field synthesis.
bool encodeMCZCommand(const uint8_t raw[7], std::vector<int32_t>& pulses);
