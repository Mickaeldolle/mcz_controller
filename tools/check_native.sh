#!/bin/sh
# Offline only: no USB, GPIO, upload or RF access.
set -eu
cd "$(dirname "$0")/.."
build_dir="$(mktemp -d)"
trap 'rm -rf -- "$build_dir"' EXIT HUP INT TERM
cxx="${CXX:-g++}"
python3 tools/build_profiles.py "$build_dir/mcz_profiles.h"

for suite in decoder encoder pulses api; do
    test_dir=tests
    case "$suite" in
        decoder|pulses) test_dir=reception/tests ;;
    esac
    "$cxx" -std=c++11 -Wall -Wextra -Werror \
        -fsanitize=address,undefined -fno-omit-frame-pointer -Iinclude -Isrc -Ireception -I"$build_dir" \
        "$test_dir/test_$suite.cpp" reception/mcz_decoder.cpp src/mcz_crc.cpp \
        src/mcz_encoder.cpp reception/mcz_pulses.cpp src/mcz_api.cpp -o "$build_dir/test_$suite"
    "$build_dir/test_$suite"
done
