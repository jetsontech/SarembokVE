# Sarembok OS ? seL4 port target.
# This CMake build is invoked by Antigravity after the seL4 toolchain is set up.
# It builds against seL4 headers; it is NOT expected to build on a plain host.
cmake_minimum_required(VERSION 3.20)
project(sarembok_kernel C)
set(CMAKE_C_STANDARD 11)
add_subdirectory(agent_process)
add_subdirectory(memory_arena)
add_subdirectory(syscall)
add_executable(sarembok_kernel_main main.c)
target_link_libraries(sarembok_kernel_main PRIVATE
    sarembok_agent_process sarembok_memory_arena sarembok_syscall)
