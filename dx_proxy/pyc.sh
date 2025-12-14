#!/bin/sh
PATH="/home/pi/Descargas/PyHamRemote/dx_proxy"
PYTHON="/usr/local/bin/python3"
CLUSTER="telnet.reversebeacon.net"
PORT=7000
SPOT=LT7D
cd $PATH

$PYTHON dx_proxy.py -R $CLUSTER -P $PORT -k "call:" -r "LT7D" -L 9000 -f LT7D

