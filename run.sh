#!/bin/bash

# Activate the environment
source ~/job_search_env/bin/activate

# Start the Python script with nohup
nohup python3 job_search_main.py > job_search_main.log 2>&1 &

# Capture the PID
PID=$!

# Write PID + the old log content into the real log file
echo "PID: $PID" > job_search_main.log
cat temp_log.log >> job_search_main.log

# Remove the temporary log
rm temp_log.log

# Optional: Echo PID to screen too
echo "Started job_search_main.py with PID $PID"