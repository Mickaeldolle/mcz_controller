#include "mcz_network.h"
#include "mcz_profiles.h"
#include "mcz_web_assets.h"
#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>
#include <atomic>
#include <esp_http_server.h>
#include <lwip/sockets.h>
#if defined(MCZ_OTA)
#include "mcz_ota.h"
#endif
#if defined(MCZ_ALEXA_TEST)
#include <fauxmoESP.h>
#endif
#if defined(MCZ_ALEXA_RADIO)
#include "mcz_alexa.h"
#include <esp_system.h>
#endif
#if defined(MCZ_TEMPERATURE_DISPLAY)
#include "mcz_temperature.h"
#endif

namespace {
MczDispatch command = nullptr;
#if defined(MCZ_ALEXA_RADIO)
struct AlexaRequest {
    bool on;
    uint32_t receivedAt;
};
QueueHandle_t alexaRequests = nullptr;

void queueAlexaPower(bool on) {
#if defined(MCZ_OTA)
    if (radioMaintenanceActive()) {
        Serial.println("ALEXA result=unavailable");
        return;
    }
#endif
    const AlexaRequest request{on, millis()};
    if (alexaRequests) xQueueOverwrite(alexaRequests, &request);
    else Serial.println("ALEXA result=unavailable");
}

void pollAlexaRadio(bool connected) {
    AlexaRequest request;
    if (!alexaRequests || xQueueReceive(alexaRequests, &request, 0) != pdTRUE) return;
    if (!connected || WiFi.status() != WL_CONNECTED || uint32_t(millis() - request.receivedAt) > 500) {
        Serial.println("ALEXA result=expired");
        return;
    }
    char id[33];
    snprintf(id, sizeof(id), "%08lx%08lx%08lx%08lx",
             (unsigned long)esp_random(), (unsigned long)esp_random(),
             (unsigned long)esp_random(), (unsigned long)esp_random());
    const char* profile = MczAlexa::profileKey(request.on);
    const auto result = command(id, mczProfile(profile));
    Serial.printf("ALEXA profile=%s result=%s\n", profile, mczResultName(result));
}
#endif

#if defined(MCZ_ALEXA_TEST)
constexpr uint16_t HTTP_PORT = 8080;
fauxmoESP alexaTest;
bool alexaConfigured = false;
bool alexaConnected = false;

void pollAlexaTest(bool connected) {
    if (connected && !alexaConfigured) {
        alexaTest.setPort(80);
        alexaTest.addDevice("Test Alexa MCZ");
        alexaTest.onSetState([](unsigned char id, const char* name, bool state, unsigned char value) {
            Serial.printf("ALEXA id=%u name=%s state=%s value=%u\n",
                          unsigned(id), name, state ? "ON" : "OFF", unsigned(value));
#if defined(MCZ_ALEXA_RADIO)
            if (id == 0) queueAlexaPower(state);
#endif
        });
        alexaConfigured = true;
    }
    if (connected != alexaConnected) {
        alexaConnected = connected;
        alexaTest.enable(connected);
#if defined(MCZ_ALEXA_RADIO)
        Serial.printf("ALEXA radio %s\n", connected ? "ready on TCP 80" : "paused");
#else
        Serial.printf("ALEXA test %s\n", connected ? "ready on TCP 80" : "paused");
#endif
    }
    if (connected) alexaTest.handle();
}
#else
constexpr uint16_t HTTP_PORT = 80;
#endif
constexpr char STORAGE[] = "mcz-network";
constexpr char SETTINGS[] = "credentials-v1";
struct Credentials {
    char ssid[33];
    char password[64];
    char key[65];
};
Credentials credentials = {};
httpd_handle_t server = nullptr;
#if defined(MCZ_OTA)
constexpr uint16_t OTA_PORT = 8081;
httpd_handle_t otaServer = nullptr;
#endif
std::atomic<bool> ready{false};
std::atomic<uint32_t> count{0};
uint32_t lastStart = 0;

bool validKey(const char* key) {
    if (strlen(key) != 64) return false;
    for (size_t i = 0; i < 64; ++i)
        if (!((key[i] >= '0' && key[i] <= '9') || (key[i] >= 'a' && key[i] <= 'f'))) return false;
    return true;
}

int nibble(char value) {
    if (value >= '0' && value <= '9') return value - '0';
    if (value >= 'a' && value <= 'f') return value - 'a' + 10;
    return -1;
}

bool decodeText(const char* hex, char* output, size_t capacity, size_t minimum) {
    if (!hex) return false;
    const size_t length = strlen(hex);
    if (length % 2 || length / 2 < minimum || length / 2 >= capacity) return false;
    for (size_t i = 0; i < length; i += 2) {
        const int high = nibble(hex[i]), low = nibble(hex[i + 1]);
        if (high < 0 || low < 0 || (!high && !low)) return false;
        output[i / 2] = char(high * 16 + low);
    }
    return true;
}

void connectStation() {
    WiFi.mode(WIFI_OFF);
    if (!credentials.ssid[0]) return;
    WiFi.mode(WIFI_STA);
    WiFi.setMinSecurity(WIFI_AUTH_WPA2_PSK);
    WiFi.setAutoReconnect(true);
    WiFi.begin(credentials.ssid, credentials.password);
}

esp_err_t sendJson(httpd_req_t* request, const char* status, const char* payload) {
    httpd_resp_set_status(request, status);
    httpd_resp_set_type(request, "application/json");
    httpd_resp_set_hdr(request, "Cache-Control", "no-store");
    return httpd_resp_sendstr(request, payload);
}

bool localClient(httpd_req_t* request) {
    sockaddr_storage peer = {};
    socklen_t length = sizeof(peer);
    if (getpeername(httpd_req_to_sockfd(request), reinterpret_cast<sockaddr*>(&peer), &length) != 0)
        return false;
    uint32_t address;
    if (peer.ss_family == AF_INET) {
        address = reinterpret_cast<sockaddr_in*>(&peer)->sin_addr.s_addr;
    } else if (peer.ss_family == AF_INET6) {
        const auto& ipv6 = reinterpret_cast<sockaddr_in6*>(&peer)->sin6_addr;
        constexpr uint8_t mappedPrefix[] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xFF, 0xFF};
        if (memcmp(ipv6.s6_addr, mappedPrefix, sizeof(mappedPrefix))) return false;
        memcpy(&address, ipv6.s6_addr + 12, sizeof(address));
    } else {
        return false;
    }
    const uint32_t mask = WiFi.subnetMask();
    return WiFi.status() == WL_CONNECTED && mask
        && (address & mask) == (uint32_t(WiFi.localIP()) & mask);
}

