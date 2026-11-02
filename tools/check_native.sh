#!/bin/sh
# Offline only: no USB, GPIO, upload or RF access.
set -eu
cd "$(dirname "$0")/.."
build_dir="$(mktemp -d)"
trap 'rm -rf -- "$build_dir"' EXIT HUP INT TERM
cxx="${CXX:-g++}"

for suite in decoder encoder pulses; do
    "$cxx" -std=c++11 -Wall -Wextra -Werror \
        -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc \
        "tests/test_$suite.cpp" src/mcz_decoder.cpp src/mcz_crc.cpp \
        src/mcz_encoder.cpp src/mcz_pulses.cpp -o "$build_dir/test_$suite"
    "$build_dir/test_$suite"
done

"$cxx" -std=c++11 -Wall -Wextra -Werror -Isrc \
    tools/decode_capture.cpp src/mcz_decoder.cpp src/mcz_crc.cpp \
    -o "$build_dir/decode_capture"
MCZ_DECODER="$build_dir/decode_capture" python3 -m unittest discover -s tests -p test_tools.py -v
