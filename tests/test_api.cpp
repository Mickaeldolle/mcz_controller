#include "mcz_api.h"
#include <assert.h>
#include <string.h>

namespace {
unsigned calls = 0;
bool complete = true;
uint8_t last[7];

bool send(const uint8_t* frame) {
    ++calls;
    memcpy(last, frame, sizeof(last));
    return complete;
}
}

int main() {
    const auto* on = mczProfile("1:1");
    const auto* off = mczProfile("off");
    const auto* fan2Off = mczProfile("3:5:0");
    assert(on && off && fan2Off && mczProfileCount() == 221);
    assert(mczProfile("3%3A5%3a0") == fan2Off);
    assert(mczProfileForFrame("C8CC02AD8059C9") == fan2Off);
    const auto* derived = mczProfile("1%3A1%3A0");
    assert(derived && mczProfileForFrame("C8CC022580CBF8") == derived);
    assert(mczProfileForFrame("C8CC02D5B0EE6A") == mczProfile("5:6:6"));
    assert(mczProfile("5:6:6"));
    assert(!mczProfile("1:1:7") && !mczProfile("0:1:0") && !mczProfile("1:0:0"));
    assert(!mczProfile("3:5:0%3"));
    assert(mczProfileForFrame("c8cc0225b87ca3") == on);
    assert(!mczProfileForFrame("C8CC028FB88E16"));
    assert(!mczProfile("1:6"));
    MczApi api;
    const char* first = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
    const char* second = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
    const char* third = "cccccccccccccccccccccccccccccccc";
    const char* fourth = "dddddddddddddddddddddddddddddddd";
    assert(api.execute("BAD", on, true, 0, send) == MczResult::Rejected);
    assert(api.execute(first, nullptr, true, 0, send) == MczResult::Rejected);
    assert(api.execute(first, on, true, 0, send) == MczResult::Sent);
    assert(!memcmp(last, on->frame, sizeof(last)));
    assert(api.execute(first, on, true, 5000, send) == MczResult::Sent);
    assert(api.execute(first, off, true, 5000, send) == MczResult::Rejected);
    assert(api.execute(second, off, true, 2999, send) == MczResult::Busy);
    assert(api.execute(second, off, true, 3000, send) == MczResult::Busy);
    assert(api.execute(third, off, false, 3000, send) == MczResult::Unavailable);
    complete = false;
    assert(api.execute(fourth, off, true, 3000, send) == MczResult::Uncertain);
    assert(!memcmp(last, off->frame, sizeof(last)));
    assert(api.execute(fourth, off, true, 9000, send) == MczResult::Uncertain);
    assert(calls == 2);
}