bool localRequest(httpd_req_t* request, uint16_t port = HTTP_PORT) {
    if (!localClient(request)) {
        sendJson(request, "403 Forbidden", "{\"error\":\"local_subnet_required\"}");
        return false;
    }
    const String ip = WiFi.localIP().toString();
    const String authority = ip + ":" + port;
    char host[22], origin[29];
    if (httpd_req_get_hdr_value_str(request, "Host", host, sizeof(host)) != ESP_OK
        || (authority != host && (port != 80 || ip != host))) {
        sendJson(request, "403 Forbidden", "{\"error\":\"invalid_host\"}");
        return false;
    }
    const String expectedOrigin = String("http://") + ip;
    if (httpd_req_get_hdr_value_len(request, "Origin")
        && (httpd_req_get_hdr_value_str(request, "Origin", origin, sizeof(origin)) != ESP_OK
            || (expectedOrigin + ":" + port != origin
                && (port != 80 || expectedOrigin != origin)))) {
        sendJson(request, "403 Forbidden", "{\"error\":\"invalid_origin\"}");
        return false;
    }
    return true;
}

bool authorized(httpd_req_t* request) {
    if (!localRequest(request)) return false;
    char header[72];
    if (httpd_req_get_hdr_value_len(request, "Authorization") == 71
        && httpd_req_get_hdr_value_str(request, "Authorization", header, sizeof(header)) == ESP_OK
        && !memcmp(header, "Bearer ", 7)) {
        unsigned difference = 0;
        for (size_t i = 0; i < 64; ++i) difference |= uint8_t(header[i + 7] ^ credentials.key[i]);
        if (!difference) return true;
    }
    httpd_resp_set_hdr(request, "WWW-Authenticate", "Bearer");
    sendJson(request, "401 Unauthorized", "{\"error\":\"unauthorized\"}");
    return false;
}

