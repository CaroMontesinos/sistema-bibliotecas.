import {build} from 'esbuild';
await build({entryPoints:['src/main.tsx'],outfile:'app.js',bundle:true,minify:true,format:'esm',platform:'browser',jsx:'automatic',define:{'process.env.NODE_ENV':'"production"'}});
console.log('Interfaz compilada en app.js');
