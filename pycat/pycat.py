#*--------------------------------------------------------------------------------------
#* PyCAT
#* Program to send commands to connected rigs using OmniRig
#*
#* Uses library pywin32
#*
#* (c) Dr. Pedro E. Colla (LU7DZ/LT7D) 2025
#* MIT License
#* For radioamateur uses only
#*
#* See PyCAT [--help|-h] for command options
#* 
#* If COM object mapping fails erase the folder pygen at C:\Users\Usuario\AppData\Local\Temp
#*--------------------------------------------------------------------------------------
import time
import pythoncom
import win32com.client
import argparse
import sys

defaultNamedNotOptArg = pythoncom.Empty
flagEnd = False
omni=None
#*--------------------------------------------------------------------------------------
#* OmniRig event handlers
#*--------------------------------------------------------------------------------------
class OmniRigEvents:
    """Event handlers, only OnCustomReply and OnParamsChange implemented"""

    def OnCustomReply(self,
                      RigNumber=defaultNamedNotOptArg,
                      Command=defaultNamedNotOptArg,
                      Reply=defaultNamedNotOptArg):
        global omni
        """Triggers when a response to a custom command is received."""
        try:
            reply_bytes = bytes(Reply)
        except TypeError:
            reply_bytes = Reply
        print(f"[CustomReply] Rig={RigNumber} Cmd={bytes(Command)} Reply={reply_bytes!r}")
        flagEnd = True

    def OnParamsChange(self, RigNumber,e):
        global omni
        try:
            rig = omni.Rig1 if RigNumber == 1 else omni.Rig2
            freq = rig.Freq
            mode = rig.Mode
            if RigNumber==1:
               self.win.rig1_freq_label.setText(f"{freq/1e6:.3f} MHz")
               self.win.rig1_vfo_label.setText(str(rig.Vfo))
            else:
               self.win.rig2_freq_label.setText(f"{freq/1e6:.3f} MHz")
               self.win.rig2_vfo_label.setText(str(rig.Vfo))
        except Exception as e:
            print(f"[EVENT] ParamsChangeEvent: rig={RigNumber}, error reading params: {e}", flush=True)



#*-----------------------------------------------------------------------------------
#* Processing of OmniRig responses and options
#*-----------------------------------------------------------------------------------
def getRigStatus(rig):
    padding=8
    # ----------------------------------------------------------------------
    # Show rig status
    # ----------------------------------------------------------------------
    print(f"Transceiver({rig.RigType})")
    print(f"  Freq({rig.Freq}) Vfo ({rig.Vfo:#08x}) Mode({getMode(rig.Mode)})")
    print(f"  VFOA({rig.FreqA}) VFOB({rig.FreqB})")
    print(f"  Status({rig.Status}) Status({rig.StatusStr})")


def get_attribute(rig):
    status_str = "<desconocido>"
    if hasattr(rig, "Get_StatusStr"):
        try:
            status_str = rig.Get_StatusStr()
        except Exception as e:
            status_str = f"<error llamando Get_StatusStr: {e}>"
    elif hasattr(rig, "StatusStr"):
        try:
            status_str = rig.StatusStr
        except Exception as e:
            status_str = f"<error leyendo StatusStr: {e}>"

    return status_str
#*------------------------------------------------------------------------------------
#* Set Vfo A or B
#*------------------------------------------------------------------------------------
def setVfo(rig,mVfo):
  if mVfo == "A":
     rig.Vfo = 0x00000800
     return
  if mVfo == "B":
     rig.Vfo =0x00001000
     return
  print(f"ERROR. Invalid VFO code given. Ignored")
  
#*------------------------------------------------------------------------------------
#* Set Mode
#*------------------------------------------------------------------------------------

def setMode(rig,mStr):
  if mStr == "CW-U" or mStr == "CW":
     rig.Mode =0x00800000
     return
  if mStr == "CW-L":
     rig.Mode =0x01000000
     return
  if mStr == "USB":
     rig.Mode =0x02000000
     return
  if mStr == "LSB":
     rig.Mode =0x04000000
     return
  if mStr == "DIG-U":
     rig.Mode =0x08000000
     return
  if mStr == "DIG-L":
     rig.Mode =0x10000000
     return
  if mStr == "AM":
     rig.Mode =0x20000000
     return
  if mStr == "FM":
     rig.Mode =0x40000000
     return
  print(f"ERROR. Mode {mStr} not valida. Ignored")
#*------------------------------------------------------------------------------------
#* Translate mode coding into actual strings
#*------------------------------------------------------------------------------------
def getMode(m):

  padding = 6
  mode = m & 0xfff00000
  #print(f"Recibio m({m:#0{padding}x}) mode({mode:#0{padding}x})  ") 
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
  if mode == 0x40000000:
     return "FM"
  return "???"

