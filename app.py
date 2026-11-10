"""SG Biblio: prototipo académico modular, Python 3.10+, sin dependencias."""
import re 
from contextlib import contextmanager
import csv, hashlib, hmac, io, json, os, secrets, sqlite3
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from http.cookies import SimpleCookie
from urllib.parse import urlparse
ROOT=Path(__file__).parent
DB=ROOT/'biblioteca.sqlite3'
SESSIONS={}
@contextmanager
def connect():
    conexion = sqlite3.connect(DB, timeout=15)
    try:
        conexion.row_factory = sqlite3.Row
        conexion.execute("PRAGMA foreign_keys=ON")
        with conexion:
            yield conexion
    finally:
        conexion.close()
def password(value, salt):
    return hashlib.pbkdf2_hmac(
        'sha256',
        value.encode(),
        salt.encode(),
        200000
    ).hex()
STUDENTS = ['Cristóbal Andrés Andalaft Cornejo', 'Daniel Cristian Elias Campos Carrasco', 'Elia Daniela Carinao Lincan', 'Patricio Eduardo Farías Inzunza', 'Franco Nicolás Flores Pizarro', 'Luis Simón Gómez Hernández', 'Rodrigo Alejandro Herrera Herrera', 'Nicolás Andrés Huenchual Donoso', 'Matías Nicolás Lagos Lizana', 'Eduard Alberto Lizcano Tamayo', 'Cristopher Eduardo Medina Medina', 'Carolina Elissette Montesinos Vera', 'Felipe Eduardo Ocaranza Pérez', 'Pablo Andrés Rencoret Yevilaf', 'Benjamín Patricio Alexis Reyes Tapia', 'Juan Esteban Sarmiento Hernández', 'Eduardo Alejandro Sepúlveda Sepúlveda', 'Matías Salvador Sepúlveda Vásquez', 'Martin Ignacio Silva Pérez', 'Ignacio Sebastian Yáñez Machmar']

JORGE_RUT = '90000001-4'  # RUT ficticio de la demostración.
def normalize_rut(value):
    raw=re.sub(r'[.\s-]','',str(value)).upper()
    if not re.fullmatch(r'[1-9][0-9]{6,7}[0-9K]',raw): raise ValueError('Ingresa un RUT con dígito verificador.')
    body,dv=raw[:-1],raw[-1]
    n=11-sum(int(v)*(2+i%6) for i,v in enumerate(reversed(body)))%11
    expected='0' if n==11 else 'K' if n==10 else str(n)
    if dv!=expected: raise ValueError('Dígito verificador inválido.')
    return body+'-'+dv
