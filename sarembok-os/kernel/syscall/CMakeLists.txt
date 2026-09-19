add_library(sarembok_syscall STATIC sarembok_syscall.c)
target_include_directories(sarembok_syscall PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(sarembok_syscall PUBLIC
    sarembok_agent_process sarembok_memory_arena)
