#if defined(MCZ_OTA)

#include "mcz_ota.h"
#include <algorithm>
#include <Arduino.h>
#include <Preferences.h>
#include <esp_image_format.h>
#include <esp_ota_ops.h>
#include <esp_system.h>
#include <esp_timer.h>
#include <mbedtls/md.h>
#include <mbedtls/sha256.h>

namespace {
constexpr char STORAGE[] = "mcz-ota";
constexpr char KEY_NAME[] = "key-v1";
constexpr size_t KEY_LENGTH = 43;
constexpr size_t NONCE_LENGTH = 32;
constexpr size_t DIGEST_LENGTH = 32;
constexpr int64_t CHALLENGE_US = 60000000;
constexpr uint32_t UPLOAD_MS = 90000;
char key[KEY_LENGTH + 1] = {};
char nonce[NONCE_LENGTH + 1] = {};
int64_t issuedAt = 0;

bool validKey(const char* value) {
    if (strlen(value) != KEY_LENGTH) return false;
    for (size_t i = 0; i < KEY_LENGTH; ++i) {
        const char c = value[i];
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z')
            || (c >= '0' && c <= '9') || c == '-' || c == '_')) return false;
    }
    return true;
}

void hexEncode(const uint8_t* data, size_t length, char* hex) {
    constexpr char digits[] = "0123456789abcdef";
    for (size_t i = 0; i < length; ++i) {
        hex[2 * i] = digits[data[i] >> 4];
        hex[2 * i + 1] = digits[data[i] & 15];
    }
    hex[2 * length] = '\0';
}

bool equalDigest(const char* first, const char* second) {
    unsigned difference = 0;
    for (size_t i = 0; i < 2 * DIGEST_LENGTH; ++i) difference |= uint8_t(first[i] ^ second[i]);
    return difference == 0;
}

template<size_t N>
bool readHexHeader(httpd_req_t* request, const char* name, char (&value)[N]) {
    if (httpd_req_get_hdr_value_len(request, name) != N - 1
        || httpd_req_get_hdr_value_str(request, name, value, N) != ESP_OK) return false;
    for (size_t i = 0; i < N - 1; ++i) {
        const char c = value[i];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
    }
    return true;
}

bool challengeIsCurrent() {
    return nonce[0] && esp_timer_get_time() - issuedAt < CHALLENGE_US;
}

bool validAuthorization(httpd_req_t* request, char (&digest)[2 * DIGEST_LENGTH + 1]) {
    char suppliedNonce[NONCE_LENGTH + 1], suppliedMac[2 * DIGEST_LENGTH + 1];
    if (!challengeIsCurrent() || !readHexHeader(request, "X-MCZ-Nonce", suppliedNonce)
        || strcmp(nonce, suppliedNonce) || !readHexHeader(request, "X-MCZ-SHA256", digest)
        || !readHexHeader(request, "X-MCZ-MAC", suppliedMac)) return false;

    constexpr char prefix[] = "mcz-ota-v1:";
    char message[sizeof(prefix) + NONCE_LENGTH + 1 + 2 * DIGEST_LENGTH];
    const int length = snprintf(message, sizeof(message), "%s%s:%s", prefix, nonce, digest);
    uint8_t mac[DIGEST_LENGTH];
    const auto* sha256 = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    if (mbedtls_md_hmac(sha256, reinterpret_cast<const uint8_t*>(key), KEY_LENGTH,
        reinterpret_cast<const uint8_t*>(message), length, mac) != 0) return false;
    char expectedMac[2 * DIGEST_LENGTH + 1];
    hexEncode(mac, sizeof(mac), expectedMac);
    return equalDigest(suppliedMac, expectedMac);
}

esp_err_t sendJson(httpd_req_t* request, const char* status, const char* body) {
    httpd_resp_set_status(request, status);
    httpd_resp_set_type(request, "application/json");
    httpd_resp_set_hdr(request, "Cache-Control", "no-store");
    return httpd_resp_sendstr(request, body);
}

esp_err_t rejectRequest(httpd_req_t* request, const char* status, const char* body) {
    httpd_resp_set_hdr(request, "Connection", "close");
    sendJson(request, status, body);
    // A rejected request can still have unread bytes. Close instead of draining them.
    return ESP_FAIL;
}

