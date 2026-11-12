#pragma once

#include <stddef.h>

constexpr size_t AMBIENT_STATUS_SIZE = 72;

void beginTemperatureDisplay();
void pollTemperatureDisplay();
void formatAmbientStatus(char (&json)[AMBIENT_STATUS_SIZE]);
