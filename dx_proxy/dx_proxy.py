
#!/usr/bin/env python3
#*--------------------------------------------------------------------------------------
#* dx_proxy
#* Program to filter a cluster telnet stream and repost spots for a given callsign
#* reformatted as from a local cluster
#* Use case:
#* The N1MM logger allows the telnet window to filter spots as comming from specific
#* clusters with certain criterias. One of the criterias, which turned to be useful
#* is to filter by geographic location of the cluster (i.e. SA clusters only).
#* This is useful to reduce the large amount of unuseful spots yield by the RBN where
#* they are reported by pairs of stations RBN-Node <-> Spotted station which aren't 
#* workable because of CONDX. Limiting the clusters to a regional area increases the
#* likelihood of the spot to be workable by our station. This is extremely powerful
#* and most of the spots are actually workable, which increases the ability to work
#* multipliers in assisted modes. However, it has a drawback, the spots on us aren't
#* as frequent nor useful, spots on us gives a clue on where are We heard and how 
#* strong, this information from local clusters isn't really useful.
#* This program reads the cluster stream and when a spot on us is detected it's recasted
#* as comming from a local cluster with the original spotter info preserved.
#*
#* Uses library pywin32
#*
#* (c) Dr. Pedro E. Colla (LU7DZ/LT7D) 2025
#* MIT License
#* For radioamateur uses only
#*
#* See dx_proxy [--help|-h] for command options
#* 
#*--------------------------------------------------------------------------------------

import argparse
import asyncio
import re
import sys
from typing import Set


# Pool of connected telnet clients connected
connected_clients: Set[asyncio.StreamWriter] = set()
clients_lock = asyncio.Lock()

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


async def remote_client_task(host: str,
                             port: int,
                             keyword: str,
                             response: str,
                             filter_callsign: str,
                             init_string: str) -> None:
    """
    Connection to the cluster telnet server.
    - Upon connection send an initial string
    - Wait till keyword and send challenge response.
    - Then the spot streams are processed
    """
    print(f"[REMOTE] Connecting to {host}:{port} ...", file=sys.stderr)
    reader, writer = await asyncio.open_connection(host, port)
    print(f"[REMOTE] Connected to {host}:{port}", file=sys.stderr)

    # Initial line, now it's fixed)

    # This is the exact spacing that N1MM seems to like
    #          1         2         3         4         5         6         7         8
    # 12345678901234567890123456789012345678901234567890123456789012345678901234567890
    # DX de LU2EIC-#:  28024.7 LU7DZ        CW  5 dB 29 WPM CQ PY2PE-#    1329Z
    # DX de LU2EIC-#:  28024.8 LU7DZ        CW 17 dB 29 WPM CQ DF2CK-#    1329Z
    # DX de LU2EIC-#:  28024.8 LU7DZ        CW  7 dB 30 WPM CQ OK1FCJ-#   1329Z
    # DX de LU2EIC-#:  28024.8 LU7DZ        CW  4 dB 30 WPM CQ HA8TKS-#   1329Z


    init_string="LT7D"
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

            # Filter callsign
            if filter_callsign != "*" and callsign.upper() != filter_callsign.upper():
                continue

            # If pass the filter show at stdout and send to clients

            cluster = from_.split("-", 1)[0]
            spot=f"DX de LU2EIC-#:"
            spot=spot.ljust(15)
            f=freq.rjust(9)
            cl=f"LU7DZ"
            cl=cl.replace("#","")
            cl=cl.ljust(13)
            snr=snr.rjust(2)
            snr=f"{snr} dB"
            speed=speed.rjust(2)
            speed=f"{speed} WPM"
            msg=f"{mode} {snr} {speed} CQ {cluster}-#"
            msg=msg.ljust(31)
            newline=f"{spot}{f}  {cl}{msg}{timestamp}" 
            print(newline,end="\n")
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
    server = await asyncio.start_server(
        handle_local_client,
        host="0.0.0.0",
        port=args.listen_port,
    )

    sockets = server.sockets or []
    for sock in sockets:
        addr = sock.getsockname()
        print(f"[LOCAL] Servidor Telnet escuchando en {addr}", file=sys.stderr)

    # Start the connection with the remote cluster telnet server
    remote_task = asyncio.create_task(
        remote_client_task(
            host=args.remote_host,
            port=args.remote_port,
            keyword=args.keyword,
            response=args.response,
            filter_callsign=args.filter_callsign,
            init_string=args.init_string,
        )
    )

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

