

#!/usr/bin/env python3
#*--------------------------------------------------------------------------------------
#* PyMap
#* Program to filter a cluster telnet stream and produce a graphical representation of
#* the geographic position of the spots
#*
#* Use case:
#* Check which areas the propagation allow a given station or geographic zone to be heard
#*
#* Uses library pywin32
#*
#* (c) Dr. Pedro E. Colla (LU7DZ/LT7D) 2025
#* MIT License
#* For radioamateur uses only
#*
#* See PyMap.py [--help|-h] for command options
#* 
#*--------------------------------------------------------------------------------------

import argparse
import asyncio
import re
import sys
from typing import Set
import csv

import time
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.basemap import Basemap

import datetime
import zipfile
import os
import glob
import tempfile
import shutil
import subprocess

import imageio.v2 as imageio
from collections import defaultdict
import json

import maidenhead as mh
from geopy.geocoders import Nominatim
from pycountry_convert import country_alpha2_to_continent_code, convert_continent_code_to_continent_name
from geopy.geocoders import Nominatim
import getopt
import sys
import argparse
from pyhamtools import LookupLib, Callinfo

# Pool of connected telnet clients connected
connected_clients: Set[asyncio.StreamWriter] = set()
clients_lock = asyncio.Lock()
my_lookuplib = LookupLib(lookuptype="countryfile")
cic = Callinfo(my_lookuplib)
map=None
#plt.ion()
#*-----------------------------------------------------------------------------
async def handle_local_client(reader: asyncio.StreamReader,
                              writer: asyncio.StreamWriter) -> None:
    """
    Listen for a local telnet client (likely N1MM or a local telnet consolidator like WinTelnetX
    All info sent by the client is ignored but the connection is preserved, when a spot
    passes the filter criteria all connected clients will be shared with the spot
    (this is an Observer like design pattern)
    """
    peername = writer.get_extra_info("peername")
    async with clients_lock:
        connected_clients.add(writer)
    print(f"[LOCAL] Client connected {peername}", file=sys.stderr)

    try:
        # Read till the telnet client disconnect.
        while True:
            data = await reader.read(1024)
            if not data:
                break
            # Future expansion for commands here, not implemented yet.
    except Exception as exc:
        print(f"[LOCAL] Error client {peername}: {exc}", file=sys.stderr)
    finally:
        async with clients_lock:
            if writer in connected_clients:
                connected_clients.remove(writer)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        print(f"[LOCAL] Client disconnected {peername}", file=sys.stderr)


def freq2band(freq):

    f=int(float(freq))
    try:
      if int(f/1000) == 432:
         return "70cm"
      if int(f/1000) == 144:
         return "2m"
      if int(f/1000) == 50:
         return "6m"
      if int(f/1000) == 28:
         return "10m"
      if int(f/1000) == 24:
         return "12m"
      if int(f/1000) == 21:
         return "15m"
      if int(f/1000) == 18:
         return "17m"
      if int(f/1000) == 14:
         return "20m"
      if int(f/1000) == 10:
         return "30m"
      if int(f/1000) == 7:
         return "40m"
      if int(f/1000) == 3:
         return "80m"
      if int(f/1000) == 1:
         return "160m"
    except:
         return 0  

async def broadcast_to_clients(message: str) -> None:
    """
    message is broadcasted to all connected clients
    """
    async with clients_lock:
        if not connected_clients:
            return
        dead_clients = []
        for w in connected_clients:
            try:
                w.write((message + "\n").encode(errors="ignore"))
            except Exception:
                dead_clients.append(w)

        # Drain outside the loop for efficiency
        try:
            await asyncio.gather(
                *(w.drain() for w in connected_clients if w not in dead_clients),
                return_exceptions=True
            )
        except Exception:
            pass

        # Remove dead or unresponsive clients
        for w in dead_clients:
            connected_clients.remove(w)
            try:
                w.close()
            except Exception:
                pass