struct WebAsset {
    const char* path;
    const char* type;
    const char* body;
};

constexpr WebAsset assets[] = {
    {"/", "text/html; charset=utf-8", nullptr},
    {"/style.css", "text/css; charset=utf-8", MczWeb::STYLE},
    {"/app.js", "text/javascript; charset=utf-8", MczWeb::SCRIPT},
};

esp_err_t webResponse(httpd_req_t* request) {
    if (!localRequest(request)) return ESP_OK;
    const auto& asset = *static_cast<const WebAsset*>(request->user_ctx);
    httpd_resp_set_type(request, asset.type);
    httpd_resp_set_hdr(request, "Cache-Control", "no-store");
    httpd_resp_set_hdr(request, "X-Content-Type-Options", "nosniff");
    // Keep a valid Origin on same-origin command POSTs.
    httpd_resp_set_hdr(request, "Referrer-Policy", "same-origin");
    httpd_resp_set_hdr(request, "Cross-Origin-Resource-Policy", "same-origin");
    httpd_resp_set_hdr(request, "Content-Security-Policy",
        "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'");
    if (asset.body) return httpd_resp_sendstr(request, asset.body);

    // The local test page gets the configured key at response time.
    esp_err_t result = httpd_resp_sendstr_chunk(request, MczWeb::PAGE_PREFIX);
    if (result == ESP_OK) result = httpd_resp_sendstr_chunk(request, credentials.key);
    if (result == ESP_OK) result = httpd_resp_sendstr_chunk(request, MczWeb::PAGE_SUFFIX);
    if (result == ESP_OK) result = httpd_resp_send_chunk(request, nullptr, 0);
    return result;
}

esp_err_t statusResponse(httpd_req_t* request) {
    if (!authorized(request)) return ESP_OK;
    String body = String("{\"version\":1,\"ready\":") + (ready.load() ? "true" : "false")
        + ",\"frequency\":" + String(MCZ_FREQUENCY_HZ) + ",\"tx_count\":" + String(count.load());
#if defined(MCZ_TEMPERATURE_DISPLAY)
    char ambient[AMBIENT_STATUS_SIZE];
    formatAmbientStatus(ambient);
#else
    constexpr char ambient[] = "";
#endif
    constexpr char profilesStart[] = ",\"profiles\":[";
    if (!body.reserve(body.length() + strlen(ambient) + sizeof(profilesStart) - 1 + mczProfileCount() * 8 + 2))
        return sendJson(request, "503 Service Unavailable", "{\"error\":\"status_unavailable\"}");
    body += ambient;
    body += profilesStart;
    for (size_t i = 0; i < mczProfileCount(); ++i) {
        if (i) body += ',';
        body += '"';
        body += mczProfileAt(i).key;
        body += '"';
    }
    body += "]}";
    return sendJson(request, "200 OK", body.c_str());
}

const char* resultStatus(MczResult result) {
    switch (result) {
    case MczResult::Sent: return "200 OK";
    case MczResult::Busy: return "409 Conflict";
    case MczResult::Unavailable: return "503 Service Unavailable";
    case MczResult::Uncertain: return "500 Internal Server Error";
    case MczResult::Rejected: return "422 Unprocessable Content";
    }
    return "500 Internal Server Error";
}

