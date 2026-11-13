#pragma once

#include <stddef.h>

constexpr size_t AMBIENT_STATUS_SIZE = 72;

void beginTemperatureDisplay();
void pollTemperatureDisplay(bool updatingFirmware = false);
void formatAmbientStatus(char (&json)[AMBIENT_STATUS_SIZE]);