def parse_dx_line(line: str):
    """
    Parsed the line from the cluster:
        DX DE {FROM} {FREQ} {CALLSIGN} {MODE} ...
    using spaces or tabs as separators.
    """
    # Split according with separator
    tokens = re.split(r'\s+', line.strip())
    if len(tokens) < 6:
        return None

    if tokens[0].upper() != "DX" or tokens[1].upper() != "DE":
        return None

    from_ = tokens[2].upper()
    freq = tokens[3].upper()
    callsign = tokens[4].upper()
    mode = tokens[5].upper()
    speed = tokens[8].upper()
    snr=tokens[6].upper()
    activity=tokens[10].upper()
    timestamp=tokens[11].upper()
    return from_, freq, callsign, mode,speed,snr,activity,timestamp





#*------------------------------------------------------------------------------------------------------
#* Transform band into a line of a pre-defined colour
#*------------------------------------------------------------------------------------------------------
def band2color(band):
    
    match band:
        case "40m":
            return 'c' 
        case "20m":   
            return 'y'  
        case "15m":
            return 'g'
        case "10m":
            return 'm'
        case _:
            return 'c'


#*------------------------------------------------------------------------------------------------------
#* Build a map (Mercator projection)
#*------------------------------------------------------------------------------------------------------
def buildMap():
    m = Basemap(projection='merc',llcrnrlon=-170,llcrnrlat=-75,urcrnrlon=170,urcrnrlat=75,resolution='l')
    m.drawmeridians(np.arange(0,360,30))
    m.drawparallels(np.arange(-90,90,30))
    m.drawcoastlines(linewidth=0.25)
    m.drawcountries(linewidth=0.25)
    return m


async def remote_client_task(host: str,
                             port: int,
                             keyword: str,
                             response: str,
                             filter_callsign: str,
                             init_string: str,
                             band: str) -> None:
    """
    Connection to the cluster telnet server.
    - Upon connection send an initial string
    - Wait till keyword and send challenge response.
    - Then the spot streams are processed
    """
    global my_lookuplib,cic,map


    print(f"[REMOTE] Connecting to {host}:{port} ...", file=sys.stderr)
    reader, writer = await asyncio.open_connection(host, port)
    print(f"[REMOTE] Connected to {host}:{port}", file=sys.stderr)

    # This is the exact spacing that N1MM seems to like
    #          1         2         3         4         5         6         7         8
    # 12345678901234567890123456789012345678901234567890123456789012345678901234567890
    # DX de LU2EIC-#:  28024.7 LU7DZ        CW  5 dB 29 WPM CQ PY2PE-#    1329Z
    # DX de LU2EIC-#:  28024.8 LU7DZ        CW 17 dB 29 WPM CQ DF2CK-#    1329Z
    # DX de LU2EIC-#:  28024.8 LU7DZ        CW  7 dB 30 WPM CQ OK1FCJ-#   1329Z
    # DX de LU2EIC-#:  28024.8 LU7DZ        CW  4 dB 30 WPM CQ HA8TKS-#   1329Z

    init_string=response
    try:
        to_send = (init_string + "\r\n").encode(errors="ignore")
        writer.write(to_send)
        await writer.drain()
        print(f"[REMOTE] >> (init) {repr(init_string)}", file=sys.stderr)
    except Exception as exc:
        print(f"[REMOTE] Error sending initial string: {exc}", file=sys.stderr)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return

    print("[REMOTE] Handshake completed, processing spots ...", file=sys.stderr)

    # Main loop receive, process and filter spots

    try:
        while True:
            data = await reader.readline()
            if not data:
                print("[REMOTE] Remote connection closed.", file=sys.stderr)
                break

            line = data.decode(errors="ignore").rstrip("\r\n")
            # Parse spot 
            parsed = parse_dx_line(line)
            if not parsed:
                # Irrelevant line, ignore it
                continue

            from_, freq, callsign, mode, speed, snr, activity, timestamp = parsed


            # If pass the filter show at stdout and send to clients

            cluster = from_.split("-", 1)[0]
            spot=f"DX de {cluster}:"
            spot=spot.ljust(15)
            f=freq.rjust(9)

            fx=int(float(f))
            if band != freq2band(fx):
               continue

            # Filter callsign
            if filter_callsign != "*" and callsign.upper() != filter_callsign.upper():
                plt.show(block=False)
                plt.pause(0.001)
                continue


            #cl=f"{filter_callsign}"
            cl=f"{callsign.upper()}"
            cl=cl.replace("#","")
            cl=cl.ljust(13)
            snr=snr.rjust(2)
            snr=f"{snr} dB"
            speed=speed.rjust(2)
            speed=f"{speed} WPM"
            #msg=f"{mode} {snr} {speed} CQ {cluster}-#"
            msg=f"{mode} {snr} {speed} CQ "
            msg=msg.ljust(31)
            newline=f"{spot}{f}  {cl}{msg}{timestamp}" 
            print(newline,end="\n")

            try:
               o=cic.get_all(cluster.upper())
               z=cic.get_all(callsign.upper())
            except:
               print(f"Callsign {cluster.upper()} or {callsign.upper()} can not be decoded")
               continue

            laFrom=float(o['latitude'])
            loFrom=float(o['longitude'])

            laTo=float(z['latitude']) 
            loTo=float(z['longitude']) 

            lat = [laFrom,laTo]
            lon = [loFrom,loTo]

            r=band2color(band)

            x,y = map(lon, lat)
            map.plot(x, y, 'o-', color=r,markersize=1, linewidth=1)
            plt.show(block=False)
            plt.pause(0.001)

            await broadcast_to_clients(newline)

    except Exception as exc:
        print(f"[REMOTE] Connection error: {exc}", file=sys.stderr)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        print("[REMOTE] Cliente remoto finalizado.", file=sys.stderr)


