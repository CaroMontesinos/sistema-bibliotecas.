# Sistema de Gestión de Bibliotecas — Universidad X

Proyecto académico de Carolina. Aplicación local con Python 3.10 o superior, SQLite y una interfaz azul/naranja. No requiere paquetes externos.

## Iniciar desde Visual Studio Code

1. Extraiga todo el ZIP y abra la carpeta `biblioteca_universidad`.
2. Abra Terminal → Nueva terminal.
3. Ejecute `py -3 app.py` en Windows o `python3 app.py` en macOS/Linux.
4. Abra http://127.0.0.1:8000 y mantenga la terminal abierta.

También puede abrir `iniciar_windows.bat`. Necesita Python instalado: https://www.python.org/downloads/ . Para detener el servidor presione Ctrl+C. El servidor es local, no es un enlace público.

## Único bibliotecario: Jorge

RUT ficticio de demostración: **90000001-4**.
Contraseña de demostración: **90000001**.

La pantalla de acceso no muestra estas credenciales. El profesor puede utilizar esta cuenta para revisar el funcionamiento. La autoría del proyecto sigue siendo Carolina; su cuenta en el sistema es de estudiante cuando se enrole.

## Enrolamiento de estudiantes

Hay 20 nombres en el listado de estudiantes proporcionado, sin RUT ni cuentas de acceso iniciales. Giordano no se incluye porque figura como profesor en el listado original. No se consultan Canvas ni otras fuentes externas.

1. Ingrese como Jorge.
2. Abra «Usuarios / enrolamiento».
3. Seleccione un estudiante pendiente del listado.
4. Registre su RUT con dígito verificador.
5. Guarde. El rol será siempre Estudiante; no se puede crear otro bibliotecario desde esta pantalla ni enviando un rol diferente al servidor.
6. El estudiante podrá ingresar con su RUT y con contraseña inicial igual al cuerpo del RUT, sin puntos, guion ni dígito verificador.

Para ensayar sin datos personales reales, utilice un RUT ficticio de prueba como 90000005-7 (contraseña 90000005), dejando claro que es un dato simulado. Ningún RUT de prueba está asociado de antemano a los nombres de la lista. El sistema valida formato, dígito verificador y unicidad; no comprueba la identidad civil ante un registro externo.

La contraseña predecible es una regla solicitada para esta demostración. Se guarda mediante PBKDF2 con sal. Para uso real se requiere una clave personal y un proceso de recuperación; esa función aún no está implementada.

## Cinco funciones del caso

| Función | Estudiante | Jorge |
|---|---|---|
| Buscar libros | Título, autor y código; filtros | Mismas consultas y alta de ejemplares |
| Reservar | Reserva para su propia cuenta | Puede registrar una reserva para un estudiante enrolado |
| Prestar | Consulta sus préstamos | Registra ejemplar, estudiante y fechas |
| Devolver | Consulta el estado de su devolución | Registra la devolución y libera el ejemplar |
| Multas | Consulta sus multas y saldos | Consulta todas y registra pagos completos de demostración |

El catálogo inicial tiene seis ejemplares. Una instalación nueva comienza sin préstamos, reservas ni multas, porque los estudiantes todavía deben enrolarse. Los botones administrativos de reserva/préstamo requieren al menos un estudiante enrolado.

## Ejemplo de operación

Enrole un estudiante con un RUT de prueba. Registre a su nombre un préstamo de E001 con inicio 01/11/2026 y vencimiento 06/11/2026. Devuélvalo el 09/11/2026: se genera una multa de $4.500. Compruebe el registro, aviso interno y reportes. Después registre el pago de muestra: el saldo pendiente disminuye, pero la multa original permanece en el historial. No hay cobro bancario.

Una reserva no es un préstamo: Jorge registra el préstamo al entregar el ejemplar. Si otro estudiante tiene la primera reserva activa del ejemplar, no se permite prestarlo a otro destinatario.

## Reportes y ficha de recurso

Los reportes permiten seleccionar fecha de corte y contrastar los registros originales. Un préstamo devuelto deja de aparecer entre los vencidos actuales y permanece en el histórico de devoluciones atrasadas. Las multas del reporte son importes generados hasta el corte; la sección Multas muestra el saldo pendiente actual.

Pulse un título del catálogo para consultar su ficha, reservar, exportar CSV/RIS, copiar la referencia o imprimir. Los libros físicos no tienen texto completo registrado. Hay una guía original de muestra para probar lectura en línea.

## Actualizar una versión anterior

Detenga el servidor y haga una copia de `biblioteca.sqlite3` antes de actualizar. Si desea conservar sus registros, coloque esa base en la carpeta de la nueva versión. Al iniciar se migra una vez: la antigua cuenta profesor pasa a Jorge; las demás cuentas pierden las credenciales anteriores y deben enrolarse. Los historiales no se eliminan. Las cuentas antiguas Carolina y Franco se relacionan con sus nombres completos cuando corresponde. Las instalaciones nuevas no contienen préstamos precargados.

No es necesario borrar la base. Para comenzar completamente de cero, conserve el respaldo, retire la base de la carpeta con el servidor detenido y vuelva a iniciar.

## Pruebas y límites

Ejecute `py -3 -m unittest discover -s tests -v`: 20 pruebas aprobadas en el entorno de creación. Las pruebas crean sus propios datos ficticios en una base temporal aislada. Con Node disponible puede ejecutar `node tests/verify_reports.cjs` para comprobar los reportes mediante un DOM mínimo.

La revisión visual en navegador no pudo completarse por restricciones del entorno. No se han medido carga, cobertura o SonarQube. El workflow incluido está preparado para GitHub Actions; no acredita una ejecución remota ni reglas de protección configuradas.

Es un prototipo local con transacciones, permisos en el servidor, sesiones y CSRF. Microservicios, alta disponibilidad, correo externo, pagos bancarios, recuperación de claves y despliegue público quedan pendientes. Los avisos se guardan dentro del sistema.

## Referencia conceptual

MDN Web Docs. Django Tutorial: The Local Library website.
https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Server-side/Django/Tutorial_local_library_website

Referencia consultada el 9 de noviembre de 2026. El código de esta entrega es una implementación propia en Python estándar; no utiliza Django. La apariencia toma como referencia las capturas proporcionadas, con identidad Universidad X.

## Presentación del inicio

El inicio muestra accesos operativos, indicadores y reservas pendientes. Se retiraron el bloque promocional azul, la etiqueta técnica, el texto de servicios y el pie de página de demostración.

Se refinaron los bloques visuales con bordes definidos, separación uniforme, sombras suaves y tablas delimitadas. El ajuste se aplica a tarjetas de acciones, indicadores y paneles.
