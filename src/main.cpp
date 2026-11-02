#include <Arduino.h>
#include <driver/rmt.h>
#include "cc1101_radio.h"
#include "radio_config.h"
#include "mcz_decoder.h"
#include "mcz_pulses.h"
#include "mcz_encoder.h"

namespace {
constexpr rmt_channel_t CHANNEL = RMT_CHANNEL_0;
constexpr uint16_t IDLE_US = 3000;
constexpr uint8_t FILTER_APB_TICKS = 255; // ~3.19 us at 80 MHz; not 255 us
constexpr size_t HARDWARE_ITEMS = 8 * RMT_MEM_ITEM_NUM;
RingbufHandle_t rxBuffer = nullptr;
int32_t pulses[HARDWARE_ITEMS * 2];
bool ready = false, diagnostics = false, rawOnce = false, triggerEnabled = false;
bool captureWindow = false;
uint32_t captureStarted = 0, lastTrigger = 0;
uint32_t validCount = 0, pulseCount = 0, blocks = 0, dropped = 0;
uint32_t lastSample = 0, lastReport = 0, previousPulses = 0;
int16_t minRssi = 32767, maxRssi = -32768;
uint32_t rssiSamples = 0, rssiErrors = 0;
uint32_t txCount = 0, lastTx = 0;
char rememberedIds[16][33] = {};
const char* rememberedResults[16] = {};
unsigned nextId = 0;
bool initCapture();

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
    captureWindow = false;
    if (rmt_rx_stop(CHANNEL) != ESP_OK) { ready = false; return false; }
    if (!prepareTransmit()) { ready = false; return false; }
    if (rmt_driver_uninstall(CHANNEL) != ESP_OK) { ready = false; return false; }
    rxBuffer = nullptr;
    rmt_config_t cfg = {};
    cfg.rmt_mode = RMT_MODE_TX; cfg.channel = CHANNEL;
    cfg.gpio_num = gpio_num_t(PIN_GDO0); cfg.clk_div = 80; cfg.mem_block_num = 8;
    cfg.tx_config.idle_output_en = true; cfg.tx_config.idle_level = RMT_IDLE_LEVEL_LOW;
    bool installed = false, sent = false;
    if (rmt_config(&cfg) == ESP_OK && rmt_driver_install(CHANNEL, 0, 0) == ESP_OK) {
        installed = true;
        uint32_t hz = 0;
        if (rmt_get_counter_clock(CHANNEL, &hz) == ESP_OK && hz == 1000000 && startTransmit()) {
            if (rmt_write_items(CHANNEL, items.data(), items.size(), false) == ESP_OK)
                sent = rmt_wait_tx_done(CHANNEL, pdMS_TO_TICKS(1500)) == ESP_OK;
        }
    }
    if (installed) rmt_tx_stop(CHANNEL); // configured idle LOW => OOK off
    // Keep the ESP32 driving LOW until the radio has actually left TX. If SPI
    // fails, retain this output and require reboot rather than float TX data.
    if (!stopTransmit()) { ready = false; return false; }
    if (installed) rmt_driver_uninstall(CHANNEL);
    pinMode(PIN_GDO0, INPUT);
    ready = finishTransmit() && initCapture() && startReceive();
    if (sent) ++txCount;
    return sent && ready;
}

void appStatus() {
    Serial.printf("APP {\"type\":\"status\",\"ready\":%s,\"frequency\":%lu,\"tx_count\":%lu}\n",
        ready && radioFrequencyHz() == 434500000 ? "true" : "false",
        (unsigned long)radioFrequencyHz(), (unsigned long)txCount);
}
void appCommand(const char* line) {
    // !TX + 32 hex request ID + space + 14 hex frame. No arbitrary radio settings.
    if (strlen(line) != 51 || strncmp(line, "!TX ", 4) || line[36] != ' ') return;
    for (unsigned i=4;i<51;++i) if (i != 36 && !isxdigit(static_cast<unsigned char>(line[i]))) return;
    char id[33]; memcpy(id, line+4, 32); id[32] = 0;
    const char* result = nullptr;
    for (unsigned i=0;i<16;++i) if (!strcmp(id, rememberedIds[i])) result = rememberedResults[i];
    if (!result) {
        uint8_t raw[7];
        for (unsigned i=0;i<7;++i) { char hex[3] = {line[37+i*2], line[38+i*2], 0}; raw[i] = strtoul(hex, nullptr, 16); }
        MCZFrame f;
        if (!parseMCZBytes(raw, 7, f) || f.remoteId != 0xC8CC02) result = "rejected";
        else if (!ready || radioFrequencyHz() != 434500000) result = "unavailable";
        else if (lastTx && uint32_t(millis()-lastTx) < 2000) result = "busy";
        else { lastTx = millis(); result = transmitCommand(raw) ? "sent" : "uncertain"; }
        memcpy(rememberedIds[nextId], id, 33); rememberedResults[nextId] = result; nextId = (nextId+1)%16;
    }
    Serial.printf("APP {\"type\":\"result\",\"id\":\"%s\",\"result\":\"%s\"}\n", id, result);
}