async def main_async(args):
    # Start the local telnet server
    global map
    server = await asyncio.start_server(
        handle_local_client,
        host="0.0.0.0",
        port=args.listen_port,
    )

    sockets = server.sockets or []
    for sock in sockets:
        addr = sock.getsockname()
        print(f"[LOCAL] Servidor Telnet escuchando en {addr}", file=sys.stderr)

    print(f"Connection arguments remote({args.remote_host}:{args.remote_port}) keyword({args.keyword}) response({args.response}) filter({args.filter_callsign}) init({args.init_string})")
    # Start the connection with the remote cluster telnet server
    remote_task = asyncio.create_task(
        remote_client_task(
            host=args.remote_host,
            port=args.remote_port,
            keyword=args.keyword,
            response=args.response,
            filter_callsign=args.filter_callsign,
            init_string=args.init_string,
            band=args.band,
        )
    )
    date="2025-12-20"
    yy=int(date.split("-")[0])
    mm=int(date.split("-")[1])
    dd=int(date.split("-")[2])
    h=22


    map=buildMap();
    f = datetime.datetime(yy,mm,dd,h,0,0)
    CS=map.nightshade(f)
    modeGIF="SHADED"
    if (modeGIF=="SHADED"):
       map.shadedrelief(scale=0.1)
    else:
       map.bluemarble(scale=0.1)

    title="PyMap"
    plt.title(title)
    if len(str(h)) == 1:
       stHour="0"+str(h)
    else:
       stHour=str(h)
    #plt.close("all")


    # While connected to the cluster accept local telnet connections.
    try:
        async with server:
            await remote_task  # wait for remote
    finally:
        # When the cluster disconnect all local clients disconnects too
        server.close()
        await server.wait_closed()
        async with clients_lock:
            for w in list(connected_clients):
                try:
                    w.close()
                except Exception:
                    pass
            connected_clients.clear()
        print("[MAIN] Terminando.", file=sys.stderr)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "DX Spot filters. Filter spots looking for a callsign and re-spot as local server"
        )
    )

    parser.add_argument(
        "-R", "--remote-host",
        required=True,
        help="Cluster telnet server address"
    )
    parser.add_argument(
        "-P", "--remote-port",
        type=int,
        required=True,
        help="Cluster telnet server port"
    )
    parser.add_argument(
        "-k", "--keyword",
        required=True,
        help="Keyword to start the connection"
    )
    parser.add_argument(
        "-r", "--response",
        required=True,
        help="Response to send as the connection challenge"
    )
    parser.add_argument(
        "-L", "--listen-port",
        type=int,
        required=True,
        help="Local telnet server port"
    )
    parser.add_argument(
        "-B", "--band",
        type=str,
        required=True,
        help="Band to filter"
    )
    parser.add_argument(
        "-f", "--filter-callsign",
        required=True,
        help="Callsign to look after (use '*' to resend all)"
    )
    parser.add_argument(
        "-i", "--init-string",
        default="",
        help=(
            "Init string usually the station callsign "
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n[MAIN] Interrupted by user.", file=sys.stderr)


if __name__ == "__main__":
    main()

