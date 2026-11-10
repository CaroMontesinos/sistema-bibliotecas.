# Validación ejecutada

Resultado actual: **20 pruebas aprobadas** con `python -m unittest discover -s tests -v`.

Se comprobaron reglas de multas, devolución idempotente, pagos sin duplicación, permisos, consultas por estudiante, préstamo exclusivo, reservas prioritarias, fechas inválidas, RUT y enrolamiento, listado de 20 pendientes, ausencia de credenciales en la pantalla y eliminación de la sección de evaluación.

La migración desde una base previa se probó conservando tres préstamos, dejando solo a Jorge como bibliotecario y recuperando el mismo identificador del estudiante al enrolarlo.

El recorrido HTTP ejecuta acceso por RUT, sesión, CSRF, devolución y rechazo de permisos contra un servidor real. Los datos de prueba se crean exclusivamente en bases temporales; una instalación nueva no trae estudiantes enrolados ni préstamos.

También aprobaron `node --check static/app.js` y `node tests/verify_reports.cjs`, que comprueba la función real de reportes con un DOM mínimo. No sustituyen la revisión visual en navegador, que sigue pendiente por restricciones del entorno. No se mide cobertura, carga ni SonarQube.
