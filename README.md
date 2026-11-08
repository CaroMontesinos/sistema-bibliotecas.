# Sistema de Gestión de Bibliotecas

Interfaz estática para GitHub Pages. El servidor y la base de datos permanecen alojados externamente. Esto permite registro real por cuenta y datos compartidos entre dispositivos; no se simula la autenticación con localStorage.

## Publicación

Crear un repositorio público llamado `sistema-bibliotecas.` en la cuenta `CaroMontesinos`. Subir el contenido de esta carpeta a la raíz de `main`. En Settings > Pages, elegir Deploy from a branch, main, /(root). La URL la confirma GitHub después del despliegue.

Los archivos mínimos son index.html, app.js, style.css y .nojekyll. La carpeta src contiene el código fuente y no es necesaria para servir la página. No se deben subir bases de datos, contraseñas ni archivos .env.

## Acceso

Cada visitante debe registrarse con nombre, usuario, contraseña de al menos 10 caracteres y tipo de usuario. Las cuentas ya registradas en la biblioteca original se conservan. La sesión de GitHub Pages se guarda temporalmente en sessionStorage y se revoca al cerrar sesión; caduca a las 24 horas. Cerrar la pestaña elimina la copia local. No se utilizan cookies de terceros.

## Arquitectura

Interfaz: React y TypeScript, compilados a JavaScript estático. API: Worker Vinext con Cloudflare D1. CORS permite únicamente el origen de GitHub Pages de CaroMontesinos y el origen propio del servidor. Las reglas de negocio se verifican en el servidor. La aplicación no migra el servidor Python a GitHub Pages.

El prototipo usa datos de demostración y no procesa pagos. Máximo tres préstamos y tres reservas; plazo de 14 días. Las reservas no retienen inventario. Las pruebas Python del informe original no miden automáticamente la cobertura de esta interfaz. SonarQube y pruebas de carga quedan pendientes.

## Cambios en el código

`src/App.tsx` es la interfaz y `src/api.ts` configura la API. La versión servida es app.js. Para recompilar desde esta carpeta: `npm install` y `npm run build` (requiere Node.js).