void clearRxBuffer() {
    if (!rxBuffer) return;
    size_t size;
    while (void* item = xRingbufferReceive(rxBuffer, &size, 0)) vRingbufferReturnItem(rxBuffer, item);
}
bool startCapture() {
    clearRxBuffer();
    return rmt_rx_start(CHANNEL, true) == ESP_OK;
}
bool initCapture() {
    rmt_config_t config = {};
    config.rmt_mode = RMT_MODE_RX;
    config.channel = CHANNEL;
    config.gpio_num = gpio_num_t(PIN_GDO0);
    // APB 80 MHz / 80 => 1 us duration ticks. Filter uses undivided APB ticks.
    config.flags = 0;
    config.clk_div = 80;
    config.mem_block_num = 8;
    config.rx_config.idle_threshold = IDLE_US;
    config.rx_config.filter_en = true;
    config.rx_config.filter_ticks_thresh = FILTER_APB_TICKS;
    if (rmt_config(&config) != ESP_OK) return false;
    if (rmt_driver_install(CHANNEL, 32768, 0) != ESP_OK) return false;
    uint32_t counterHz = 0;
    if (rmt_get_counter_clock(CHANNEL, &counterHz) != ESP_OK || counterHz != 1000000) {
        Serial.printf("RMT CLOCK ERROR actual=%lu expected=1000000\n", (unsigned long)counterHz);
        return false;
    }
    if (rmt_get_ringbuf_handle(CHANNEL, &rxBuffer) != ESP_OK || !rxBuffer) return false;
    Serial.printf("CAPTURE=RMT tick_us=1 filter_apb_ticks=%u idle_us=%u capacity_items=%u\n",
        FILTER_APB_TICKS, IDLE_US, unsigned(HARDWARE_ITEMS));
    return startCapture();
}
void resetDiagnosticWindow() {
    lastReport = millis(); lastSample = lastReport; previousPulses = pulseCount;
    minRssi = 32767; maxRssi = -32768; rssiSamples = 0; rssiErrors = 0;
}
void diagnosticTick() {
    if (!diagnostics && !triggerEnabled) return;
    uint32_t now = millis();
    if (uint32_t(now - lastSample) >= 10) {
        lastSample = now;
        int16_t rssi;
        if (radioRssiHalfDb(rssi)) {
            if (rssi < minRssi) minRssi = rssi;
            if (rssi > maxRssi) maxRssi = rssi;
            ++rssiSamples;
            if (triggerEnabled && !captureWindow && uint32_t(now - lastTrigger) >= 1000 && rssi >= -170) {
                captureWindow = true; captureStarted = now; lastTrigger = now;
                Serial.printf("TRIGGER_START t_ms=%lu RSSI=%.1f dBm_est\n", (unsigned long)now, rssi / 2.0);
            }
        } else ++rssiErrors;
    }
    if (captureWindow && uint32_t(now - captureStarted) >= 700) captureWindow = false;
    if (diagnostics && uint32_t(now - lastReport) >= 1000) {
        Serial.printf("DIAG t_ms=%lu FREQ_HZ=%lu window_ms=%lu pulses=%lu blocks=%lu dropped=%lu samples=%lu spi_errors=%lu STATE=%02X VALID=%lu",
            (unsigned long)now, (unsigned long)radioFrequencyHz(), (unsigned long)(now - lastReport),
            (unsigned long)(pulseCount - previousPulses), (unsigned long)blocks, (unsigned long)dropped,
            (unsigned long)rssiSamples, (unsigned long)rssiErrors, radioState(), (unsigned long)validCount);
        if (rssiSamples) Serial.printf(" RSSI_min=%.1f RSSI_max=%.1f dBm_est", minRssi / 2.0, maxRssi / 2.0);
        Serial.println(); resetDiagnosticWindow();
    }
}
void printFrame(const MCZFrame& f) {
    ++validCount;
    Serial.printf("MCZ FRAME VALID #%lu ID=%06lX Mode=%u Power=%u Fan1=%u Fan2=%u User=%u Reserved=%u CRC=OK\n",
        (unsigned long)validCount, (unsigned long)f.remoteId, f.mode, f.power, f.fan1, f.fan2, f.user, f.reserved);
    Serial.print("Raw:");
    for (uint8_t b : f.raw) Serial.printf(" %02X", b);
    Serial.println();
}
void receiveBlock() {
    size_t bytes = 0;
    auto* items = static_cast<rmt_item32_t*>(xRingbufferReceive(rxBuffer, &bytes, 0));
    if (!items) return;
    ++blocks;
    const size_t length = bytes / sizeof(rmt_item32_t);
    size_t count = 0;
    bool valid = bytes % sizeof(rmt_item32_t) == 0 && length < HARDWARE_ITEMS;
    for (size_t i = 0; valid && i < length; ++i) {
        if (!items[i].duration0) break;
        valid = appendMeasuredPulse(pulses, HARDWARE_ITEMS * 2, count, items[i].level0, items[i].duration0);
        if (!items[i].duration1) break;
        valid = valid && appendMeasuredPulse(pulses, HARDWARE_ITEMS * 2, count, items[i].level1, items[i].duration1);
    }
    vRingbufferReturnItem(rxBuffer, items);
    // Legacy RMT omits the final idle level. Its duration is a lower bound,
    // not an exact measurement. Include it so the last Manchester half is kept.
    if (valid && count && uint32_t(pulses[count - 1] < 0 ? -pulses[count - 1] : pulses[count - 1]) < IDLE_US)
        valid = appendMeasuredPulse(pulses, HARDWARE_ITEMS * 2, count, pulses[count - 1] < 0, IDLE_US);
    if (!valid) { ++dropped; Serial.println("RMT_DROPPED: bloc plein ou invalide"); return; }
    pulseCount += count;
    if (radioFrequencyHz() == 434500000)
        for (const auto& f : decodeMCZFrames(pulses, count)) printFrame(f);
    if ((rawOnce && count >= 20) || (captureWindow && count >= 80)) {
        Serial.printf("RMT_CAPTURE t_ms=%lu pulses=%u idle_tail_min_us=%u\n",
            (unsigned long)millis(), unsigned(count), IDLE_US);
        Serial.println("RX_BURST_BEGIN");
        for (size_t i = 0; i < count; ++i) Serial.printf("%+ld\n", (long)pulses[i]);
        Serial.println("RX_BURST_END");
        rawOnce = false;
    }
}
}

