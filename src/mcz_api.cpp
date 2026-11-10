#include "mcz_api.h"
#include "mcz_profiles.h"
#include <string.h>

const MczProfile* mczProfile(const char* key) {
    // The longest canonical key is flame:fan1:fan2, each a single digit.
    char canonical[6];
    size_t length = 0;
    for (; *key; ++key) {
        if (length == sizeof(canonical) - 1) return nullptr;
        if (key[0] == '%' && key[1] == '3' && (key[2] == 'A' || key[2] == 'a')) {
            canonical[length++] = ':';
            key += 2;
        } else {
            canonical[length++] = *key;
        }
    }
    canonical[length] = 0;
    for (const auto& profile : MCZ_PROFILES)
        if (!strcmp(canonical, profile.key)) return &profile;
    return nullptr;
}

const MczProfile* mczProfileForFrame(const char* hex) {
    if (strlen(hex) != 14) return nullptr;
    char canonical[15];
    for (size_t i = 0; i < 14; ++i)
        canonical[i] = hex[i] >= 'a' && hex[i] <= 'f' ? char(hex[i] - 'a' + 'A') : hex[i];
    canonical[14] = 0;
    for (const auto& profile : MCZ_PROFILES)
        if (!strcmp(canonical, profile.hex)) return &profile;
    return nullptr;
}

size_t mczProfileCount() { return sizeof(MCZ_PROFILES) / sizeof(MCZ_PROFILES[0]); }
const MczProfile& mczProfileAt(size_t index) { return MCZ_PROFILES[index]; }

bool validRequestId(const char* id) {
    if (strlen(id) != 32) return false;
    for (size_t i = 0; i < 32; ++i)
        if (!((id[i] >= '0' && id[i] <= '9') || (id[i] >= 'a' && id[i] <= 'f'))) return false;
    return true;
}

const char* mczResultName(MczResult result) {
    switch (result) {
    case MczResult::Sent: return "sent";
    case MczResult::Uncertain: return "uncertain";
    case MczResult::Busy: return "busy";
    case MczResult::Unavailable: return "unavailable";
    case MczResult::Rejected: return "rejected";
    }
    return "rejected";
}

MczResult MczApi::execute(const char* id, const MczProfile* profile, bool ready,
                         uint32_t now, Transmit transmit) {
    if (!validRequestId(id) || !profile) return MczResult::Rejected;
    for (const auto& request : history)
        if (!strcmp(id, request.id))
            return request.profile == profile ? request.result : MczResult::Rejected;

    MczResult result;
    if (!ready) result = MczResult::Unavailable;
    else if (transmitted && uint32_t(now - lastTx) < 3000) result = MczResult::Busy;
    else {
        transmitted = true;
        lastTx = now;
        result = transmit(profile->frame) ? MczResult::Sent : MczResult::Uncertain;
    }
    Request& request = history[next];
    memcpy(request.id, id, sizeof(request.id));
    request.profile = profile;
    request.result = result;
    next = (next + 1) % (sizeof(history) / sizeof(history[0]));
    return result;
}