#*------------------------------------------------------------------------------------
#*                          MAIN Processing
#*------------------------------------------------------------------------------------
def main():
    # ----------------------------------------------------------------------
    # ARGUMENTOS
    # ----------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="Get rig status, set variables or send custom commands using pywin32."
    )

    parser.add_argument(
        "-c", "--command",
        required=False,
        default="",
        help="Command string, format {cmd}{parms};   (string literal, ie: FA28022680;)."
    )

    parser.add_argument(
        "-f", "--freq",
        type=int,
        default=0,
        help="Change frequency of current VFO"
    )

    parser.add_argument(
        "--spliton",
        action="store_true",
        help="Force Split On"
    )

    parser.add_argument(
        "--splitoff",
        action="store_true",
        help="Force Split Off"
    )

    parser.add_argument(
        "--swap",
        action="store_true",
        help="Swap VFO A and B"
    )

    parser.add_argument(
        "--equal",
        action="store_true",
        help="Copy VFO A into B"
    )

    parser.add_argument(
        "-m", "--mode",
        type=str,
        default="",
        required=False,
        help="Change Mode {CW,CW-R,USB,LSB,AM,FM,DIG-U,DIG-L}"
    )

    parser.add_argument(
        "--vfo",
        type=str,
        default="",
        required=False,
        help="Set VFO A or B depending on argument (i.e. --vfo A or --vfo B)"
    )

    parser.add_argument(
        "-l", "--length",
        type=int,
        default=0,
        help="Custom command default response length, default 0"
    )

    parser.add_argument(
        "-v", "--view",
        action="store_true",
        help="Show current status."
    )
    parser.add_argument(
        "-d", "--debug",
        default=False,
        help="Debugging mode"
    )

    parser.add_argument(
        "-e", "--end",
        default=";",
        help="Custom command default terminator, default ;"
    )

    parser.add_argument(
        "-r", "--rig",
        default="rig1",
        help="Define rig to control as rig1 or rig2. Default: rig1"
    )

    args = parser.parse_args()

    # ----------------------------------------------------------------------
    # Creates COM object and establish rig to operate
    # ----------------------------------------------------------------------
    omni = win32com.client.gencache.EnsureDispatch("OmniRig.OmniRigX")
    omni_events = win32com.client.WithEvents(omni, OmniRigEvents)

    if args.rig.upper() == "RIG2":
       rig=omni.Rig2
    else:
       rig=omni.Rig1    

    # ----------------------------------------------------------------------
    # Operates with direct interface functions from OmniRig
    # ----------------------------------------------------------------------

    if args.view == True:
       padding=6
       getRigStatus(rig)

    if args.spliton == True:
       print(f"Turn Split On")
       rig.Split = 0x00008000
       sys.exit(0)

    if args.splitoff == True:
       print(f"Turn Split Off")
       rig.Split = 0x00010000
       sys.exit(0)

    if args.mode != "":
       print(f"Mode change to {args.mode.upper()}")
       setMode(rig,args.mode.upper())
       sys.exit(0)

    if args.swap:
       print(f"Vfo swap A/B")
       rig.Vfo=0x00004000
       sys.exit(0)

    if args.equal:
       print(f"Vfo equal A/B")
       rig.Vfo=0x00002000
       sys.exit(0)

    if args.vfo != "":
       print(f"Vfo change to {args.vfo.upper()}")
       setVfo(rig,args.vfo.upper())
       sys.exit(0)

    if args.freq != 0:
       print(f"Frequency change to {args.freq}")
       rig.Freq = args.freq
       sys.exit(0)

    # ----------------------------------------------------------------------
    # If no further command has been given terminate
    # ----------------------------------------------------------------------

    if args.command == "":
       sys.exit(0)

    # ----------------------------------------------------------------------
    # Process custom command only if the rig is Yaesu FT2000
    # this restriction can be lifted if the commands can be given using
    # an ASCII string command, all commands requiring binary formats can not
    # be processed by this logic
    # ----------------------------------------------------------------------

    if rig.RigType != "FT-2000":
       print(f"Custom commands not supported for rigs other than FT-2000")
       sys.exit(0)

    command_str = args.command
    reply_length = args.length
    reply_end = args.end


    # Convert command to bytes

    command_bytes = command_str.encode("ascii")
    cmd_sent=command_bytes;
    rig.SendCustomCommand(command_bytes, reply_length, reply_end)

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
        print("\nKeyboard interrupt received, aborting...")


if __name__ == "__main__":
    main()

