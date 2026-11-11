import importlib.util, json, tempfile, threading, unittest, urllib.request, urllib.error, http.cookiejar
from pathlib import Path
spec=importlib.util.spec_from_file_location('app',Path(__file__).parents[1]/'app.py'); app=importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); app.DB=Path(self.tmp.name)/'test.sqlite3';app.SESSIONS.clear();app.init()
        self.seed=app.state({'id':1,'username':'Jorge','role':'bibliotecario'})
        with app.connect() as c:
            for uid,name,rut in [(2,'Carolina Elissette Montesinos Vera','90000002-2'),(3,'Franco Nicolás Flores Pizarro','90000003-0'),(4,'Patricio Eduardo Farías Inzunza','90000004-9')]:
                salt='test-salt';c.execute("INSERT INTO users(id,username,rut,salt,hash,role) VALUES(?,?,?,?,?,'estudiante')",(uid,name,rut,salt,app.password(rut.split('-')[0],salt)))
            c.executemany('INSERT INTO loans(book_id,user_id,created_by,start,due,returned,fine) VALUES(?,?,1,?,?,?,?)',[(1,3,'2026-11-01','2026-11-06',None,0),(2,4,'2026-11-01','2026-11-08',None,0),(3,3,'2026-11-01','2026-11-07','2026-11-09',3000)])
        self.admin={'id':1,'username':'Jorge','role':'bibliotecario'};self.student={'id':3,'username':'franco','role':'estudiante'}
    def tearDown(self):self.tmp.cleanup()
    def test_calendar_fines(self):
        for due,actual,n in [('2026-11-06','2026-11-05',0),('2026-11-06','2026-11-06',0),('2026-11-06','2026-11-09',4500),('2026-12-31','2027-01-01',1500),('2026-01-31','2026-02-01',1500)]:
            with self.subTest(actual=actual):self.assertEqual(app.fine(due,actual),n)
    def test_return_atomic_and_idempotent(self):
        self.assertEqual(app.mutate(self.admin,'/api/return',{'id':1,'returned':'2026-11-09'})[0],200)
        app.mutate(self.admin,'/api/return',{'id':1,'returned':'2026-11-09'})
        with app.connect() as c:
            row=c.execute('SELECT * FROM loans WHERE id=1').fetchone();self.assertEqual(row['fine'],4500);self.assertEqual(c.execute("SELECT COUNT(*) FROM audit WHERE event='DEVOLUCION'").fetchone()[0],1);self.assertEqual(c.execute('SELECT COUNT(*) FROM notices').fetchone()[0],1)
        self.assertTrue(next(b for b in app.state(self.admin)['books'] if b['id']==1)['available'])
    def test_student_rejected_and_logged(self):
        self.assertEqual(app.mutate(self.student,'/api/return',{'id':1,'returned':'2026-11-09'})[0],403)
        with app.connect() as c:
            self.assertIsNone(c.execute('SELECT returned FROM loans WHERE id=1').fetchone()[0]); self.assertEqual(c.execute('SELECT event FROM audit').fetchone()[0],'ACCESO_RECHAZADO')
    def test_own_records_only(self):
        s=app.state(self.student);self.assertEqual(len(s['loans']),2);self.assertTrue(all(l['user_id']==3 for l in s['loans']));self.assertFalse(s['audit']);self.assertFalse(s['users'])
    def test_no_double_active_loan(self):
        with self.assertRaises(ValueError):app.mutate(self.admin,'/api/loan',{'book_id':1,'user_id':4,'start':'2026-11-09','due':'2026-11-16'})
    def test_reservation_priority_and_consumption(self):
        app.mutate(self.admin,'/api/reserve',{'book_id':4,'user_id':4})
        with self.assertRaises(ValueError):app.mutate(self.admin,'/api/loan',{'book_id':4,'user_id':3,'start':'2026-11-09','due':'2026-11-16'})
        app.mutate(self.admin,'/api/loan',{'book_id':4,'user_id':4,'start':'2026-11-09','due':'2026-11-16'})
        with app.connect() as c:self.assertEqual(c.execute('SELECT status FROM reservations').fetchone()[0],'Atendida')
    def test_invalid_dates(self):
        with self.assertRaises(ValueError):app.mutate(self.admin,'/api/return',{'id':1,'returned':'2026-10-31'})
    def test_duplicate_code_rolls_back(self):
        with self.assertRaises(app.sqlite3.IntegrityError):app.mutate(self.admin,'/api/book',{'title':'Otra','author':'Autor','code':'E001'})
        self.assertEqual(len(app.state(self.admin)['books']),6)
    def test_payment_keeps_fine_and_is_idempotent(self):
        app.mutate(self.admin,'/api/return',{'id':1,'returned':'2026-11-09'})
        app.mutate(self.admin,'/api/pay',{'id':1});app.mutate(self.admin,'/api/pay',{'id':1})
        loan=next(l for l in app.state(self.admin)['loans'] if l['id']==1)
        self.assertEqual(loan['fine'],4500);self.assertTrue(loan['paid_at']);self.assertEqual(loan['paid_by'],'Jorge')
        with app.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM payments').fetchone()[0],1)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM audit WHERE event='PAGO_DEMOSTRACION'").fetchone()[0],1)
    def test_student_cannot_record_payment(self):
        self.assertEqual(app.mutate(self.student,'/api/pay',{'id':3})[0],403)
        with app.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM payments').fetchone()[0],0)
    def test_cannot_pay_unreturned_loan(self):
        with self.assertRaises(ValueError):app.mutate(self.admin,'/api/pay',{'id':1})
    def test_rut_validation(self):
        self.assertEqual(app.normalize_rut('90.000.003-0'),'90000003-0')
        self.assertEqual(app.normalize_rut('900000030'),'90000003-0')
        for invalid in ('90000003-1','franco','90000003'):
            with self.assertRaises(ValueError):app.normalize_rut(invalid)
    def test_enrollment_roles_and_password(self):
        app.mutate(self.admin,'/api/user',{'roster_id':1,'rut':'90000005-7','role':'bibliotecario'})
        with app.connect() as c:
            u=c.execute("SELECT * FROM users WHERE rut='90000005-7'").fetchone()
            self.assertEqual(u['role'],'estudiante');self.assertEqual(u['hash'],app.password('90000005',u['salt']))
        self.assertEqual(app.mutate(self.student,'/api/user',{'roster_id':2,'rut':'90000006-5','role':'bibliotecario'})[0],403)
    def test_duplicate_rut_rejected(self):
        with self.assertRaises(app.sqlite3.IntegrityError):app.mutate(self.admin,'/api/user',{'roster_id':1,'rut':'90000003-0'})
    def test_restart_preserves_enrollment(self):
        app.mutate(self.admin,'/api/user',{'roster_id':1,'rut':'90000005-7'})
        app.init()
        with app.connect() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM users').fetchone()[0],5)
    def test_initial_only_jorge_and_pending_roster(self):
        self.assertEqual(len(self.seed['accounts']),1)
        self.assertEqual(self.seed['accounts'][0]['username'],'Jorge')
        self.assertEqual(len(self.seed['roster']),20)
        self.assertTrue(all(p['rut'] is None for p in self.seed['roster']))
        self.assertFalse(any('Giordano' in p['name'] for p in self.seed['roster']))
        self.assertFalse(self.seed['loans'])
    def test_unknown_roster_and_second_enrollment_rejected(self):
        with self.assertRaises(ValueError):app.mutate(self.admin,'/api/user',{'roster_id':999,'rut':'90000005-7'})
        app.mutate(self.admin,'/api/user',{'roster_id':1,'rut':'90000005-7'})
        with self.assertRaises(ValueError):app.mutate(self.admin,'/api/user',{'roster_id':1,'rut':'90000006-5'})
        with app.connect() as c:self.assertEqual(c.execute("SELECT COUNT(*) FROM users WHERE role='bibliotecario'").fetchone()[0],1)
    def test_removed_guide_and_public_credentials(self):
        html=(Path(__file__).parents[1]/'static/index.html').read_text(encoding='utf-8')
        self.assertNotIn('Guía de evaluación',html);self.assertNotIn('demo-access',html)
        self.assertNotIn('90000001',html)
    def test_previous_version_migration_preserves_history(self):
        with app.connect() as c:
            c.execute('DROP INDEX one_librarian')
            c.execute("UPDATE users SET username='profesor' WHERE id=1")
            c.execute("UPDATE users SET username='carolina',role='bibliotecario' WHERE id=2")
            c.execute("UPDATE users SET username='franco' WHERE id=3")
            c.execute("DELETE FROM settings WHERE key='jorge_roster_v1'")
        app.init()
        with app.connect() as c:
            self.assertEqual(c.execute("SELECT username FROM users WHERE role='bibliotecario'").fetchone()[0],'Jorge')
            self.assertEqual(c.execute('SELECT COUNT(*) FROM loans').fetchone()[0],3)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM users WHERE rut IS NOT NULL').fetchone()[0],1)
        app.mutate(self.admin,'/api/user',{'roster_id':5,'rut':'90000003-0'})
        with app.connect() as c:self.assertEqual(c.execute("SELECT id FROM users WHERE rut='90000003-0'").fetchone()[0],3)
    def test_full_http_login_permissions_return(self):
        server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
        op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        def req(path,d=None,token=''):
            r=urllib.request.Request(base+path,data=json.dumps(d).encode() if d is not None else None,headers={'Content-Type':'application/json','X-CSRF-Token':token})
            return json.load(op.open(r))
        try:
            with self.assertRaises(urllib.error.HTTPError) as err:req('/api/state')
            self.assertEqual(err.exception.code,401)
            with self.assertRaises(urllib.error.HTTPError):req('/api/login',{'rut':'90000001-4','password':'wrong'})
            token=req('/api/login',{'rut':'90.000.001-4','password':'90000001'})['csrf']
            self.assertEqual(req('/api/state')['user']['role'],'bibliotecario')
            with self.assertRaises(urllib.error.HTTPError) as err:req('/api/return',{'id':1,'returned':'2026-11-09'})
            self.assertEqual(err.exception.code,403)
            req('/api/return',{'id':1,'returned':'2026-11-09'},token)
            self.assertEqual(req('/api/state')['loans'][0]['fine'],4500)
            req('/api/logout',{},token)
            token=req('/api/login',{'rut':'90000003-0','password':'90000003'})['csrf']
            with self.assertRaises(urllib.error.HTTPError) as err:req('/api/return',{'id':2,'returned':'2026-11-09'},token)
            self.assertEqual(err.exception.code,403)
        finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