esp_err_t commandResponse(httpd_req_t* request) {
    if (!authorized(request)) return ESP_OK;
    char query[80], id[33], key[10];
    if (request->content_len != 0 || httpd_req_get_hdr_value_len(request, "Transfer-Encoding")
        || httpd_req_get_url_query_str(request, query, sizeof(query)) != ESP_OK
        || httpd_query_key_value(query, "id", id, sizeof(id)) != ESP_OK || !validRequestId(id)
        || httpd_query_key_value(query, "profile", key, sizeof(key)) != ESP_OK) {
        return sendJson(request, "400 Bad Request", "{\"error\":\"invalid_command\"}");
    }
    const char* separator = strchr(query, '&');
    if (!separator || strchr(separator + 1, '&'))
        return sendJson(request, "400 Bad Request", "{\"error\":\"invalid_command\"}");
    const auto result = command(id, mczProfile(key));
    char body[90];
    snprintf(body, sizeof(body), "{\"id\":\"%s\",\"result\":\"%s\"}", id, mczResultName(result));
    return sendJson(request, resultStatus(result), body);
}

bool stopServer(httpd_handle_t& handle) {
    if (handle && httpd_stop(handle) != ESP_OK) return false;
    handle = nullptr;
    return true;
}

void startServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = HTTP_PORT;
    // Legacy RMT interrupts must be allocated and freed on the same core.
    config.core_id = xPortGetCoreID();
    config.stack_size = 6144;
    config.max_open_sockets = 4;
    config.recv_wait_timeout = 2;
    config.send_wait_timeout = 2;
    config.lru_purge_enable = true;
    if (httpd_start(&server, &config) != ESP_OK) return;
    httpd_uri_t status = {};
    status.uri = "/api/v1/status";
    status.method = HTTP_GET;
    status.handler = statusResponse;
    httpd_uri_t request = {};
    request.uri = "/api/v1/command";
    request.method = HTTP_POST;
    request.handler = commandResponse;
    if (httpd_register_uri_handler(server, &status) != ESP_OK
        || httpd_register_uri_handler(server, &request) != ESP_OK) {
        stopServer(server);
        return;
    }
    for (const auto& asset : assets) {
        httpd_uri_t route = {};
        route.uri = asset.path;
        route.method = HTTP_GET;
        route.handler = webResponse;
        route.user_ctx = const_cast<WebAsset*>(&asset);
        if (httpd_register_uri_handler(server, &route) != ESP_OK) {
            stopServer(server);
            return;
        }
    }
}

#if defined(MCZ_OTA)
void startOtaServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = OTA_PORT;
    ++config.ctrl_port;
    config.stack_size = 6144;
    config.max_open_sockets = 2;
    config.max_uri_handlers = 2;
    config.recv_wait_timeout = 2;
    config.send_wait_timeout = 2;
    config.lru_purge_enable = true;
    if (httpd_start(&otaServer, &config) != ESP_OK) return;

    httpd_uri_t challenge = {};
    challenge.uri = "/api/v1/ota/challenge";
    challenge.method = HTTP_GET;
    challenge.handler = [](httpd_req_t* req) { return localRequest(req, OTA_PORT) ? otaChallenge(req) : ESP_OK; };
    httpd_uri_t upload = {};
    upload.uri = "/api/v1/ota";
    upload.method = HTTP_POST;
    upload.handler = [](httpd_req_t* req) { return localRequest(req, OTA_PORT) ? otaUpload(req) : ESP_FAIL; };
    if (httpd_register_uri_handler(otaServer, &challenge) != ESP_OK
        || httpd_register_uri_handler(otaServer, &upload) != ESP_OK) {
        stopServer(otaServer);
        return;
    }
    Serial.printf("OTA ready on TCP %u\n", unsigned(OTA_PORT));
}
#endif
}

