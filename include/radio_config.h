#pragma once
#include <stdint.h>
// ESP32 38-pin board + E07-M1101D. Wiring confirmed by user on 2026-10-30.
constexpr int PIN_SCK = 18;
constexpr int PIN_MISO = 19;
constexpr int PIN_MOSI = 23;
constexpr int PIN_CS = 5;
constexpr int PIN_GDO0 = 27;
// No radio access until deliberately enabled after checking board and wiring.
#ifndef MCZ_WIRING_CONFIRMED
#define MCZ_WIRING_CONFIRMED 0
#endif