esp_err_t receiveFirmware(httpd_req_t* request, esp_ota_handle_t handle, const char* expectedDigest) {
    mbedtls_sha256_context hash;
    mbedtls_sha256_init(&hash);
    esp_err_t result = mbedtls_sha256_starts_ret(&hash, 0) == 0 ? ESP_OK : ESP_FAIL;
    const uint32_t started = millis();
    size_t remaining = request->content_len;
    uint8_t buffer[1024];
    while (remaining && result == ESP_OK) {
        if (uint32_t(millis() - started) >= UPLOAD_MS) {
            result = ESP_ERR_TIMEOUT;
            break;
        }
        const int received = httpd_req_recv(request, reinterpret_cast<char*>(buffer),
                                          std::min(remaining, sizeof(buffer)));
        if (received <= 0) {
            result = received == HTTPD_SOCK_ERR_TIMEOUT ? ESP_ERR_TIMEOUT : ESP_FAIL;
            break;
        }
        if (mbedtls_sha256_update_ret(&hash, buffer, received) != 0) {
            result = ESP_FAIL;
            break;
        }
        result = esp_ota_write(handle, buffer, received);
        remaining -= received;
    }
    if (result == ESP_OK) {
        uint8_t digest[DIGEST_LENGTH];
        if (mbedtls_sha256_finish_ret(&hash, digest) == 0) {
            char hex[2 * DIGEST_LENGTH + 1];
            hexEncode(digest, sizeof(digest), hex);
            if (!equalDigest(hex, expectedDigest)) result = ESP_ERR_INVALID_CRC;
        } else {
            result = ESP_FAIL;
        }
    }
    mbedtls_sha256_free(&hash);
    return result;
}

esp_err_t installFirmware(httpd_req_t* request, const esp_partition_t* partition, const char* digest) {
    esp_ota_handle_t handle;
    esp_err_t result = esp_ota_begin(partition, OTA_WITH_SEQUENTIAL_WRITES, &handle);
    if (result != ESP_OK) return result;

    result = receiveFirmware(request, handle, digest);
    if (result != ESP_OK) {
        esp_ota_abort(handle);
        return result;
    }
    result = esp_ota_end(handle);
    if (result != ESP_OK) return result;

    esp_app_desc_t description;
    result = esp_ota_get_partition_description(partition, &description);
    if (result != ESP_OK) return result;

    // The authenticated body must cover the entire bootable image.
    const esp_partition_pos_t position{partition->address, partition->size};
    esp_image_metadata_t image = {};
    result = esp_image_get_metadata(&position, &image);
    if (result != ESP_OK) return result;
    if (image.image_len != request->content_len) return ESP_ERR_OTA_VALIDATE_FAILED;
    return esp_ota_set_boot_partition(partition);
}
}

void initOta() {
    Preferences storage;
    if (storage.begin(STORAGE, true) && storage.isKey(KEY_NAME)) {
        if (storage.getString(KEY_NAME, key, sizeof(key)) != sizeof(key) || !validKey(key)) key[0] = 0;
    }
}

bool otaConfigured() {
    return key[0] != 0;
}

const char* configureOta(const char* arguments) {
    const bool clear = !strcmp(arguments, "CLEAR");
    const char* value = !strncmp(arguments, "SET ", 4) ? arguments + 4 : "";
    if (!clear && !validKey(value)) return "rejected";

    Preferences storage;
    if (!storage.begin(STORAGE, false)) return "storage_error";
    const bool saved = clear ? !storage.isKey(KEY_NAME) || storage.remove(KEY_NAME)
                             : storage.putString(KEY_NAME, value) == KEY_LENGTH;
    if (!saved) return "storage_error";
    if (clear) memset(key, 0, sizeof(key));
    else memcpy(key, value, sizeof(key));
    nonce[0] = 0;
    return "saved";
}

esp_err_t otaChallenge(httpd_req_t* request) {
    if (request->content_len || httpd_req_get_hdr_value_len(request, "Transfer-Encoding")) {
        return rejectRequest(request, "400 Bad Request", "{\"error\":\"unexpected_body\"}");
    }
    if (!challengeIsCurrent()) {
        uint8_t random[NONCE_LENGTH / 2];
        esp_fill_random(random, sizeof(random));
        hexEncode(random, sizeof(random), nonce);
        issuedAt = esp_timer_get_time();
    }
    char body[64];
    snprintf(body, sizeof(body), "{\"nonce\":\"%s\"}", nonce);
    return sendJson(request, "200 OK", body);
}

esp_err_t otaUpload(httpd_req_t* request) {
    const auto* partition = esp_ota_get_next_update_partition(nullptr);
    if (!partition) return rejectRequest(request, "503 Service Unavailable", "{\"error\":\"no_ota_partition\"}");
    if (!request->content_len || request->content_len > partition->size
        || httpd_req_get_hdr_value_len(request, "Transfer-Encoding")) {
        return rejectRequest(request, "400 Bad Request", "{\"error\":\"invalid_firmware_size\"}");
    }
    char digest[2 * DIGEST_LENGTH + 1];
    if (!validAuthorization(request, digest)) {
        return rejectRequest(request, "403 Forbidden", "{\"error\":\"ota_authorization_failed\"}");
    }
    if (!beginRadioMaintenance()) return rejectRequest(request, "409 Conflict", "{\"error\":\"radio_busy\"}");

    nonce[0] = 0;
    Serial.println("OTA start");
    const esp_err_t result = installFirmware(request, partition, digest);
    if (result != ESP_OK) {
        endRadioMaintenance();
        Serial.printf("OTA failed: %s\n", esp_err_to_name(result));
        return rejectRequest(request, "422 Unprocessable Content", "{\"error\":\"firmware_update_failed\"}");
    }
    Serial.println("OTA installed; rebooting");
    sendJson(request, "200 OK", "{\"result\":\"rebooting\"}");
    delay(250);
    esp_restart();
}

#endif
