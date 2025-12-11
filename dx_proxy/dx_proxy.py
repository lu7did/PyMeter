#!/usr/bin/env python3
import argparse
import asyncio
import re
import sys
from typing import Set


# Conjunto global de clientes conectados al servidor local
connected_clients: Set[asyncio.StreamWriter] = set()
clients_lock = asyncio.Lock()


async def handle_local_client(reader: asyncio.StreamReader,
                              writer: asyncio.StreamWriter) -> None:
    """
    Atiende un cliente Telnet local.
    No se procesa lo que envíe el cliente; sólo se mantiene la conexión
    para poder enviarle líneas que matcheen el filtro.
    """
    peername = writer.get_extra_info("peername")
    async with clients_lock:
        connected_clients.add(writer)
    print(f"[LOCAL] Cliente conectado desde {peername}", file=sys.stderr)

    try:
        # Leemos hasta que el cliente se desconecte.
        while True:
            data = await reader.read(1024)
            if not data:
                break
            # Aquí podrías implementar comandos si algún día hiciera falta.
    except Exception as exc:
        print(f"[LOCAL] Error con el cliente {peername}: {exc}", file=sys.stderr)
    finally:
        async with clients_lock:
            if writer in connected_clients:
                connected_clients.remove(writer)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        print(f"[LOCAL] Cliente desconectado {peername}", file=sys.stderr)


async def broadcast_to_clients(message: str) -> None:
    """
    Envía 'message' a todos los clientes conectados al servidor Telnet local.
    El mensaje se envía en una sola línea terminada en CRLF.
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

        # Hacemos drain fuera del bucle por eficiencia
        try:
            await asyncio.gather(
                *(w.drain() for w in connected_clients if w not in dead_clients),
                return_exceptions=True
            )
        except Exception:
            pass

        # Eliminamos los clientes que fallaron
        for w in dead_clients:
            connected_clients.remove(w)
            try:
                w.close()
            except Exception:
                pass


def parse_dx_line(line: str):
    """
    Intenta parsear una línea en el formato:
        DX DE {FROM} {FRECUENCIA} {CALLSIGN} {MODE} ...
    con separadores de uno o más espacios/tabs.

    Devuelve (from_, freq, callsign, mode) o None si no matchea.
    """
    # Split por uno o más espacios o tabs
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
    Cliente Telnet hacia el servidor remoto.
    - Tras conectar, envía una línea inicial (init_string + CRLF) para
      "despertar" al servidor, por si espera algo antes de enviar datos.
    - Espera hasta encontrar 'keyword' en alguna línea y responde con 'response'.
      La keyword puede aparecer en cualquier parte de la línea.
    - Luego procesa líneas DX y, si matchean el filtro de callsign, las
      manda a stdout y a todos los clientes locales.
    """
    print(f"[REMOTE] Conectando a {host}:{port} ...", file=sys.stderr)
    reader, writer = await asyncio.open_connection(host, port)
    print(f"[REMOTE] Conectado a {host}:{port}", file=sys.stderr)

    # Enviamos una línea inicial para activar al servidor (por ejemplo CRLF)
    init_string="LU7DZ"
    try:
        to_send = (init_string + "\r\n").encode(errors="ignore")
        writer.write(to_send)
        await writer.drain()
        print(f"[REMOTE] >> (init) {repr(init_string)}", file=sys.stderr)
    except Exception as exc:
        print(f"[REMOTE] Error enviando init_string: {exc}", file=sys.stderr)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return

    # Handshake: esperamos la palabra clave en cualquier parte del string recibido
    #print(f"[REMOTE] Esperando palabra clave '{keyword}' ...", file=sys.stderr)
    #try:
    #    while True:
    #        data = await reader.readline()
    #        if not data:
    #            print("[REMOTE] Conexión cerrada por el servidor durante el handshake.",
    #                  file=sys.stderr)
    #            writer.close()
    #            await writer.wait_closed()
    #            return
    #
    #        line = data.decode(errors="ignore").rstrip("\r\n")
    #        print(f"[REMOTE] << {line}", file=sys.stderr)
    #        break
            # La keyword puede aparecer en cualquier parte del string
            #if keyword in line:
            #    resp = response + "\r\n"
            #    writer.write(resp.encode(errors="ignore"))
            #    await writer.drain()
            #    print(f"[REMOTE] >> {response}", file=sys.stderr)
            #    break
    #except Exception as exc:
    #    print(f"[REMOTE] Error durante el handshake: {exc}", file=sys.stderr)
    #    writer.close()
    #    try:
    #        await writer.wait_closed()
    #    except Exception:
    #         pass
    #    return

    print("[REMOTE] Handshake completado. Procesando líneas DX ...", file=sys.stderr)

    # Bucle principal de recepción y filtrado
    try:
        while True:
            data = await reader.readline()
            if not data:
                print("[REMOTE] Conexión remota cerrada.", file=sys.stderr)
                break

            line = data.decode(errors="ignore").rstrip("\r\n")
            # Intentamos parsear como línea DX
            parsed = parse_dx_line(line)
            if not parsed:
                # Línea no relevante, la ignoramos
                continue

            from_, freq, callsign, mode, speed, snr, activity, timestamp = parsed

            # Filtro de callsign (case-insensitive simple)
            if filter_callsign != "*" and callsign.upper() != filter_callsign.upper():
                continue

            # Si pasa el filtro, lo mostramos por stdout y lo enviamos a los clientes.

            #print(line)
            cluster = from_.split("-", 1)[0]
            #newline=f"DX de LU7DZ:    {freq}  {callsign}           {mode}    {snr} dB  {speed} WPM  {activity}      {timestamp}   fm:{cluster}#"
            newline=f"DX de LU7DZ:    {freq}  {callsign}           {mode}    {snr} dB  {speed} WPM  fm:{cluster}#      {timestamp}   fm:{cluster}#"
            print(newline,end="\n")
            await broadcast_to_clients(newline)

    except Exception as exc:
        print(f"[REMOTE] Error en la conexión remota: {exc}", file=sys.stderr)
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        print("[REMOTE] Cliente remoto finalizado.", file=sys.stderr)


