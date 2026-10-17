# ⚠️ `command_frame.cpp` lives one level up, beside the README, because
#    `tests/test_stackchan_wire.py` reads it there and checks its literals
#    against the contract. It is anchored to this file's directory so the path
#    does not depend on CMake's handling of a bare `../`.
idf_component_register(
    SRCS "main.cpp" "servo.cpp" "leds.cpp" "zeros.cpp"
         "${CMAKE_CURRENT_LIST_DIR}/../command_frame.cpp"
    INCLUDE_DIRS "." ".."
)
