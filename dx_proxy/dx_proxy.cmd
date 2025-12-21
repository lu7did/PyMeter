Rem #!/usr/bin/env python3
Rem #*--------------------------------------------------------------------------------------
Rem #* dx_proxy
Rem #* Program to filter a cluster telnet stream and repost spots for a given callsign
Rem #* reformatted as from a local cluster

python dx_proxy.py -R telnet.reversebeacon.net -P 7000 -k "LU2EIC" -r LU2EIC -L 9000 -f LU7DZ

