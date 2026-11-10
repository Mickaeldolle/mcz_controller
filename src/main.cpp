#include <Arduino.h>
#include <atomic>
#include <driver/rmt.h>
#include "cc1101_radio.h"
#include "radio_config.h"
#include "mcz_encoder.h"
#include "mcz_network.h"
#include "mcz_profiles.h"

namespace {
constexpr rmt_channel_t CHANNEL = RMT_CHANNEL_0;
constexpr uint8_t MEMORY_BLOCKS = 8;
constexpr size_t HARDWARE_ITEMS = MEMORY_BLOCKS * RMT_MEM_ITEM_NUM;
std::atomic<bool> ready{false};
std::atomic<uint32_t> txCount{0};
SemaphoreHandle_t radioLock = nullptr;
MczApi api;

bool initTransmit() {
    rmt_config_t cfg = {};
    cfg.rmt_mode = RMT_MODE_TX;
    cfg.channel = CHANNEL;
    cfg.gpio_num = gpio_num_t(PIN_GDO0);
    cfg.clk_div = 80;
    cfg.mem_block_num = MEMORY_BLOCKS;
    cfg.tx_config.idle_output_en = true;
    cfg.tx_config.idle_level = RMT_IDLE_LEVEL_LOW;
    if (rmt_config(&cfg) != ESP_OK || rmt_driver_install(CHANNEL, 0, 0) != ESP_OK)
        return false;
    uint32_t hz = 0;
    return rmt_get_counter_clock(CHANNEL, &hz) == ESP_OK && hz == 1000000;
}

bool transmitCommand(const uint8_t raw[7]) {
    std::vector<int32_t> encoded;
    if (!encodeMCZCommand(raw, encoded)) return false;
    std::vector<rmt_item32_t> items;
    bool firstHalf = true;
    for (int32_t pulse : encoded) {
        uint32_t remaining = pulse > 0 ? pulse : -pulse;
        while (remaining) {
            uint16_t duration = remaining > 32767 ? 32767 : remaining;
            if (firstHalf) { rmt_item32_t item = {}; items.push_back(item); }
            auto& item = items.back();
            if (firstHalf) { item.duration0 = duration; item.level0 = pulse > 0; }
            else { item.duration1 = duration; item.level1 = pulse > 0; }
            firstHalf = !firstHalf; remaining -= duration;
        }
    }
    if (items.size() >= HARDWARE_ITEMS) return false;
    const bool sent = startTransmit()
        && rmt_write_items(CHANNEL, items.data(), items.size(), false) == ESP_OK
        && rmt_wait_tx_done(CHANNEL, pdMS_TO_TICKS(1500)) == ESP_OK;
    const bool stopped = rmt_tx_stop(CHANNEL) == ESP_OK;
    // Always try SIDLE, even on a failed or timed-out RMT transmission.
    // Keep GDO0 driven low at rest so OOK stays off if the SPI stop fails.
    const bool idle = stopTransmit();
    if (sent) ++txCount;
    const bool complete = sent && stopped && idle;
    ready = complete;
    return complete;
}

void appStatus() {
    Serial.printf("APP {\"type\":\"status\",\"version\":1,\"ready\":%s,\"frequency\":%lu,\"tx_count\":%lu}\n",
        ready.load() ? "true" : "false", (unsigned long)MCZ_FREQUENCY_HZ, (unsigned long)txCount.load());
}
MczResult dispatch(const char* id, const MczProfile* profile) {
    if (!profile) return MczResult::Rejected;
    if (!radioLock) return MczResult::Unavailable;
    if (xSemaphoreTake(radioLock, pdMS_TO_TICKS(50)) != pdTRUE) return MczResult::Busy;
    const auto result = api.execute(id, profile, ready.load(), millis(), transmitCommand);
    xSemaphoreGive(radioLock);
    return result;
}

void serialCommand(char* line) {
    if (!strcmp(line, "!NET")) {
        printNetworkStatus();
    } else if (!strncmp(line, "!WIFI ", 6)) {
        configureNetwork(line + 6);
    } else if (!strncmp(line, "!TX ", 4) && strlen(line) == 51 && line[36] == ' ') {
        line[36] = 0;
        const char* id = line + 4;
        if (!validRequestId(id)) return;
        const auto result = dispatch(id, mczProfileForFrame(line + 37));
        Serial.printf("APP {\"type\":\"result\",\"id\":\"%s\",\"result\":\"%s\"}\n",
                      id, mczResultName(result));
    }
}

void pollSerial() {
    static char line[272];
    static size_t used = 0;
    static bool collecting = false, overflow = false;
    static uint32_t lastChar = 0;
    for (unsigned i = 0; i < 32 && Serial.available(); ++i) {
        const int c = Serial.read();
        const uint32_t now = millis();
        if (collecting && uint32_t(now - lastChar) > 1000) {
            memset(line, 0, used);
            collecting = false;
        }
        lastChar = now;
        if (!collecting) {
            if (c == 'j') appStatus();
            if (c != '!') continue;
            collecting = true;
            overflow = false;
            used = 0;
        }
        if (c == '\n') {
            const size_t end = used && line[used - 1] == '\r' ? used - 1 : used;
            line[end] = 0;
            if (!overflow) serialCommand(line);
            memset(line, 0, used);
            collecting = false;
        } else if (c > 0 && used < sizeof(line) - 1) {
            line[used++] = char(c);
        } else {
            overflow = true;
        }
    }
}

}

void setup() {
    Serial.setRxBufferSize(512);
    Serial.begin(115200);
    delay(500);
    initNetwork(dispatch);
    Serial.println("MCZ API v1: USB j, !TX, !NET; Wi-Fi optional.");
    radioLock = xSemaphoreCreateMutex();
    if (!radioLock) { Serial.println("ERREUR verrou radio"); return; }
    if (!MCZ_WIRING_CONFIRMED) { Serial.println("STOP: cablage non confirme"); return; }
    pinMode(PIN_GDO0, INPUT);
    if (!initRadio()) { Serial.println("ERREUR CC1101"); return; }
    if (!initTransmit()) { Serial.println("ERREUR emission RMT"); return; }
    ready = true;
    Serial.println("TX READY 434.50MHz OOK RMT, CC1101 IDLE");
}
void loop() {
    pollSerial();
    pollNetwork(ready.load(), txCount.load());
    delay(1);
}
