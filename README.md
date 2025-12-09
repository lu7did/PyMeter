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

