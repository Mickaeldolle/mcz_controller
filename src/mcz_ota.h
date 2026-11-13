#pragma once
#include <esp_http_server.h>

void initOta();
bool otaConfigured();
const char* configureOta(const char* arguments);
esp_err_t otaChallenge(httpd_req_t* request);
esp_err_t otaUpload(httpd_req_t* request);

bool beginRadioMaintenance();
void endRadioMaintenance();
bool radioMaintenanceActive();