void initNetwork(MczDispatch dispatch) {
    command = dispatch;
#if defined(MCZ_OTA)
    initOta();
#endif
#if defined(MCZ_ALEXA_RADIO)
    alexaRequests = xQueueCreate(1, sizeof(AlexaRequest));
#endif
    WiFi.persistent(false);

    Preferences storage;
    if (storage.begin(STORAGE, true)) {
        if (storage.getBytesLength(SETTINGS) != sizeof(credentials)
            || storage.getBytes(SETTINGS, &credentials, sizeof(credentials)) != sizeof(credentials)
            || !memchr(credentials.ssid, 0, sizeof(credentials.ssid))
            || !memchr(credentials.password, 0, sizeof(credentials.password))
            || credentials.key[64] || !validKey(credentials.key)) credentials = {};
        storage.end();
    }
    connectStation();
}

void pollNetwork(bool radioReady, uint32_t txCount) {
    const bool connected = credentials.ssid[0] && WiFi.status() == WL_CONNECTED;
#if defined(MCZ_ALEXA_TEST)
    pollAlexaTest(connected);
#endif
#if defined(MCZ_ALEXA_RADIO)
    pollAlexaRadio(connected);
#endif
    if (!credentials.ssid[0]) return;
    ready = radioReady;
    count = txCount;
    if (connected) {
        const uint32_t now = millis();
        if (uint32_t(now - lastStart) >= 1000) {
            lastStart = now;
            if (!server) startServer();
#if defined(MCZ_OTA)
            if (!otaServer && otaConfigured()) startOtaServer();
#endif
        }
    } else {
#if defined(MCZ_OTA)
        stopServer(otaServer);
#endif
        stopServer(server);
    }
}

void printNetworkStatus() {
    const bool connected = server && WiFi.status() == WL_CONNECTED;
    Serial.printf("APP {\"type\":\"network\",\"configured\":%s,\"connected\":%s,\"ip\":\"%s\",\"port\":%u}\n",
                  credentials.ssid[0] ? "true" : "false", connected ? "true" : "false",
                  connected ? WiFi.localIP().toString().c_str() : "", unsigned(HTTP_PORT));
}

void configureNetwork(char* arguments) {
    Credentials updated = {};
    const bool clear = !strcmp(arguments, "CLEAR");
    bool valid = clear;
    if (!clear) {
        char* tail = nullptr;
        const char* ssid = strtok_r(arguments, " ", &tail);
        const char* password = strtok_r(nullptr, " ", &tail);
        const char* key = strtok_r(nullptr, " ", &tail);
        valid = decodeText(ssid, updated.ssid, sizeof(updated.ssid), 1)
            && decodeText(password, updated.password, sizeof(updated.password), 8)
            && key && validKey(key) && !strtok_r(nullptr, " ", &tail);
        if (valid) memcpy(updated.key, key, sizeof(updated.key));
    }
    bool saved = false;
    Preferences storage;
#if defined(MCZ_OTA)
    const bool otaStopped = !valid || stopServer(otaServer);
#else
    constexpr bool otaStopped = true;
#endif
    if (valid && otaStopped && stopServer(server) && storage.begin(STORAGE, false)) {
        saved = clear ? !storage.isKey(SETTINGS) || storage.remove(SETTINGS)
                      : storage.putBytes(SETTINGS, &updated, sizeof(updated)) == sizeof(updated);
        storage.end();
    }
    if (saved) {
        credentials = updated;
        connectStation();
    }
    Serial.printf("APP {\"type\":\"network_config\",\"result\":\"%s\"}\n",
                  saved ? "saved" : valid ? "storage_error" : "rejected");
}

#if defined(MCZ_OTA)
void configureNetworkOta(const char* arguments) {
    // Join the HTTP task before changing its credentials or challenge.
    const char* result = stopServer(otaServer) ? configureOta(arguments) : "unavailable";
    Serial.printf("APP {\"type\":\"ota_config\",\"result\":\"%s\"}\n", result);
}
#endif