def fine(expected,actual): return max(0,(date.fromisoformat(actual)-date.fromisoformat(expected)).days)*1500
def init():
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, salt TEXT, hash TEXT, role TEXT);
CREATE TABLE IF NOT EXISTS books(id INTEGER PRIMARY KEY,title TEXT,author TEXT,code TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS loans(id INTEGER PRIMARY KEY,book_id INTEGER REFERENCES books(id),user_id INTEGER REFERENCES users(id),created_by INTEGER REFERENCES users(id),start TEXT,due TEXT,returned TEXT,fine INTEGER DEFAULT 0);
CREATE UNIQUE INDEX IF NOT EXISTS active_copy ON loans(book_id) WHERE returned IS NULL;
CREATE TABLE IF NOT EXISTS reservations(id INTEGER PRIMARY KEY,book_id INTEGER REFERENCES books(id),user_id INTEGER REFERENCES users(id),created TEXT,status TEXT DEFAULT 'Activa');
CREATE UNIQUE INDEX IF NOT EXISTS active_reservation ON reservations(book_id,user_id) WHERE status='Activa';
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,actor TEXT,event TEXT,detail TEXT,created TEXT);
CREATE TABLE IF NOT EXISTS payments(loan_id INTEGER PRIMARY KEY REFERENCES loans(id),amount INTEGER NOT NULL,actor TEXT NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notices(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),message TEXT,created TEXT);''')
        c.executescript('CREATE TABLE IF NOT EXISTS roster(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL); CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);')
        c.executemany('INSERT OR IGNORE INTO roster(name) VALUES(?)',[(name,) for name in STUDENTS])
        if 'rut' not in {r[1] for r in c.execute('PRAGMA table_info(users)')}: c.execute('ALTER TABLE users ADD COLUMN rut TEXT')
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS user_rut ON users(rut)')
        if not c.execute("SELECT value FROM settings WHERE key='jorge_roster_v1'").fetchone():
            # Migración: mantener historiales; las cuentas previas requieren enrolamiento.
            old=c.execute("SELECT id FROM users WHERE username IN ('Jorge','profesor') ORDER BY CASE username WHEN 'Jorge' THEN 0 ELSE 1 END LIMIT 1").fetchone()
            c.execute("UPDATE users SET rut=NULL,role='estudiante'")
            salt=secrets.token_hex(16)
            if old:
                c.execute("UPDATE users SET username='Jorge',role='bibliotecario',rut=?,salt=?,hash=? WHERE id=?",(JORGE_RUT,salt,password('90000001',salt),old['id']))
            else:
                c.execute("INSERT INTO users(username,role,rut,salt,hash) VALUES('Jorge','bibliotecario',?,?,?)",(JORGE_RUT,salt,password('90000001',salt)))
            for previous,new in [('carolina','Carolina Elissette Montesinos Vera'),('franco','Franco Nicolás Flores Pizarro')]:
                if not c.execute('SELECT id FROM users WHERE username=?',(new,)).fetchone():c.execute('UPDATE users SET username=? WHERE username=?',(new,previous))
            c.execute("INSERT INTO settings(key,value) VALUES('jorge_roster_v1','1')")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_librarian ON users(role) WHERE role='bibliotecario'")
        if not c.execute('SELECT COUNT(*) FROM books').fetchone()[0]:
            c.executemany('INSERT INTO books(title,author,code) VALUES(?,?,?)', [('Ingeniería de software','Ian Sommerville','E001'),('Código limpio','Robert C. Martin','E002'),('Bases de datos','Abraham Silberschatz','E003'),('Redes de computadoras','Andrew Tanenbaum','E004'),('Patrones de diseño','Erich Gamma y otros','E005'),('Sistemas operativos','William Stallings','E006')])

def log(c,u,event,detail): c.execute('INSERT INTO audit(actor,event,detail,created) VALUES(?,?,?,?)',(u['username'],event,detail,datetime.now().isoformat(timespec='seconds')))
def mutate(u,path,d):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if path not in ('/api/reserve',) and u['role']!='bibliotecario':
            log(c,u,'ACCESO_RECHAZADO',path); return 403,{'error':'No tienes permiso para modificar préstamos ajenos ni administrar el catálogo.'}
        if path=='/api/user':
            person=c.execute('SELECT * FROM roster WHERE id=?',(int(d['roster_id']),)).fetchone()
            if not person: raise ValueError('Selecciona un estudiante del listado autorizado.')
            rut=normalize_rut(d.get('rut','')); name=person['name']
            existing=c.execute('SELECT * FROM users WHERE username=?',(name,)).fetchone()
            if existing and existing['rut']: raise ValueError('Este estudiante ya está enrolado.')
            salt=secrets.token_hex(16)
            if existing:
                c.execute("UPDATE users SET rut=?,salt=?,hash=?,role='estudiante' WHERE id=?",(rut,salt,password(rut.split('-')[0],salt),existing['id']))
            else:
                c.execute("INSERT INTO users(username,rut,salt,hash,role) VALUES(?,?,?,?,'estudiante')",(name,rut,salt,password(rut.split('-')[0],salt)))
            log(c,u,'ESTUDIANTE_ENROLADO',f'{name}; RUT {rut}; rol estudiante')
        elif path=='/api/book':
            title=str(d.get('title','')).strip(); author=str(d.get('author','')).strip(); code=str(d.get('code','')).strip()
            if not all((title,author,code)): raise ValueError('Completa título, autor y código del ejemplar.')
            c.execute('INSERT INTO books(title,author,code) VALUES(?,?,?)',(title,author,code)); log(c,u,'EJEMPLAR_CREADO',code)
        elif path=='/api/loan':
            bid=int(d['book_id']); uid=int(d['user_id']); start=date.fromisoformat(d['start']); due=date.fromisoformat(d['due'])
            if due<start: raise ValueError('El vencimiento no puede ser anterior al préstamo.')
            if not c.execute("SELECT id FROM users WHERE id=? AND role='estudiante' AND rut IS NOT NULL",(uid,)).fetchone(): raise ValueError('Selecciona un estudiante válido.')
            if c.execute('SELECT id FROM loans WHERE book_id=? AND returned IS NULL',(bid,)).fetchone(): raise ValueError('El ejemplar ya tiene un préstamo activo.')
            queued=c.execute("SELECT user_id FROM reservations WHERE book_id=? AND status='Activa' ORDER BY id LIMIT 1",(bid,)).fetchone()
            if queued and queued[0]!=uid: raise ValueError('El ejemplar está reservado para otro estudiante.')
            cur=c.execute('INSERT INTO loans(book_id,user_id,created_by,start,due) VALUES(?,?,?,?,?)',(bid,uid,u['id'],start.isoformat(),due.isoformat()))
            c.execute("UPDATE reservations SET status='Atendida' WHERE book_id=? AND user_id=? AND status='Activa'",(bid,uid)); log(c,u,'PRESTAMO_CREADO',f'P{cur.lastrowid:03d}'); c.execute('INSERT INTO notices(user_id,message,created) VALUES(?,?,?)',(uid,f'Préstamo P{cur.lastrowid:03d} registrado. Vence: {due}.',datetime.now().isoformat()))
        elif path=='/api/return':
            loan=c.execute('SELECT * FROM loans WHERE id=?',(int(d['id']),)).fetchone()
            if not loan: raise ValueError('Préstamo inexistente.')
            actual=date.fromisoformat(d['returned']).isoformat()
            if actual<loan['start']: raise ValueError('La devolución no puede ser anterior al préstamo.')
            if loan['returned']:
                if actual!=loan['returned']: raise ValueError('El préstamo ya fue devuelto en otra fecha.')
                return 200,{'message':'La devolución ya estaba registrada. No se duplicó la multa.'}
            amount=fine(loan['due'],actual); c.execute('UPDATE loans SET returned=?,fine=? WHERE id=?',(actual,amount,loan['id'])); log(c,u,'DEVOLUCION',f"P{loan['id']:03d}; fecha {actual}; multa ${amount}"); c.execute('INSERT INTO notices(user_id,message,created) VALUES(?,?,?)',(loan['user_id'],f"Devolución P{loan['id']:03d} registrada. Multa: ${amount}.",datetime.now().isoformat()))
        elif path=='/api/pay':
            loan=c.execute('SELECT * FROM loans WHERE id=?',(int(d['id']),)).fetchone()
            if not loan or not loan['returned'] or loan['fine']<=0: raise ValueError('No hay una multa liquidada para registrar el pago.')
            if c.execute('SELECT loan_id FROM payments WHERE loan_id=?',(loan['id'],)).fetchone(): return 200,{'message':'El pago ya estaba registrado. No se duplicó.'}
            now=datetime.now().isoformat(timespec='seconds')
            c.execute('INSERT INTO payments(loan_id,amount,actor,created) VALUES(?,?,?,?)',(loan['id'],loan['fine'],u['username'],now))
            log(c,u,'PAGO_DEMOSTRACION',f"P{loan['id']:03d}; importe ${loan['fine']}")
            c.execute('INSERT INTO notices(user_id,message,created) VALUES(?,?,?)',(loan['user_id'],f"Pago de demostración registrado para P{loan['id']:03d}: ${loan['fine']}.",now))
        elif path=='/api/reserve':
            uid=u['id'] if u['role']=='estudiante' else int(d['user_id'])
            if not c.execute("SELECT id FROM users WHERE id=? AND role='estudiante' AND rut IS NOT NULL",(uid,)).fetchone(): raise ValueError('Estudiante inválido.')
            c.execute('INSERT INTO reservations(book_id,user_id,created) VALUES(?,?,?)',(int(d['book_id']),uid,datetime.now().isoformat())); log(c,u,'RESERVA_CREADA',str(d['book_id']))
        else: return 404,{'error':'Operación desconocida.'}
    return 200,{'message':'Operación guardada correctamente.'}
def state(u):
    with connect() as c:
        admin=u['role']=='bibliotecario'
        books=[dict(r) for r in c.execute('SELECT b.*,NOT EXISTS(SELECT 1 FROM loans l WHERE l.book_id=b.id AND returned IS NULL) AS available FROM books b')]
        loans=[dict(r) for r in c.execute('SELECT l.*,p.created paid_at,p.actor paid_by,b.title,b.code,u.username borrower,a.username creator FROM loans l JOIN books b ON b.id=l.book_id JOIN users u ON u.id=l.user_id JOIN users a ON a.id=l.created_by LEFT JOIN payments p ON p.loan_id=l.id '+('' if admin else 'WHERE l.user_id=?'),() if admin else (u['id'],))]
        reserves=[dict(r) for r in c.execute('SELECT r.*,b.title,u.username FROM reservations r JOIN books b ON b.id=r.book_id JOIN users u ON u.id=r.user_id '+('' if admin else 'WHERE r.user_id=?'),() if admin else (u['id'],))]
        notices=[dict(r) for r in c.execute('SELECT * FROM notices '+('' if admin else 'WHERE user_id=?')+' ORDER BY id DESC',() if admin else (u['id'],))]
        return dict(roster=[dict(r) for r in c.execute('SELECT r.id,r.name,u.rut FROM roster r LEFT JOIN users u ON u.username=r.name ORDER BY r.name')] if admin else [],accounts=[dict(r) for r in c.execute('SELECT id,username,rut,role FROM users WHERE rut IS NOT NULL ORDER BY id')] if admin else [],user=dict(u),books=books,loans=loans,reservations=reserves,notices=notices,users=[dict(r) for r in c.execute("SELECT id,username,rut FROM users WHERE role='estudiante' AND rut IS NOT NULL")] if admin else [],audit=[dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')] if admin else [])
class Handler(BaseHTTPRequestHandler):
    def reply(self,code,data,ctype='application/json; charset=utf-8',headers=None):
        body=json.dumps(data,ensure_ascii=False).encode() if ctype.startswith('application/json') else data
        self.send_response(code); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body))); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(body)
    def session(self):
        try:
            ck=SimpleCookie(self.headers.get('Cookie','')); return SESSIONS.get(ck['sid'].value)
        except KeyError: return None
    def do_GET(self):
        path=urlparse(self.path).path
        if path in ('/','/app.js','/style.css','/lectura.html'):
            fn={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/lectura.html':'lectura.html'}[path]; return self.reply(200,(ROOT/'static'/fn).read_bytes(),{'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8','/lectura.html':'text/html; charset=utf-8'}[path])
        s=self.session()
        if not s: return self.reply(401,{'error':'Inicia sesión para continuar.'})
        if path=='/api/state': return self.reply(200,state(s['user']))
        return self.reply(404,{'error':'No encontrado.'})
    def do_POST(self):
        # Solicitudes del mismo origen; JSON impide formularios externos simples.
        origin=self.headers.get('Origin')
        if origin and origin!=f"http://{self.headers.get('Host')}": return self.reply(403,{'error':'Origen no permitido.'})
        if not self.headers.get('Content-Type','').startswith('application/json'): return self.reply(415,{'error':'Se requiere JSON.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>16384: return self.reply(413,{'error':'Solicitud demasiado grande.'})
            d=json.loads(self.rfile.read(length)); path=urlparse(self.path).path
            if path=='/api/login':
                try: rut=normalize_rut(d.get('rut',''))
                except ValueError: return self.reply(401,{'error':'RUT o contraseña incorrectos.'})
                with connect() as c: u=c.execute('SELECT * FROM users WHERE rut=?',(rut,)).fetchone()
                if not u or not hmac.compare_digest(u['hash'],password(d.get('password',''),u['salt'])): return self.reply(401,{'error':'RUT o contraseña incorrectos.'})
                token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(24); SESSIONS[token]={'user':{'id':u['id'],'username':u['username'],'role':u['role'],'rut':u['rut']},'csrf':csrf}
                return self.reply(200,{'csrf':csrf},headers={'Set-Cookie':f'sid={token}; HttpOnly; SameSite=Strict; Path=/'})
            s=self.session()
            if not s: return self.reply(401,{'error':'Inicia sesión.'})
            if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']): return self.reply(403,{'error':'Sesión de formulario inválida. Vuelve a ingresar.'})
            if path=='/api/logout':
                ck=SimpleCookie(self.headers.get('Cookie','')); SESSIONS.pop(ck['sid'].value,None); return self.reply(200,{},headers={'Set-Cookie':'sid=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict'})
            code,result=mutate(s['user'],path,d); return self.reply(code,result)
        except (ValueError,KeyError,TypeError): return self.reply(400,{'error':'Datos inválidos. Revisa fechas, campos e identificadores.'})
        except sqlite3.IntegrityError: return self.reply(409,{'error':'Registro duplicado o referencia inválida. Comprueba la disponibilidad y las reservas.'})
        except sqlite3.Error: return self.reply(503,{'error':'No se pudo guardar. Intenta nuevamente.'})
if __name__=='__main__':
    init(); print('Biblioteca Universidad X: http://127.0.0.1:8000\nJorge (bibliotecario): RUT 90000001-4 / contraseña 90000001\nCtrl+C para detener.')
    ThreadingHTTPServer(('127.0.0.1',8000),Handler).serve_forever()
