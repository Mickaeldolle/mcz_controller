#if defined(MCZ_TEMPERATURE_DISPLAY)
#include "mcz_temperature.h"

#include <Adafruit_SSD1306.h>
#include <Arduino.h>
#include <DHT.h>
#include <Wire.h>
#include <cmath>

namespace {
constexpr int DHT_PIN = 26;
constexpr int SDA_PIN = 21;
constexpr int SCL_PIN = 22;
constexpr uint32_t I2C_FREQUENCY = 100000;
constexpr uint32_t SAMPLE_INTERVAL_MS = 3000;

DHT sensor(DHT_PIN, DHT11);
Adafruit_SSD1306 display(128, 64, &Wire, -1, I2C_FREQUENCY, I2C_FREQUENCY);
bool displayReady = false;
uint32_t lastSample = 0;
int displayedTemperature = -2;
int displayedHumidity = -2;

int roundedMeasurement(float value, float maximum) {
    return std::isfinite(value) && value >= 0 && value <= maximum
        ? int(std::lround(value)) : -1;
}

void drawMeasurements(int temperature, int humidity) {
    display.clearDisplay();
    display.setCursor(0, 0);
    display.setTextSize(1);
    display.println(F("Temp. ambiante"));
    if (temperature < 0 && humidity < 0) {
        display.setCursor(0, 24);
        display.println(F("Sonde indisponible"));
    } else {
        display.setCursor(0, 14);
        display.setTextSize(3);
        if (temperature >= 0) display.print(temperature);
        else display.print(F("--"));
        display.print(' ');
        display.write(uint8_t(248));  // Degree sign in CP437.
        display.print('C');

        display.setCursor(0, 50);
        display.setTextSize(1);
        display.print(F("Humidit"));
        display.write(uint8_t(130));  // Accented e in CP437.
        display.setCursor(62, 46);
        display.setTextSize(2);
        if (humidity >= 0) display.print(humidity);
        else display.print(F("--"));
        display.print(F(" %"));
    }
    display.display();
}
}

void beginTemperatureDisplay() {
    sensor.begin();
    lastSample = millis();
    if (Wire.begin(SDA_PIN, SCL_PIN, I2C_FREQUENCY)) {
        Wire.setTimeOut(20);
        for (const uint8_t address : {0x3C, 0x3D}) {
            Wire.beginTransmission(address);
            if (Wire.endTransmission() != 0) continue;
            displayReady = display.begin(SSD1306_SWITCHCAPVCC, address, false, false);
            if (displayReady) Serial.printf("TEMP OLED address=0x%02X\n", unsigned(address));
            break;
        }
    }

    if (!displayReady) {
        Serial.println(F("TEMP OLED indisponible"));
        return;
    }

    display.cp437(true);
    display.setTextColor(SSD1306_WHITE);
    display.clearDisplay();
    display.setCursor(0, 0);
    display.print(F("Lecture en cours"));
    display.display();
}

void pollTemperatureDisplay() {
    const uint32_t now = millis();
    if (uint32_t(now - lastSample) < SAMPLE_INTERVAL_MS) return;
    lastSample = now;

    const int temperature = roundedMeasurement(sensor.readTemperature(), 50);
    const int humidity = roundedMeasurement(sensor.readHumidity(), 100);
    if (temperature >= 0) Serial.printf("TEMP DHT11=%d C\n", temperature);
    else Serial.println(F("TEMP DHT11 indisponible"));
    if (humidity >= 0) Serial.printf("TEMP DHT11 humidity=%d %%\n", humidity);
    else Serial.println(F("TEMP DHT11 humidity indisponible"));

    if (displayReady && (displayedTemperature != temperature || displayedHumidity != humidity)) {
        drawMeasurements(temperature, humidity);
        displayedTemperature = temperature;
        displayedHumidity = humidity;
    }
}
#endif
