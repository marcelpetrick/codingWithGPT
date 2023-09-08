#!/bin/bash

while true; do
    clear

    # Locate all Python processes and fetch their PIDs
    python_pids=$(pgrep -f python)

    echo "Python processes and their file descriptors:"
    echo "---------------------------------------------"

    # Iterate over each PID and display the number of file descriptors and tasks
    for pid in $python_pids; do
        # Check if /proc/$pid exists to avoid potential errors
        if [ -d "/proc/$pid" ]; then
            fd_count=$(ls /proc/$pid/fd | wc -l)
            task_count=$(ls /proc/$pid/task | wc -l)
            echo "PID: $pid - File Descriptors: $fd_count - Tasks: $task_count"
        fi
    done

    sleep 1
done
