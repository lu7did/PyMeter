#!/bin/sh
#*--------------------------------------------------------------------------------------
#* dx_proxy
#* Program to filter a cluster telnet stream and repost spots for a given callsign
#* reformatted as from a local cluster
#*--------------------------------------------------------------------------------------
PATH="/home/pi/Descargas/PyHamRemote/dx_proxy"
PYTHON="/usr/local/bin/python3"
CLUSTER="telnet.reversebeacon.net"
PORT=7000
SPOT=LU7DZ
RESP=LU2EIC
cd $PATH

$PYTHON dx_proxy.py -R $CLUSTER -P $PORT -k "call:" -r $RESP -L 9000 -f $SPOT

