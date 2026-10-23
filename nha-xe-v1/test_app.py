import http.client
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import app

class WorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); app.ROOT=Path(cls.tmp.name); app.DB=app.ROOT/'test.sqlite3'; app.init_db()
        cls.passwords=dict(line.split(': ',1) for line in (app.ROOT/'TAI-KHOAN.txt').read_text(encoding='utf-8').splitlines()[1:])
        cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.tmp.cleanup()
    def setUp(self):
        with app.connect() as c:
            c.execute('DELETE FROM bus_crew')
            c.execute('DELETE FROM fleet_audit')
            c.execute('DELETE FROM employees')
            for i in range(1,4):
                c.execute('UPDATE buses SET name=?,phone=?,plate=?,version=1 WHERE id=?', (f'Xe {i}',f'086861231{i}','',i))
            c.execute('DELETE FROM cash_entries')
            c.execute('DELETE FROM audit')
            c.execute('DELETE FROM cargo')
    def request(self,path,data=None,auth=None,csrf=True):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        headers={}
        if auth:
            headers['Cookie']=auth[0]
            if csrf: headers['X-CSRF-Token']=auth[1]
        if data is not None: headers['Content-Type']='application/json'
        c.request('POST' if data is not None else 'GET',path,json.dumps(data) if data is not None else None,headers)
        r=c.getresponse(); body=r.read(); result=(r.status,json.loads(body) if r.getheader('Content-Type','').startswith('application/json') else body.decode('utf-8-sig'),r.getheader('Set-Cookie')); c.close(); return result
    def login(self,name):
        s,d,cookie=self.request('/api/login',{'username':name,'password':self.passwords[name]}); self.assertEqual(s,200)
        auth=(cookie.split(';')[0],''); s,d,_=self.request('/api/me',auth=auth); return (auth[0],d['csrf'])

    def fleet_people(self, auth):
        for i in range(12):
            self.assertEqual(self.request('/api/fleet/employee', {
                'name':f'Nhân viên thử {i}', 'phone':f'09000000{i:02d}',
                'role':'driver' if i%4<2 else 'assistant', 'active':True},auth)[0],200)
        return self.request('/api/fleet',auth=auth)[1]

    def test_fleet_seed_permissions_and_edit(self):
        self.assertEqual(self.request('/api/fleet')[0],401)
        admin,staff=self.login('admin'),self.login('nhanvien_sg')
        data=self.request('/api/fleet',auth=staff)[1]
        self.assertEqual([b['phone'] for b in data['buses']],['0868612311','0868612312','0868612313'])
        self.assertEqual(data['employees'],[])
        bus={**data['buses'][0], 'name':'Xe Sài Gòn', 'phone':'0868612399','plate':'92B-12345'}
        for path,payload in [('bus',bus),('employee',{}),('crew',{})]:
            self.assertEqual(self.request('/api/fleet/'+path,payload,staff)[0],403)
        self.assertEqual(self.request('/api/fleet/bus',bus,admin,csrf=False)[0],403)
        self.assertEqual(self.request('/api/fleet/bus',bus,admin)[0],200)
        self.assertEqual(self.request('/api/fleet/bus',bus,admin)[0],400)  # Stale version.
        app.init_db()
        newer=self.request('/api/fleet',auth=admin)[1]
        self.assertEqual(len(newer['buses']),3)
        self.assertEqual(newer['buses'][0]['phone'],'0868612399')
        self.assertEqual(newer['buses'][0]['plate'],'92B-12345')
        second={**newer['buses'][1], 'phone':'0868612399'}
        self.assertEqual(self.request('/api/fleet/bus',second,admin)[0],400)

    def test_fleet_three_complete_crews_and_employee_guards(self):
        admin=self.login('admin'); data=self.fleet_people(admin)
        for i,bus in enumerate(data['buses']):
            crew=dict(zip(app.fleet.SLOTS,range(i*4+1,i*4+5)))
            self.assertEqual(self.request('/api/fleet/crew',{**bus,'crew':crew},admin)[0],200)
        data=self.request('/api/fleet',auth=admin)[1]
        self.assertEqual(sum(len(b['crew']) for b in data['buses']),12)
        person=next(e for e in data['employees'] if e['id']==1)
        for update in ({'active':False},{'role':'assistant','active':True}):
            self.assertEqual(self.request('/api/fleet/employee',{**person,**update},admin)[0],400)
        self.assertEqual(self.request('/api/fleet/employee',{**person,'active':True,'name':'Tên sửa'},admin)[0],200)
        self.assertEqual(self.request('/api/fleet/employee',{**person,'active':True},admin)[0],400)
        self.assertEqual(self.request('/api/fleet/crew',{**data['buses'][0],'crew':{}},admin)[0],200)
        person=next(e for e in self.request('/api/fleet',auth=admin)[1]['employees'] if e['id']==1)
        self.assertEqual(self.request('/api/fleet/employee',{**person,'active':False},admin)[0],200)
        with app.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM fleet_audit').fetchone()[0],18)

    def test_fleet_invalid_roster_rolls_back(self):
        admin=self.login('admin'); data=self.fleet_people(admin); bus=data['buses'][0]
        correct=dict(zip(app.fleet.SLOTS,[1,2,3,4]))
        self.assertEqual(self.request('/api/fleet/crew',{**bus,'crew':correct},admin)[0],200)
        bus=self.request('/api/fleet',auth=admin)[1]['buses'][0]
        for crew in ({'driver1':1}, {**correct,'driver2':1}, {**correct,'driver1':3,'assistant1':1},
                     {**correct,'assistant2':999}, {**correct,'driver1':True}, []):
            self.assertEqual(self.request('/api/fleet/crew',{**bus,'crew':crew},admin)[0],400)
            self.assertEqual(self.request('/api/fleet',auth=admin)[1]['buses'][0],bus)
        person=next(e for e in data['employees'] if e['id']==5)
        self.assertEqual(self.request('/api/fleet/employee',{**person,'active':False},admin)[0],200)
        self.assertEqual(self.request('/api/fleet/crew',{**bus,'crew':{**correct,'driver1':5}},admin)[0],400)

    def test_fleet_concurrent_assignment_has_one_winner(self):
        admin=self.login('admin'); data=self.fleet_people(admin)
        gate=threading.Barrier(2,timeout=10)
        def assign(bus):
            gate.wait()
            return self.request('/api/fleet/crew',{**bus,'crew':dict(zip(app.fleet.SLOTS,[1,2,3,4]))},admin)[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(assign,bus) for bus in data['buses'][:2]]
            self.assertEqual(sorted(job.result(timeout=20) for job in jobs),[200,400])
        result=self.request('/api/fleet',auth=admin)[1]
        self.assertEqual(sorted(len(bus['crew']) for bus in result['buses']),[0,0,4])
        with app.connect() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM fleet_audit WHERE action='crew'").fetchone()[0],1)

    def test_admin_and_staff_create_different_orders_concurrently(self):
        admin,staff=self.login('admin'),self.login('nhanvien_sg')
        expected={}
        # Each pair starts together using independent HTTP connections and cookies.
        # Alternate same-branch and opposite-branch orders, with all payment modes.
        with ThreadPoolExecutor(max_workers=2) as pool:
            for round_number in range(30):
                gate=threading.Barrier(2,timeout=10)
                jobs=[]
                for role,auth in [('admin',admin),('nhanvien_sg',staff)]:
                    name=f'Concurrent-{round_number}-{role}'
                    payment=('paid','destination','debt')[round_number%3]
                    branch='TK' if role=='admin' and round_number%2 else 'SG'
                    data={'receiver_phone':f'090{round_number:06d}{0 if role=="admin" else 1}',
                          'receiver_name':name,'goods_description':f'Box {role}',
                          'quantity':round_number+1,'fee':10000+round_number*100+(1 if role=='admin' else 2),
                          'payment':payment,'delivery_place':'Test office','note':name,'branch':branch}
                    expected[name]=(data,role)
                    def send_together(payload=data,session=auth,barrier=gate):
                        barrier.wait()
                        return self.request('/api/cargo',payload,session)
                    jobs.append(pool.submit(send_together))
                for job in jobs:
                    status,result,_=job.result(timeout=20)
                    self.assertEqual((status,result),(200,{'ok':True}))
        status,listing,_=self.request('/api/cargo',auth=admin)
        self.assertEqual(status,200)
        self.assertEqual(len(listing['rows']),60)
        self.assertEqual(len({r['id'] for r in listing['rows']}),60)
        with app.connect() as c:
            users={r['id']:r['username'] for r in c.execute('SELECT id,username FROM users')}
            for row in listing['rows']:
                data,role=expected[row['receiver_name']]
                for field in data:
                    self.assertEqual(row[field],data[field],(row['id'],field))
                self.assertEqual(users[row['created_by']],role)
                audits=c.execute('SELECT * FROM audit WHERE cargo_id=?',(row['id'],)).fetchall()
                self.assertEqual(len(audits),1)
                self.assertEqual(users[audits[0]['actor']],role)
                snapshot=json.loads(audits[0]['after_json'])
                self.assertEqual(snapshot['receiver_name'],row['receiver_name'])
                self.assertEqual(snapshot['fee'],row['fee'])
                receipts=c.execute('SELECT * FROM cash_entries WHERE cargo_id=?',(row['id'],)).fetchall()
                self.assertEqual(len(receipts),1 if row['payment']=='paid' else 0)
                if receipts:
                    self.assertEqual((receipts[0]['amount'],users[receipts[0]['actor']],receipts[0]['branch']),
                                     (row['fee'],role,row['branch']))
            self.assertEqual(c.execute('SELECT COUNT(*) FROM audit').fetchone()[0],60)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM cash_entries').fetchone()[0],20)
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
        total=sum(data['fee'] for data,_ in expected.values() if data['payment']=='paid')
        own=sum(data['fee'] for data,role in expected.values() if data['payment']=='paid' and role=='nhanvien_sg')
        _,summary,_=self.request('/api/cash-today',auth=admin)
        _,personal,_=self.request('/api/cash-today',auth=staff)
        self.assertEqual(summary['income'],total)
        self.assertEqual(personal['income'],own)
    def test_end_to_end(self):
        self.assertEqual(self.request('/api/cargo')[0],401)
        sg,tk,admin=self.login('nhanvien_sg'),self.login('nhanvien_tk'),self.login('admin')
        record={'receiver_phone':'0901234567','receiver_name':'Khách thử','goods_description':'Xọt + bao','quantity':2,'fee':150000,'payment':'destination','delivery_place':'Tam Kỳ','note':'<script>alert(1)</script>','branch':'TK'}
        self.assertEqual(self.request('/api/cargo',record,sg,False)[0],403)
        self.assertEqual(self.request('/api/cargo',{**record,'fee':-1},sg)[0],400)
        self.assertEqual(self.request('/api/cargo',record,sg)[0],200)
        s,d,_=self.request('/api/cargo?q=0901234567',auth=tk); self.assertEqual(len(d['rows']),1)
        row=d['rows'][0]; self.assertEqual(row['branch'],'SG'); ident=row['id']
        self.assertEqual(self.request('/api/report',auth=sg)[0],404)
        self.assertEqual(self.request('/api/action',{'id':ident,'action':'arrived'},sg)[0],403)
        self.assertEqual(self.request('/api/action',{'id':ident,'action':'arrived'},tk)[0],200)
        self.assertEqual(self.request('/api/action',{'id':ident,'action':'delivered'},tk)[0],400)
        self.assertEqual(self.request('/api/action',{'id':ident,'action':'collect'},tk)[0],200)
        self.assertEqual(self.request('/api/action',{'id':ident,'action':'collect'},tk)[0],400)
        self.assertEqual(self.request('/api/action',{'id':ident,'action':'delivered'},tk)[0],200)
        self.assertEqual(self.request('/api/action',{'id':ident,'action':'arrived'},tk)[0],400)
        s,d,_=self.request('/api/report',auth=admin); self.assertEqual(d['total'],150000); self.assertEqual(d['collected'],150000); self.assertEqual(d['destination'],0); self.assertEqual(len(d['audit']),4)
        self.assertEqual(self.request('/api/logout',{},sg)[0],200)
        self.assertEqual(self.request('/api/cargo',auth=sg)[0],401)

    def test_defer_preserves_receipt_and_moves_manifest(self):
        sg,tk,admin=self.login('nhanvien_sg'),self.login('nhanvien_tk'),self.login('admin')
        record={'receiver_phone':'0903333333','receiver_name':'Overflow','goods_description':'Box','quantity':5,'fee':100000,'payment':'paid','delivery_place':'TK','note':''}
        with patch('app.now',return_value='2026-12-31T18:00:00+07:00'):
            self.assertEqual(self.request('/api/cargo',record,sg)[0],200)
        _,listing,_=self.request('/api/cargo?date=2026-12-31',auth=sg)
        row=listing['rows'][0]
        payload={'id':row['id'],'action':'defer','expected_date':'2026-12-31','vehicle':'Xe B'}
        self.assertEqual(self.request('/api/action',payload,tk)[0],403)
        self.assertEqual(self.request('/api/action',{**payload,'vehicle':''},sg)[0],400)
        self.assertEqual(self.request('/api/action',payload,sg)[0],200)
        self.assertEqual(self.request('/api/action',payload,sg)[0],400)
        _,old,_=self.request('/api/cargo?date=2026-12-31',auth=sg)
        _,new,_=self.request('/api/cargo?date=2027-01-01',auth=sg)
        self.assertEqual(old['rows'],[])
        moved=new['rows'][0]
        self.assertEqual((moved['id'],moved['date'],moved['vehicle']),(row['id'],'2026-12-31','Xe B'))
        self.assertEqual(moved['collected_at'],row['collected_at'])
        with app.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM cash_entries').fetchone()[0],1)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM audit WHERE action='defer'").fetchone()[0],1)
        app.init_db(); app.init_db()
        _,listing,_=self.request('/api/cargo?date=2027-01-01',auth=sg)
        self.assertEqual(len(listing['rows']),1)
        self.assertEqual(self.request('/api/action',{'id':row['id'],'action':'arrived'},tk)[0],200)
        self.assertEqual(self.request('/api/action',{**payload,'expected_date':'2027-01-01'},admin)[0],400)

    def test_cash_periods_and_permissions(self):
        sg,admin=self.login('nhanvien_sg'),self.login('admin')
        with app.connect() as c:
            actors={r['username']:r['id'] for r in c.execute('SELECT id,username FROM users')}
            for day,kind,amount,user,branch in [('2026-10-08','income',100,'nhanvien_sg','SG'),('2026-10-09','income',200,'nhanvien_sg','SG'),('2026-10-22','expense',50,'nhanvien_sg','SG'),('2026-10-23','income',400,'nhanvien_sg','SG'),('2026-10-31','income',800,'nhanvien_tk','TK'),('2026-11-01','income',1600,'nhanvien_sg','SG')]:
                c.execute('INSERT INTO cash_entries(kind,amount,branch,actor,note,at) VALUES(?,?,?,?,?,?)',(kind,amount,branch,actors[user],'Test',day+'T23:59:59+07:00'))
        _,fortnight,_=self.request('/api/cash-report?period=fortnight&anchor=2026-10-22&branch=TK',auth=sg)
        self.assertEqual((fortnight['start'],fortnight['end'],fortnight['income'],fortnight['expense']),('2026-10-09','2026-10-22',200,50))
        _,month,_=self.request('/api/cash-report?period=month&anchor=2026-10',auth=sg)
        self.assertEqual((month['income'],month['expense']),(700,50))
        _,all_month,_=self.request('/api/cash-report?period=month&anchor=2026-10',auth=admin)
        self.assertEqual(all_month['income'],1500)
        _,tk_month,_=self.request('/api/cash-report?period=month&anchor=2026-10&branch=TK',auth=admin)
        self.assertEqual(tk_month['income'],800)
        self.assertEqual(app.cash_range('month','2028-02'),('2028-02-01','2028-02-29'))
        self.assertEqual(app.cash_range('fortnight','2027-01-05'),('2026-12-23','2027-01-05'))
        for query in ['period=month&anchor=bad','period=fortnight&anchor=2026-02-30','period=bad','period=month&anchor=2026-13']:
            self.assertEqual(self.request('/api/cash-report?'+query,auth=sg)[0],400)

    def test_personal_daily_cash(self):
        sg,tk,admin=self.login('nhanvien_sg'),self.login('nhanvien_tk'),self.login('admin')
        self.assertEqual(self.request('/api/cash-today')[0],401)
        record={'receiver_phone':'0902222222','receiver_name':'Cash test','goods_description':'Box','quantity':1,'fee':100000,'payment':'paid','delivery_place':'TK','note':''}
        self.assertEqual(self.request('/api/cargo',record,sg)[0],200)
        self.assertEqual(self.request('/api/cargo',{**record,'fee':50000,'payment':'destination'},sg)[0],200)
        _,rows,_=self.request('/api/cargo',auth=sg)
        ident=next(r['id'] for r in rows['rows'] if r['payment']=='destination')
        self.assertEqual(self.request('/api/action',{'id':ident,'action':'collect'},tk)[0],200)
        expense={'amount':20000,'note':'Boc xep','branch':'TK','actor':999,'request_id':'cash-test-expense-0001'}
        self.assertEqual(self.request('/api/expenses',expense,sg,False)[0],403)
        self.assertEqual(self.request('/api/expenses',{**expense,'amount':-1},sg)[0],400)
        self.assertEqual(self.request('/api/expenses',expense,sg)[0],200)
        self.assertEqual(self.request('/api/expenses',expense,sg)[0],200)
        self.assertEqual(self.request('/api/expenses',{**expense,'amount':30000},sg)[0],400)
        _,mine,_=self.request('/api/cash-today?branch=TK&actor=999',auth=sg)
        self.assertEqual((mine['income'],mine['expense'],mine['net'],mine['count']),(100000,20000,80000,2))
        self.assertTrue(all(e['username']=='nhanvien_sg' and e['branch']=='SG' for e in mine['entries']))
        _,other,_=self.request('/api/cash-today',auth=tk)
        self.assertEqual((other['income'],other['expense']),(50000,0))
        _,total,_=self.request('/api/cash-today',auth=admin)
        self.assertEqual((total['income'],total['expense']),(150000,20000))
        _,tk_total,_=self.request('/api/cash-today?branch=TK',auth=admin)
        self.assertEqual((tk_total['income'],tk_total['expense']),(50000,0))
        # Simulate old data without the new ledger, and rerun the migration twice.
        with app.connect() as c:
            c.execute("DELETE FROM cash_entries WHERE kind='income'")
        app.init_db(); app.init_db()
        _,rebuilt,_=self.request('/api/cash-today',auth=admin)
        self.assertEqual((rebuilt['income'],rebuilt['expense'],rebuilt['count']),(150000,20000,3))
        with app.connect() as c:
            c.execute("UPDATE cash_entries SET at='2020-01-01T12:00:00+07:00' WHERE kind='expense'")
        _,today,_=self.request('/api/cash-today',auth=sg)
        self.assertEqual(today['expense'],0)

    def test_admin_two_branches(self):
        admin=self.login('admin')
        record={'receiver_phone':'0901111111','receiver_name':'Test','goods_description':'Box','quantity':1,'fee':10000,'payment':'paid','delivery_place':'Office','note':''}
        for branch,fee,payment in [('SG',10000,'paid'),('TK',20000,'paid'),('SG',30000,'destination')]:
            self.assertEqual(self.request('/api/cargo',{**record,'branch':branch,'fee':fee,'payment':payment},admin)[0],200)
        self.assertEqual(self.request('/api/cargo',{**record,'branch':''},admin)[0],400)
        self.assertEqual(self.request('/api/cargo',{**record,'branch':'BAD'},admin)[0],400)
        _,sg,_=self.request('/api/cargo?branch=SG',auth=admin)
        _,tk,_=self.request('/api/cargo?branch=TK',auth=admin)
        _,incoming,_=self.request('/api/cargo?branch=TK&flow=inbound',auth=admin)
        self.assertEqual(len(sg['rows']),2); self.assertEqual(len(tk['rows']),1)
        self.assertEqual([r['id'] for r in sg['rows']],[r['id'] for r in incoming['rows']])
        self.assertEqual(tk['rows'][0]['collected_branch'],'TK')
        pending=next(r for r in sg['rows'] if r['payment']=='destination')
        self.assertEqual(self.request('/api/action',{'id':pending['id'],'action':'collect'},admin)[0],200)
        _,sg_report,_=self.request('/api/report?branch=SG',auth=admin)
        _,tk_report,_=self.request('/api/report?branch=TK',auth=admin)
        _,all_report,_=self.request('/api/report',auth=admin)
        self.assertEqual(sg_report['total'],40000); self.assertEqual(sg_report['collected'],10000)
        self.assertEqual(tk_report['total'],20000); self.assertEqual(tk_report['collected'],50000)
        self.assertEqual(all_report['collected'],60000)
        self.assertTrue(all(json.loads(a['after_json'])['branch']=='TK' for a in tk_report['audit']))
        status,csv_text,_=self.request('/api/export?branch=TK',auth=admin)
        self.assertEqual(status,200); self.assertIn(',TK,',csv_text); self.assertNotIn(',SG,',csv_text)
        for path in ['/api/cargo?branch=BAD','/api/report?branch=BAD','/api/export?branch=BAD','/api/cargo?flow=BAD']:
            self.assertEqual(self.request(path,auth=admin)[0],400)

if __name__=='__main__': unittest.main()
