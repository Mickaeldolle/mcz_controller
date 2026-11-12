#pragma once
#include <string.h>

namespace MczAlexa {
inline bool consume(const char*& input, const char* token) {
    input += strspn(input, " \t\r\n");
    const size_t length = strlen(token);
    if (strncmp(input, token, length) != 0) return false;
    input += length;
    return true;
}

inline bool isPowerRequest(const char* body) {
    return consume(body, "{") && consume(body, "\"on\"") && consume(body, ":")
        && (consume(body, "true") || consume(body, "false")) && consume(body, "}")
        && body[strspn(body, " \t\r\n")] == '\0';
}

inline const char* profileKey(bool on) {
    return on ? "5:5:3" : "off";
}
}
