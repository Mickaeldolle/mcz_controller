#pragma once
#include "mcz_api.h"

using MczDispatch = MczResult (*)(const char*, const MczProfile*);

void initNetwork(MczDispatch dispatch);
void pollNetwork(bool radioReady, uint32_t txCount);
void printNetworkStatus();
void configureNetwork(char* arguments);
#if defined(MCZ_OTA)
void configureNetworkOta(const char* arguments);
#endif
