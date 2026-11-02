#include "mcz_pulses.h"
#include <limits.h>
bool appendMeasuredPulse(int32_t* out, size_t capacity, size_t& count,
                         bool high, uint32_t durationUs) {
    if (!out || count > capacity || durationUs > INT32_MAX) return false;
    if (!durationUs) return true;
    const int32_t value = high ? int32_t(durationUs) : -int32_t(durationUs);
    if (count && (out[count - 1] > 0) == high) {
        const int64_t merged = int64_t(out[count - 1]) + value;
        if (merged > INT32_MAX || merged < -int64_t(INT32_MAX)) return false;
        out[count - 1] = int32_t(merged);
        return true;
    }
    if (count == capacity) return false;
    out[count++] = value;
    return true;
}
