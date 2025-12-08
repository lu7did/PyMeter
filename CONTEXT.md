Esta es la información de contexto que deberá ser usada para definir los requerimientos de construcción
del proyecto.

El programa debe estar realizado para Python 3.12.
El programa tiene que ser implementado utilizando un esqueleto de proyecto como el provisto por cookiecutter.
Se crearán dos directorios adicionales en la estructura uno denominado script y el otro ejemplos, el contenido de los mismos
no se incluirán en el workflow de validación de push
Preservar este archivo CONTEXT.md en el repositorio para documentar las metareglas de creación para éste proyecto, el mismo
debe ser reiterado cada vez que se inicia una secuencia de creación.
Debes generar un archivo README.md básico y actualizarlo con el push exitoso de cada PR durante la construcción de 
manera que esté permanentemente actualizado con las funciones disponibles.
Debes generar un archivo CHANGELOG.md y actualizarlo con el push exitoso de cada PR durante la construcción de manera
de tener trazabilidad de las acciones.
Todos los requerimientos y peticiones que ser realizan para producir un nuevo push tienen que ser agregados al documento
STORIES.md indicando el timestamp de cada nuevo ingreso.
Agrega al proyecto un archivo especificando que la licencia será MIT
genera la documentación automáticamente con pdoc o sphinx
El programa comenzará con Versión 1.0 build 000, cada push exitoso aumentará en 1 el número de build que encuentre en el archivo, el cual deberá
ser actualizado tanto en README.md como en CHANGELOG.md
Se creará y mantendrá actualizado en la medida que se agreguen funciones un workflow de validación consistente en
los siguientes productos:

* Ejecutar ruff para validar las reglas de formato y que no de errores.
* Ejecutar black para validar el formato consistente.
* Utilizar y validar el correcto uso de reglas de formateo PEP8.
* Utilizar y validar el correcto uso de convenciones PEP257 para los docstrings, aceptar solo si no hay errores.
* Ejecutar MyPy para los modulos que no sean explícitamente puestos fuera de su alcance, aceptar solo si no hay errores.
* Ejecutar PyRight para los modulos que no sean explicitamente puestos fuera de su alcance, aceptar solo si no hay errores.
* Implementar test automático con Pytest con hipótesis de test unitario que permitan la cobertura del 80% o mejor.
* Utilizar bandit para la evaluación básica de seguridad y que no queden observaciones.
* No utilizar Trufflehog en los controles de seguridad.
* Producir una documentación básica del funcionamiento del módulor y actualizarla con cada PR exitoso.
* Debe generarse y mantenerse actualizado un archivo requirements.txt que se usará para las dependencias de librerías.
* Si el proyecto tiene dependencias externas mandatorias u opcionales produce el archivo requirements.txt necesario.
* Se automatizará un workflow en github integrando la fase de CI/CD completa.
* Con cada PR exitoso genera o actualiza la focumentación básica con pdoc o sphinx.

Toda vez que sea posible hay que separar la lógica funcional de la lógica relacionada con la presentación e interacción con el usuario.
El programa debe utilizar técnicas de programación de object oriented.
El programa debe implementar las funciones toda vez que sea posible mediante el uso de patrones.
Las funciones implementadas deben tener tratamiento y gestión de las excepciones producidas durante el runtime además de las que sean específicamente pedidas en la historia a implementar.
Produce un archivo comprimido con toda la estructura necesaria para subir el proyecto a GitHub
El programa debe ser optimizado por performance.
El programa debe ser realizado en un formato tal que permita la utilización como package Python.
Las funciones implementadas deben tener tratamiento y gestión de las excepciones producidas durante el runtime además de las que sean específicamente pedidas en la historia a implementar.
Produce un archivo comprimido con toda la estructura necesaria para subir el proyecto a GitHub
El programa debe ser optimizado por performance.

Dada vez que se realiza un commit debe realizar las siguientes validaciones:
* Que las modificaciones introducidas en el push a realizar se han revisado en todos los módulos y verificado que se 
han introducido las modificaciones para que sean aceptadas por todos.
* Se hará una ejecución local de los programas que se harán en el workflow de validación y no se realizará el push
hasta que se satisfaga la condición de aceptación para minimizar en lo posible los builds fallidos.
* Cada vez que se introduzca un nuevo argumento o variable global se revisarán todos los módulos para que el mismo
tenga correcta definición y uso.
* Cada vez que se introduzca una nueva libraría o package Python se revisarán todos los módulos para que el mismo
tenga correcta definción y uso.
* Cada vez que se haga una modificación estructural en un módulo se hará un análisis de impacto en los restantes
y se producirá una actualización para evitar problemas, excepciones, faltantes y otras inconsistencias.
