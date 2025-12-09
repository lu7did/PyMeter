#*--------------------------------------------------------------------------------------
#* PyCAT
#* Programa para enviar comandos a un transceptor utilizando OmniRig
#*
#* Utiliza librería pywin32
#*
#* (c) Dr. Pedro E. Colla (LU7DZ/LT7D) 2025
#* MIT License
#* For radioamateur uses only
#*
#* PyCAT [--help|-h] [-c|--command CATStr] [-l|--length n]
#* 
#*--------------------------------------------------------------------------------------
import time
import pythoncom
import win32com.client
import argparse
import sys

defaultNamedNotOptArg = pythoncom.Empty

flagEnd = False
#*--------------------------------------------------------------------------------------
#* OmniRig event handlers
#*--------------------------------------------------------------------------------------
class OmniRigEvents:
    """Manejador de eventos para OmniRig (COM)."""

    def OnCustomReply(self,
                      RigNumber=defaultNamedNotOptArg,
                      Command=defaultNamedNotOptArg,
                      Reply=defaultNamedNotOptArg):
        """Evento disparado cuando llega una respuesta al comando personalizado."""
        try:
            reply_bytes = bytes(Reply)
        except TypeError:
            reply_bytes = Reply
        print(f"[CustomReply] Rig={RigNumber} Cmd={Command!r} Reply={reply_bytes!r}")
        flagEnd = True

def get_attribute(rig):
    """
    Intenta llamar a la interfaz de dispatch Get_StatusStr del rig.
    Si no existe como método, prueba la propiedad StatusStr.
    """
    status_str = "<desconocido>"

    # Algunos wrappers exponen directamente Get_StatusStr()
    if hasattr(rig, "Get_StatusStr"):
        try:
            status_str = rig.Get_StatusStr()
        except Exception as e:
            status_str = f"<error llamando Get_StatusStr: {e}>"
    # Otros exponen la propiedad StatusStr
    elif hasattr(rig, "StatusStr"):
        try:
            status_str = rig.StatusStr
        except Exception as e:
            status_str = f"<error leyendo StatusStr: {e}>"

    return status_str

def getMode(mode):

  if mode == 0x00800000:
     return "CW-U"
  if mode == 0x01000000:
     return "CW-L"
  if mode == 0x02000000:
     return "USB"
  if mode == 0x04000000:
     return "LSB"
  if mode == 0x08000000:
     return "DIG-U"
  if mode == 0x10000000:
     return "DIG-L"
  if mode == 0x20000000:
     return "AM"
  if mode == 0x20000000:
     return "FM"
  return "???"

def main():
    # ----------------------------------------------------------------------
    # ARGUMENTOS
    # ----------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Enviar un comando CAT a OmniRig usando pywin32."
    )

    parser.add_argument(
        "-c", "--command",
        required=True,
        help="Comando CAT a enviar (string literal, ej.: 'FA;' o 'MG;')."
    )

    parser.add_argument(
        "-l", "--length",
        type=int,
        default=0,
        help="Longitud esperada de la respuesta. Default: 0"
    )

    parser.add_argument(
        "-v", "--verbose",
        default=False,
        help="Carácter que indica fin de respuesta (default ';')."
    )
    parser.add_argument(
        "-d", "--debug",
        default=False,
        help="Emite mensajes para hacer debug"
    )

    parser.add_argument(
        "-e", "--end",
        default=";",
        help="Muestra estado del equipo controlado"
    )

    parser.add_argument(
        "-r", "--rig",
        default="rig1",
        help="Define cual es el rig a controlar"
    )

    args = parser.parse_args()

    command_str = args.command
    reply_length = args.length
    reply_end = args.end


    # Convertir comando a bytes
    command_bytes = command_str.encode("ascii")


    # ----------------------------------------------------------------------
    # CREAR OBJETO COM
    # ----------------------------------------------------------------------
    omni = win32com.client.gencache.EnsureDispatch("OmniRig.OmniRigX")
    omni_events = win32com.client.WithEvents(omni, OmniRigEvents)

    if args.rig.upper() == "RIG2":
       rig=omni.Rig2
    else:
       rig=omni.Rig1    

    #rig1 = omni.Rig1

    # ----------------------------------------------------------------------
    # ENVIAR COMANDO
    # ----------------------------------------------------------------------
    if args.verbose:
       print(f"Type ({rig.RigType}) VFO A/B({rig.Vfo}) main({rig.Freq}) A({rig.FreqA}) B({rig.FreqB}) Mode({getMode(rig.Mode)}) Split({rig.Split and 0x8000})")
    if args.debug:
       print(f"Type ({rig.RigType}) Status({rig.Status}) RIT({rig.Rit}) XIT({rig.Xit}) Status({rig.StatusStr})")

    cmd_sent=command_bytes;
    rig.SendCustomCommand(command_bytes, reply_length, reply_end)

    if args.verbose:
       if reply_length != 0:
          if args.debug:
             print("Esperando respuesta (Ctrl+C para salir)...")

    try:
        while True:
            pythoncom.PumpWaitingMessages()
            if reply_length == 0:
               print(f"CMD[{cmd_sent}] --> ANSWER[{command_bytes}]")
               time.sleep(1)
               sys.exit(0)
            print(f"{command_bytes}")
            if cmd_sent != command_bytes:            
               print(f"CMD[{cmd_sent}] --> ANSWER[{command_bytes}]")
               sys.exit(0)
    except KeyboardInterrupt:
        print("\nFinalizando...")


if __name__ == "__main__":
    main()

