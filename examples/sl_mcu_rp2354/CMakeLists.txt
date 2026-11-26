# cmsynth on the RP2354 (sl_mcu_rp2354), Arm Cortex-M33

cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.3.0)
set(toolchainVersion 15_2_Rel1)
set(picotoolVersion 2.3.0)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================

# Arm cores (rp2350-riscv would run on the Hazard3 cores)
set(PICO_PLATFORM rp2350)

# Custom board header
set(PICO_BOARD_HEADER_DIRS "${CMAKE_SOURCE_DIR}/boards/include" CACHE STRING "Extra board header dirs")
set(PICO_BOARD sl_mcu_rp2354 CACHE STRING "Board type")

# System clock in kHz: overclocked, main.c raises the core voltage to 1.30 V
# (the RP2350 is rated for 150 MHz)
set(SYS_CLOCK_KHZ 320000 CACHE STRING "System clock in kHz")

# Voices, rendered on both cores
set(MAX_VOICES 32 CACHE STRING "Number of synth voices")

# TinyUSB from the repository (lib/tinyusb, symlinked here as tinyusb/), the
# same copy the STM32 example builds, instead of the one in the Pico SDK
set(PICO_TINYUSB_PATH ${CMAKE_CURRENT_LIST_DIR}/../../lib/tinyusb)

# Pull in Raspberry Pi Pico SDK (must be before project)
include(pico_sdk_import.cmake)

project(cmsynth C CXX ASM)

pico_sdk_init()

# The synth source shared by all targets (src/, symlinked here as cmsynth/)
set(CMSYNTH_SRC ${CMAKE_CURRENT_LIST_DIR}/cmsynth)

add_executable(cmsynth
    main.c
    usb_descriptors.c
    ${CMSYNTH_SRC}/synth.c
    ${CMSYNTH_SRC}/params.c
    ${CMSYNTH_SRC}/midi.c
)

target_include_directories(cmsynth PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}
    ${CMSYNTH_SRC}
)

target_compile_definitions(cmsynth PRIVATE
    SYS_CLOCK_KHZ=${SYS_CLOCK_KHZ}
    MAX_VOICES=${MAX_VOICES}
    PICO_CORE1_STACK_SIZE=0x1000
)

target_compile_options(cmsynth PRIVATE
    -O3
    -ffunction-sections
    -fdata-sections
)

# Generate header from PIO file
pico_generate_pio_header(cmsynth ${CMAKE_CURRENT_LIST_DIR}/i2s.pio)

target_link_libraries(cmsynth
    pico_stdlib
    pico_multicore
    hardware_vreg
    pico_unique_id
    hardware_dma
    hardware_pio
    hardware_clocks
    hardware_uart
    tinyusb_device
)

# Run everything from SRAM: no XIP cache misses in the audio path
pico_set_binary_type(cmsynth copy_to_ram)

# printf goes through main.c's non-blocking UART driver, not the SDK's
pico_enable_stdio_uart(cmsynth 0)
pico_enable_stdio_usb(cmsynth 0)

pico_add_extra_outputs(cmsynth)

# Print the size after building
get_filename_component(TOOLCHAIN_BIN_DIR ${CMAKE_C_COMPILER} DIRECTORY)
find_program(CMAKE_SIZE_UTIL arm-none-eabi-size HINTS ${TOOLCHAIN_BIN_DIR})
add_custom_command(TARGET cmsynth POST_BUILD
    COMMAND ${CMAKE_SIZE_UTIL} $<TARGET_FILE:cmsynth>
)