void setup() {
    Serial.begin(115200); delay(500);
    Serial.println("MCZ USB RX/TX. Aucun envoi au demarrage. j=statut application; !TX=commande explicite.");
    if (!MCZ_WIRING_CONFIRMED) { Serial.println("STOP: cablage non confirme"); return; }
    if (!initRadio()) { Serial.println("ERREUR CC1101"); return; }
    if (!initCapture()) { Serial.println("ERREUR capture RMT"); return; }
    ready = startReceive();
    if (!ready) rmt_rx_stop(CHANNEL);
    Serial.println(ready ? "RX READY 434.50MHz OOK RMT" : "ERREUR entree RX");
}
void loop() {
    if (Serial.available()) {
        const int c = Serial.read();
        static char line[80]; static unsigned used = 0; static bool collecting = false, overflow = false;
        static uint32_t lastChar = 0;
        if (collecting && uint32_t(millis()-lastChar) > 1000) collecting = false;
        lastChar = millis();
        if (c == '!' && !collecting) { collecting = true; used = 0; overflow = false; }
        if (collecting) {
            if (c == '\n') {
                line[used] = 0;
                if (!overflow) appCommand(line);
                collecting = false;
            } else if (c != '\r') {
                if (used < sizeof(line)-1) line[used++] = char(c); else overflow = true;
            }
            return;
        }
        if (c == 'j') appStatus();
        if (c >= '0' && c <= '3' && ready) {
            const bool stopped = rmt_rx_stop(CHANNEL) == ESP_OK;
            captureWindow = false;
            ready = stopped && selectReceiveProfile(uint8_t(c - '0')) && startCapture();
            resetDiagnosticWindow();
            Serial.printf("RX_PROFILE %s FREQ_HZ=%lu STATE=%02X\n", ready ? "OK" : "FAILED_REBOOT_REQUIRED",
                (unsigned long)radioFrequencyHz(), radioState());
        }
        if (c == 'r' && ready) { rawOnce = true; Serial.println("Capture RMT brute armee"); }
        if (c == 't' && ready) {
            triggerEnabled = !triggerEnabled; captureWindow = false; lastTrigger = millis();
            Serial.println(triggerEnabled ? "TRIGGER ON threshold=-85dBm RMT window=700ms min_pulses=80" : "TRIGGER OFF");
        }
        if (c == 'd' && ready) {
            diagnostics = !diagnostics; resetDiagnosticWindow();
            Serial.println(diagnostics ? "DIAG ON RSSI estime, non calibre" : "DIAG OFF");
        }
        if (c == 's' && ready) Serial.printf("STATE=%02X VALID=%lu FREQ_HZ=%lu CAPTURE=RMT BLOCKS=%lu DROPPED=%lu\n",
            radioState(), (unsigned long)validCount, (unsigned long)radioFrequencyHz(), (unsigned long)blocks, (unsigned long)dropped);
    }
    if (!ready) { delay(10); return; }
    diagnosticTick();
    // Limit work per loop so RSSI sampling and serial commands keep progressing.
    for (unsigned i = 0; i < 4; ++i) receiveBlock();
    delay(1);
}
