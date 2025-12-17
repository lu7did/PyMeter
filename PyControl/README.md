PyControl
=========

Última actualización: 2025-12-17T00:28:37.191Z

Descripción
-----------
PyControl es una GUI Qt5 ligera incluida dentro del repositorio PyHamRemote que reutiliza widgets del módulo PyMeter para proporcionar un panel de control de rigs, medidor VU, selectores y controles de Power/Volume con persistencia simple.

Controles incluidos
-------------------
- Signal (label) con un LedIndicator pequeño a su derecha que alterna color cada segundo (verde oscuro <-> verde lima).
- VU Meter: tira de LEDs (bandas verdes/amarillas/rojas) alineada a la izquierda, LEDs compactos y muy próximos.
- Tabla de rigs con dos filas (rig1, rig2) y columnas: [radio, rig, name, status(LED), freq, mode].
- Power: Label, Slider (0..255), valor actual y botón "Set" (persistencia al pulsar).
- Volume: idéntico a Power con su propio slider y botón Set.
- Tres grupos de radio (exclusivos por grupo):
  - Izquierda (vertical): SWR / Power / Signal
  - Centro: ant 1 / ant 2
  - Derecha: VFO A / VFO B
- Selector de modo (ComboBox) situado en la misma línea que el VU meter, alineado a la derecha; opciones: CW, USB, LSB, AM, FM, DIG-U, DIG-L, CW-R.
- Botones con LED en la fila inferior: RX, Mute, Split, Tune. Actualmente los botones solo imprimen en consola un mensaje cuando se presionan.

Persistencia
------------
- Archivo: PyControl/PyControl.ini (formato KEY=VALUE).
- Si no existe, el programa crea el INI con valores por defecto al arrancar.
- Se guardan inmediatamente los cambios en: RIG, LEFT (SWR/Power/Signal), ANT, VFO, MODE.
- Los sliders (Power/Volume) solamente actualizan el INI al pulsar su correspondiente botón "Set" (KEYs: POWER y VOLUME).

API pública del GUI
-------------------
Los métodos y atributos siguientes están expuestos como propiedades del objeto ventana (win) devuelto por build_window()/main().

Ventana principal (win)
- Atributos públicos (accesibles):
  - win.meter -> instancia de VUMeter
  - win.tr -> LedButton (RX)
  - win.tune -> TuneButton
  - win.mute -> LedButton
  - win.split -> SwapButton
  - win.rig_group, win.rig1_radio, win.rig2_radio
  - win.rig1_name, win.rig2_name
  - win.rig1_led, win.rig2_led
  - win.rig1_freq_label, win.rig2_freq_label
  - win.rig1_mode, win.rig2_mode
  - win._signal_timer (QTimer interno, usado para alternar el Signal LED)

- Métodos públicos:
  - win.set_meter(val: int) -> None
      Establece el valor del VU meter (0..255).
  - win.set_tr(v: int) -> None
      Establece el estado del botón TR (0=RX, 1=TX).
  - win.set_rig_name(index: int, name: str) -> None
      Actualiza el campo "name" de la fila rig index (1 o 2).
  - win.set_rig_led_color(index: int, color_on: tuple[int,int,int], on: bool=True) -> None
      Cambia el color "on" del LedIndicator de la fila y su estado encendido/apagado.
  - win.set_rig_freq(index: int, hz: int) -> None
      Establece la frecuencia mostrada para la fila (enteros en Hz; se formatea con separadores y sufijo " MHz").
  - win.set_rig_mode(index: int, mode: str) -> None
      Establece la etiqueta de modo para la fila (p. ej. "USB").

Componentes (Clases y métodos principales)
- VUMeter (PyMeter.PyMeter.VUMeter)
  - Constructor: VUMeter(segments: int = 10, led_diameter: int = 8)
  - Métodos:
    - set_value(value: int) -> None
    - set_enabled(enabled: bool) -> None

- LedIndicator (PyMeter.PyMeter.LedIndicator)
  - Constructor: LedIndicator(diameter: int = 8, color_on: tuple = (0,255,0))
  - Métodos:
    - set_on(state: bool) -> None
    - is_on() -> bool
    - set_color_on(color: tuple[int,int,int]) -> None
    - set_color_off(color: tuple[int,int,int]) -> None

- LedButton (PyMeter.PyMeter.LedButton)
  - Constructor: LedButton(label: str, color_on: tuple = (0,255,0))
  - Métodos:
    - set_state(value: int) -> None
    - get_state() -> int
    - Señal clicked del QPushButton subyacente disponible para conectar handlers.

- TuneButton / SwapButton / VFOButton
  - Heredan LedButton. TuneButton proporciona internamente _setMainWindow(win) para integración con PyMeter/OmniRig (si existe).

Argumentos de ejecución
-----------------------
- --test : activa animación de prueba del VU meter (modo demo).
- --linux: evita intentar cargar win32com/pywin32 e inyecta módulos dummy; útil para desarrollo en Linux/macOS.

Ejemplos
--------
- Ejecutar en modo test en Linux/macOS:
    python3 PyControl.py --linux --test

- Uso programático (desde un intérprete con la aplicación corriendo o integrándolo):
    win.set_rig_name(1, 'IC-706')
    win.set_rig_freq(1, 14070000)
    win.set_rig_mode(1, 'USB')
    win.set_rig_led_color(1, (0,255,0), on=True)

Notas
-----
- La GUI está orientada a pruebas y desarrollo; la integración completa con OmniRig requiere pywin32 en Windows y no se activa en modo --linux.
- El archivo PyControl.ini se crea/actualiza en el directorio PyControl; no se sube automáticamente a repositorio remoto por políticas locales.

Si se desea una sección adicional con ejemplos de código de integración o la lista completa de claves posibles en PyControl.ini, puedo añadirla.

Formato de PyControl.ini
-----------------------
El archivo de configuración se encuentra en PyControl/PyControl.ini y tiene un formato simple KEY=VALUE por línea. Las claves actualmente reconocidas por la aplicación son:

- RIG: 'rig1' o 'rig2'
- LEFT: 'SWR', 'Power' o 'Signal'
- ANT: 'ant 1' o 'ant 2'
- VFO: 'VFO A' o 'VFO B'
- MODE: uno de 'CW','USB','LSB','AM','FM','DIG-U','DIG-L','CW-R'
- POWER: entero 0..255 (persistido al pulsar 'Set')
- VOLUME: entero 0..255 (persistido al pulsar 'Set')

Ejemplo de PyControl.ini:
RIG=rig1
LEFT=Signal
ANT=ant 1
VFO=VFO A
MODE=CW
POWER=0
VOLUME=0

Ejemplo de ejecución
--------------------
- Ejecutar en modo test en Linux/macOS (no requiere pywin32):
    python3 PyControl.py --linux --test

- Ejecutar en Windows integrando con OmniRig (requiere pywin32/OmniRig y permisos adecuados):
    python3 PyControl.py

Estos comandos deben ejecutarse desde el directorio PyControl o usando la ruta completa al script. Asegúrate de instalar las dependencias (PyQt5 y opcionales pywin32) en un entorno virtual antes de ejecutar.