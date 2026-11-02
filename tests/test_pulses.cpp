#include "mcz_pulses.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
int main() {
    int32_t out[3] = {};
    size_t n = 0;
    assert(appendMeasuredPulse(out, 3, n, true, 414));
    assert(appendMeasuredPulse(out, 3, n, true, 414));
    assert(n == 1 && out[0] == 828);
    assert(appendMeasuredPulse(out, 3, n, false, 414));
    assert(appendMeasuredPulse(out, 3, n, true, 414));
    assert(n == 3 && out[1] == -414 && out[2] == 414);
    assert(!appendMeasuredPulse(out, 3, n, false, 414));
    assert(n == 3 && out[2] == 414);
    assert(appendMeasuredPulse(out, 3, n, true, 0));
    assert(n == 3);
    n = 0;
    assert(appendMeasuredPulse(out, 3, n, true, INT32_MAX));
    assert(!appendMeasuredPulse(out, 3, n, true, 1));
    assert(out[0] == INT32_MAX);
    n = 0;
    assert(appendMeasuredPulse(out, 3, n, false, INT32_MAX));
    assert(!appendMeasuredPulse(out, 3, n, false, 1));
    assert(!appendMeasuredPulse(nullptr, 3, n, true, 1));
    assert(!appendMeasuredPulse(out, 3, n, true, UINT32_MAX));
    puts("PASS: pulse levels, merging, terminator, capacity, signed bounds");
}
