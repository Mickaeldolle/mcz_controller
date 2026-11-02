#pragma once
#include <stddef.h>
#include <stdint.h>
// Append a measured level, merging equal adjacent levels without losing time.
// A zero duration is an RMT terminator. False means invalid duration/capacity.
bool appendMeasuredPulse(int32_t* out, size_t capacity, size_t& count,
                         bool high, uint32_t durationUs);
