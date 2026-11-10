#pragma once
#include <stddef.h>
#include <stdint.h>

struct MczProfile {
    const char* key;
    const char* hex;
    uint8_t frame[7];
};

const MczProfile* mczProfile(const char* key);
const MczProfile* mczProfileForFrame(const char* hex);
size_t mczProfileCount();
const MczProfile& mczProfileAt(size_t index);
bool validRequestId(const char* id);

enum class MczResult { Sent, Uncertain, Busy, Unavailable, Rejected };
const char* mczResultName(MczResult result);

// The caller serializes execute() with the radio operations.
class MczApi {
public:
    using Transmit = bool (*)(const uint8_t*);
    MczResult execute(const char* id, const MczProfile* profile, bool ready,
                      uint32_t now, Transmit transmit);

private:
    struct Request {
        char id[33];
        const MczProfile* profile;
        MczResult result;
    };
    Request history[16] = {};
    size_t next = 0;
    bool transmitted = false;
    uint32_t lastTx = 0;
};
