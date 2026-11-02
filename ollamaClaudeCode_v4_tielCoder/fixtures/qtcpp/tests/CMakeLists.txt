add_executable(tst_backlog tst_backlog.cpp)
target_link_libraries(tst_backlog PRIVATE backlog Qt6::Test)
add_test(NAME tst_backlog COMMAND tst_backlog)