async def main_async(args):
    # Iniciamos el servidor Telnet local
    server = await asyncio.start_server(
        handle_local_client,
        host="0.0.0.0",
        port=args.listen_port,
    )

    sockets = server.sockets or []
    for sock in sockets:
        addr = sock.getsockname()
        print(f"[LOCAL] Servidor Telnet escuchando en {addr}", file=sys.stderr)

    # Lanzamos la tarea del cliente remoto
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

    # Mientras el cliente remoto corre, el servidor local acepta conexiones.
    try:
        async with server:
            await remote_task  # esperamos a que termine el remoto
    finally:
        # Cuando el remoto termina, cerramos el servidor local y los clientes
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
            "Cliente/servidor Telnet: se conecta a un servidor remoto, "
            "filtra líneas DX por CALLSIGN y reenvía las coincidencias "
            "a clientes Telnet locales y a stdout."
        )
    )

    parser.add_argument(
        "-R", "--remote-host",
        required=True,
        help="Host del servidor Telnet remoto"
    )
    parser.add_argument(
        "-P", "--remote-port",
        type=int,
        required=True,
        help="Puerto del servidor Telnet remoto"
    )
    parser.add_argument(
        "-k", "--keyword",
        required=True,
        help="Palabra clave que se busca en cualquier parte del banner remoto"
    )
    parser.add_argument(
        "-r", "--response",
        required=True,
        help="Respuesta a enviar cuando se detecta la palabra clave"
    )
    parser.add_argument(
        "-L", "--listen-port",
        type=int,
        required=True,
        help="Puerto donde se levantará el servidor Telnet local"
    )
    parser.add_argument(
        "-f", "--filter-callsign",
        required=True,
        help="CALLSIGN a filtrar (use '*' para enviar todos)"
    )
    parser.add_argument(
        "-i", "--init-string",
        default="",
        help=(
            "Cadena inicial a enviar al servidor remoto inmediatamente "
            "después de conectar (por defecto se envía solo CRLF)."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()
    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\n[MAIN] Interrumpido por el usuario.", file=sys.stderr)


if __name__ == "__main__":
    main()

