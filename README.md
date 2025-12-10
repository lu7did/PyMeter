PyHamRemote

Conjunto de utilitarios y scripts para la automatización de estaciones de radioaficionado, centrado en concursos (contest) y DX.

Resumen de módulos principales:
- CONDXmap: Herramientas para procesar datos PSK/FT8/ADIF y generar mapas de condiciones de propagación (scripts: condxmap.py, adif2json.py, csv2json.py, grid2geo.py). Incluye datos de ejemplo en CONDXmap/data y salidas en CONDXmap/out.
- PyMeter: Aplicación de medidor/GUI para monitorizar niveles y señales; incluye PyMeter.py, scripts de instalación y utilidades en PyMeter/scripts.
- dx_proxy: Proxy/servicio para manejo de spots DX y datos de red (dx_proxy/dx_proxy.py).
- pycat: Herramienta auxiliar ligera (pycat/pycat.py).

Instalación y uso:
- Revisar los README.md específicos dentro de cada subdirectorio (CONDXmap/README.md, PyMeter/README.md) para instrucciones detalladas.
- Para PyMeter: ejecutar PyMeter/scripts/install.sh y lanzar PyMeter/scripts/PyMeter o PyMeter/PyMeter.py según la plataforma.
- Para CONDXmap: ejecutar los scripts en CONDXmap/ para procesar los ficheros en CONDXmap/data y generar imágenes en CONDXmap/out.

Licencia: Ver LICENSE.

Última actualización: 2025-12-10T18:11:33Z
