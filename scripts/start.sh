#!/bin/bash

SCRIPT_DIR=$(dirname "$0")
cd "$SCRIPT_DIR/.."

PROG="main.py"

if [ ! -e "$PROG" ]
then
    echo "$PWD/$PROG does not exist"
    exit 1
fi

echo "run $PWD/$PROG"

while true
do
    echo "-------------`date`---------------"
    echo "check if swap service is started"
    FOUND_RESULT=$(ps -ef | grep "python3 $PROG swap" | grep -v grep)
    if [ -z "$FOUND_RESULT" ]; then
        echo "no, start swap service";
        nohup python3 "$PROG" swap &> /dev/null &
    else
        echo "yes, swap service is already started"
    fi
    echo "sleep 60 seconds"
    echo ""
    sleep 60
done
