// Verifica la función de presentación real con un DOM mínimo, sin dependencias.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const elements=new Map();const el=s=>{if(!elements.has(s))elements.set(s,{innerHTML:'',textContent:'',value:s==='#cut'?'2026-11-09':'',hidden:false,classList:{toggle(){}},addEventListener(){}});return elements.get(s);};
const context={document:{querySelector:el,querySelectorAll:()=>[]},sessionStorage:{getItem:()=>'',setItem(){}},fetch:async()=>({ok:false,json:async()=>({error:'Sin sesión'})}),console,setTimeout};vm.createContext(context);
vm.runInContext(fs.readFileSync(require('path').join(__dirname,'../static/app.js'),'utf8'),context);
const fixture={user:{id:1,username:'profesor',role:'bibliotecario'},loans:[{id:1,code:'E001',borrower:'franco',start:'2026-11-01',due:'2026-11-06',returned:'2026-11-09',fine:4500},{id:2,code:'E002',borrower:'ana',start:'2026-11-01',due:'2026-11-08',returned:null,fine:0},{id:3,code:'E003',borrower:'franco',start:'2026-11-01',due:'2026-11-07',returned:'2026-11-09',fine:3000}]};
context.fixture=fixture;vm.runInContext("data=fixture;page='reports';render()",context);
let output=el('#reportBody').innerHTML;assert(output.includes('$7.500'));let tables=output.match(/<table>.*?<\/table>/g);assert(tables[0].includes('E002'));assert(!tables[0].includes('E001'));assert(tables[1].includes('4.500'));assert(tables[1].includes('3.000'));
el('#cut').value='2026-11-08';el('#cut').onchange();output=el('#reportBody').innerHTML;tables=output.match(/<table>.*?<\/table>/g);assert(tables[0].includes('E001'));assert(tables[0].includes('E003'));assert(!tables[0].includes('E002'));assert(tables[1].includes('Sin registros'));assert(!output.includes('$7.500'));
console.log('OK: dos salidas de reporte, corte actual e histórico, importes y registros originales.');
