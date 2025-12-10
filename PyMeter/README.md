# PyMeter

PyMeter es una aplicación gráfica en Python (PyQt5) que implementa un VU-metro y varios controles asociados para pruebas y demostraciones.

Nivel actual
- El VU-metro principal acepta valores en el rango 0..255 y muestra el nivel en una escala horizontal de 10 LEDs (verde/amarillo/rojo).

Argumentos de línea de comandos
- --config=<ruta>  : archivo de configuración (por defecto PyMeter.ini) con pares CLAVE=VALOR.
- --test           : activa modo de prueba; el vumetro se animará subiendo y bajando cíclicamente y el indicador Ready titilará.

Propósito de cada control
- Ready (Online/Offline) + LED: indica si la aplicación está Online (LED verde lime) o Offline (LED verde oscuro). Cuando está Offline, los botones y sliders quedan desactivados y el vumetro muestra sólo colores apagados.
- TR (RX/TX) button: botón de alternancia RX (0) / TX (1). El LED dentro del botón muestra verde lime para RX y rojo intenso para TX; en Offline se fuerza a RX con LED apagado (verde oscuro).
- TUNE button: botón con LED integrado; inicialmente en verde lime. Al pulsar, el LED se pone rojo vivo por 2 segundos y luego retorna a verde lime.
- A<>B (Swap) button: botón momentáneo que emite un evento de intercambio entre VFOs.
- VFO (VFOA/VFOB) button: botón toggle; alterna entre VFOA (LED verde oscuro/verde lime) y VFOB (LED rojo oscuro/rojo intenso). Estado persistido en la configuración.
- Signal / Power / SWR radios: grupo mutuamente excluyente que emite evento cuando cambia la selección; su valor se guarda en la configuración bajo SIGNAL.
- Ant 1 / Ant 2 radios: selector de antena; emite evento y persiste en la configuración bajo ANT.
- Rig radios (rig1 / rig2) con etiquetas modificables: selector mutuamente excluyente; actualiza la etiqueta pequeña junto a Online/Offline y persiste en la configuración bajo RIG.
- Power slider (0..255): controla un valor Power cuyo número mostrado se calcula como trunc(int((95*S/255)+5)) y se muestra con unidad "W" (p. ej. "42W"). Su valor bruto 0..255 se guarda en la configuración bajo POWER.
- Volumen slider (0..255): controla un valor Volumen cuyo número mostrado se calcula como trunc(int(10*S/255)). Su valor bruto 0..255 se guarda en la configuración bajo VOLUME.

Archivo de configuración (PyMeter.ini)
- Formato simple de líneas CLAVE=VALOR. Claves usadas actualmente:
  - SIGNAL (Signal|Power|SWR)
  - RIG (rig1|rig2)
  - ANT (Ant 1|Ant 2)
  - VFO (VFOA|VFOB)
  - POWER (0..255)
  - VOLUME (0..255)

Ejecución
- scripts/install.sh : script para instalar dependencias (si existe).
- scripts/PyMeter     : script que lanza la aplicación.

Notas de comportamiento
- Los sliders Power y Volumen son independientes; cambiar uno no afecta al otro.
- Tras cualquier cambio en un slider se refrescan las etiquetas de ambos sliders para mostrar sus valores actuales calculados.
- Cuando la aplicación inicia, si existe PyMeter.ini, los controles se inicializan con los valores guardados; en caso contrario se crea un archivo con valores por defecto.

Métodos y atributos públicos para actualizar controles

A continuación se listan los métodos y atributos (públicos o de uso programático) que pueden usarse desde código externo para actualizar valores o estados de los distintos controles de la interfaz:

Métodos (uso recomendado)
- MainWindow.set_meter(value: int): actualiza el VU-meter (rango 0..255).
- MainWindow.set_tr(value: int): establece el estado TR (0=RX, 1=TX) y actualiza la visualización interna del botón.
- MainWindow.set_ready(enabled: bool): habilita/deshabilita el modo Online/Offline; actualiza ready LED, label, habilita/deshabilita botones y sliders, y ajusta colores de LEDs.
- MainWindow.set_rig_name(index: int, name: str): actualiza la etiqueta visible para rig1 (index=1) o rig2 (index=2).
- MainWindow._handle_slider_change(name: str, value: int, slider_obj): manejador unificado que actualiza la etiqueta numérica asociada al slider ('power' o 'volume') y persiste el valor.
- MainWindow._refresh_sliders(): refresca las etiquetas numéricas de los sliders desde sus valores actuales.
- VUMeter.set_value(value: int): establece el valor interno del vumeter y redibuja el widget.
- VUMeter.set_enabled(enabled: bool): habilita/deshabilita la representación del vumeter (colores apagados cuando está deshabilitado).
- LedIndicator.set_on(state: bool): enciende/apaga el LED (visualmente).
- LedIndicator.is_on() -> bool: consulta el estado del LED.
- LedIndicator.set_color_on(color: Tuple[int,int,int]): cambia el color cuando el LED está encendido.
- LedIndicator.set_color_off(color: Tuple[int,int,int]): cambia el color cuando el LED está apagado/dim.
- LedButton.set_state(value: int): establece el estado lógico del botón compuesto (0/1) y actualiza label y LED.
- LedButton.get_state() -> int: devuelve el estado lógico actual del botón.
- VFOButton.set_state(value: int): override específico de VFO para mostrar VFOA/VFOB.

Atributos de instancia con acceso/uso programático (controles expuestos)
- MainWindow.meter: instancia de VUMeter.
- MainWindow.tr: instancia de LedButton (TR RX/TX).
- MainWindow.tune: instancia de TuneButton.
- MainWindow.vfo: instancia de VFOButton.
- MainWindow.swap: instancia de SwapButton.
- MainWindow.ready_label, MainWindow.ready_led, MainWindow.ready_rig_label: controles que muestran Online/Offline y nombre de rig.
- MainWindow.rb_signal, rb_power, rb_swr: radio buttons de modo.
- MainWindow.rb_ant1, rb_ant2: radio buttons de antena.
- MainWindow.rb_rig1, rb_rig2: radio buttons de selección de rig.
- MainWindow.rig1_label, MainWindow.rig2_label: labels donde se muestran los nombres de los rigs (modificables vía set_rig_name).
- MainWindow.slider_power, MainWindow.slider_power_value: slider y label numérico asociado a Power.
- MainWindow.slider_vol, MainWindow.slider_vol_value: slider y label numérico asociado a Volumen.
- MainWindow._online (bool): estado interno Online/Offline (puede consultarse con getattr). 

Notas de uso
- MainWindow.set_ready(True/False) actúa de forma global: actualiza ready LED/label, habilita/deshabilita botones (TR, TUNE, VFO, SWAP) y sliders, y regula colores de LEDs según el estado online/offline.
- Para actualizar las etiquetas numéricas de Power/Volumen, utilizar MainWindow.slider_power.setValue(...) o MainWindow.slider_vol.setValue(...); los handlers internos llamarán a _handle_slider_change/_refresh_sliders que actualizan las etiquetas y persisten valores.
- Para persistir manualmente el estado actual en el fichero de configuración, MainWindow._write_config() escribe SIGNAL, RIG, ANT, VFO, POWER y VOLUME en el archivo configurado.

Funciones a nivel de módulo
- updateRigStatus(omni, win): función pública que consulta el estado de OmniRig y actualiza etiquetas de rigs y estado Online/Offline llamando a win.set_ready(...).


