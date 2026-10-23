import re
import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta, date
import calendar
import fleet
# Ticket sales reuse this server's authentication, SQLite connection and cash ledger.
import tickets
import notifications
import public_booking
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data.sqlite3'
SESSIONS = {}
FAILURES = {}
TZ = timezone(timedelta(hours=7))

def now():
    return datetime.now(TZ).isoformat(timespec='seconds')

def cash_range(period, anchor):
    if period=='month':
        start=date.fromisoformat(anchor+'-01')
        return start.isoformat(), start.replace(day=calendar.monthrange(start.year,start.month)[1]).isoformat()
    end=date.fromisoformat(anchor)
    if period not in ('today','fortnight'):
        raise ValueError('Khoảng thời gian không hợp lệ')
    return (end-timedelta(days=13 if period=='fortnight' else 0)).isoformat(),end.isoformat()

@contextmanager
def connect():
    conn = sqlite3.connect(DB, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 310000).hex()

def init_db():
    with connect() as c:
        c.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, salt TEXT NOT NULL, password TEXT NOT NULL, branch TEXT NOT NULL, role TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cargo(id INTEGER PRIMARY KEY, date TEXT NOT NULL, branch TEXT NOT NULL, receiver_phone TEXT NOT NULL, receiver_name TEXT NOT NULL, goods_description TEXT NOT NULL, quantity INTEGER NOT NULL CHECK(quantity>0), fee INTEGER NOT NULL CHECK(fee>=0), payment TEXT NOT NULL CHECK(payment IN ('paid','destination','debt')), collected_at TEXT, collected_branch TEXT, delivery_place TEXT NOT NULL, note TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'waiting' CHECK(status IN ('waiting','arrived','delivered')), created_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS cargo_date ON cargo(date,branch);
        CREATE INDEX IF NOT EXISTS cargo_phone ON cargo(receiver_phone);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, cargo_id INTEGER NOT NULL REFERENCES cargo(id), actor INTEGER NOT NULL REFERENCES users(id), action TEXT NOT NULL, before_json TEXT, after_json TEXT NOT NULL, at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cash_entries(id INTEGER PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('income','expense')), amount INTEGER NOT NULL CHECK(amount>=0), branch TEXT NOT NULL CHECK(branch IN ('SG','TK')), actor INTEGER NOT NULL REFERENCES users(id), note TEXT NOT NULL, at TEXT NOT NULL, cargo_id INTEGER UNIQUE REFERENCES cargo(id), request_id TEXT UNIQUE);
        CREATE INDEX IF NOT EXISTS cash_actor_date ON cash_entries(actor,at);
        ''')
        fleet.init_db(c)
        tickets.init_db(c)
        columns={r['name'] for r in c.execute('PRAGMA table_info(cargo)')}
        if 'scheduled_date' not in columns:
            c.execute('ALTER TABLE cargo ADD COLUMN scheduled_date TEXT')
        if 'vehicle' not in columns:
            c.execute("ALTER TABLE cargo ADD COLUMN vehicle TEXT NOT NULL DEFAULT ''")
        c.execute('UPDATE cargo SET scheduled_date=date WHERE scheduled_date IS NULL')
        c.execute('CREATE INDEX IF NOT EXISTS cargo_schedule ON cargo(scheduled_date,branch)')
        # Reconstruct only receipts with an identifiable actor in the existing audit.
        # UNIQUE cargo_id makes this migration safe to run again on every startup.
        c.execute('''INSERT OR IGNORE INTO cash_entries(kind,amount,branch,actor,note,at,cargo_id)
            SELECT 'income',g.fee,g.collected_branch,a.actor,'Thu cước đơn #' || g.id,g.collected_at,g.id
            FROM cargo g JOIN audit a ON a.cargo_id=g.id
            WHERE g.collected_at IS NOT NULL AND g.collected_branch IN ('SG','TK')
            AND (a.action='collect' OR (a.action='Nhận hàng' AND g.payment='paid'))
            ORDER BY a.id''')
        if not c.execute('SELECT 1 FROM users').fetchone():
            credentials = []
            for username, branch, role in [('admin','SG','admin'),('nhanvien_sg','SG','staff'),('nhanvien_tk','TK','staff')]:
                password, salt = secrets.token_urlsafe(12), secrets.token_hex(16)
                c.execute('INSERT INTO users(username,salt,password,branch,role) VALUES(?,?,?,?,?)', (username,salt,password_hash(password,salt),branch,role))
                credentials.append(f'{username}: {password}')
            (ROOT / 'TAI-KHOAN.txt').write_text('Tài khoản khởi tạo — giữ kín file này.\n'+'\n'.join(credentials), encoding='utf-8')
        public_booking.init_db(c)

class Handler(BaseHTTPRequestHandler):
    def send(self, status, data, content_type='application/json; charset=utf-8', headers=None):
        raw = json.dumps(data, ensure_ascii=False).encode() if content_type.startswith('application/json') else data
        self.send_response(status)
        for k,v in {'Content-Type':content_type,'Content-Length':str(len(raw)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Content-Security-Policy':"default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'", **(headers or {})}.items():
            self.send_header(k,v)
        self.end_headers()
        self.wfile.write(raw)

    def body(self):
        length = int(self.headers.get('Content-Length','0'))
        if length < 1 or length > 16384:
            raise ValueError('Nội dung yêu cầu không hợp lệ')
        data = json.loads(self.rfile.read(length))
        if not isinstance(data,dict):
            raise ValueError('Dữ liệu phải là một đối tượng')
        return data

    def user(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie',''))
            token = cookie['session'].value
        except Exception:
            return None
        session = SESSIONS.get(token)
        if not session or session['expires'] < time.time():
            SESSIONS.pop(token,None)
            return None
        return session

    def do_GET(self):
        from urllib.parse import urlsplit, parse_qs
        url = urlsplit(self.path)
        if url.path in ('/','/app.js','/style.css'):
            name = {'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[url.path]
            mime = {'index.html':'text/html; charset=utf-8','app.js':'text/javascript; charset=utf-8','style.css':'text/css; charset=utf-8'}[name]
            return self.send(200,(ROOT/'static'/name).read_bytes(),mime)
        if url.path == '/api/public/availability':
            q = parse_qs(url.query)
            try:
                with connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    result = tickets.availability(c, q.get('day', [now()[:10]])[0], q.get('origin', ['TK'])[0], now())
                token = public_booking.token_from_cookie(self.headers.get('Cookie')) or public_booking.create_token()
                result.update(csrf=token, email_ready=notifications.configured('email'))
                return self.send(200, result, headers={'Set-Cookie': f'booking_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=1800'})
            except (ValueError, TypeError):
                return self.send(400, {'error': 'Ngày hoặc điểm xuất phát không hợp lệ'})
        u = self.user()
        if not u:
            return self.send(401,{'error':'Vui lòng đăng nhập'})
        if url.path == '/api/me':
            return self.send(200,{'username':u['username'],'branch':u['branch'],'role':u['role'],'csrf':u['csrf'],'today':now()[:10]})
        if url.path == '/api/fleet':
            with connect() as c:
                c.execute('BEGIN')
                result = fleet.snapshot(c)
            return self.send(200, result)
        q = parse_qs(url.query)
        if url.path in ('/api/tickets', '/api/tickets/availability'):
            try:
                with connect() as c:
                    c.execute('BEGIN IMMEDIATE')
                    reader = tickets.availability if url.path.endswith('/availability') else tickets.listing
                    result = reader(c, q.get('day', [now()[:10]])[0], q.get('origin', [u['branch']])[0], now())
                    result['email_ready'] = notifications.configured('email')
                return self.send(200, result)
            except (ValueError, TypeError):
                return self.send(400, {'error': 'Ngày hoặc điểm xuất phát không hợp lệ'})
        branch = q.get('branch',[''])[0]
        if branch not in ('','SG','TK'):
            return self.send(400,{'error':'Chi nhánh không hợp lệ'})
        if url.path in ('/api/cash-today','/api/cash-report'):
            today=now()[:10]
            try:
                period=q.get('period',['today'])[0] if url.path=='/api/cash-report' else 'today'
                anchor=q.get('anchor',[today[:7] if period=='month' else today])[0] if url.path=='/api/cash-report' else today
                start,end=cash_range(period,anchor)
            except (ValueError,TypeError):
                return self.send(400,{'error':'Ngày hoặc khoảng thời gian không hợp lệ'})
            sql='FROM cash_entries e JOIN users u ON u.id=e.actor WHERE substr(e.at,1,10) BETWEEN ? AND ?'
            params=[start,end]
            if u['role']!='admin':
                sql+=' AND e.actor=?'; params.append(u['id'])
            elif branch:
                sql+=' AND e.branch=?'; params.append(branch)
            with connect() as c:
                totals=c.execute("SELECT COALESCE(SUM(CASE WHEN e.kind='income' THEN e.amount ELSE 0 END),0) AS income, COALESCE(SUM(CASE WHEN e.kind='expense' THEN e.amount ELSE 0 END),0) AS expense,COUNT(*) AS count "+sql,params).fetchone()
                entries=[dict(r) for r in c.execute('SELECT e.*,u.username '+sql+' ORDER BY e.id DESC LIMIT 100',params)]
            return self.send(200,{'date':today,'start':start,'end':end,'income':totals['income'],'expense':totals['expense'],'net':totals['income']-totals['expense'],'count':totals['count'],'entries':entries})
        if url.path == '/api/cargo':
            day, search = q.get('date',[''])[0], q.get('q',[''])[0].strip()[:100]
            sql, params = 'SELECT * FROM cargo WHERE 1=1', []
            flow = q.get('flow',['outbound'])[0]
            if flow not in ('outbound','inbound'):
                return self.send(400,{'error':'Chiều hàng không hợp lệ'})
            if branch:
                origin = branch if flow=='outbound' else ('TK' if branch=='SG' else 'SG')
                sql += ' AND branch=?'; params.append(origin)
            if day:
                sql += ' AND scheduled_date=?'; params.append(day)
            if search:
                sql += ' AND (instr(receiver_phone,?)>0 OR instr(lower(receiver_name),lower(?))>0 OR instr(lower(goods_description),lower(?))>0)'; params += [search]*3
            with connect() as c:
                rows = [dict(r) for r in c.execute(sql+' ORDER BY id DESC LIMIT 1001',params)]
            return self.send(200,{'rows':rows[:1000],'truncated':len(rows)>1000})
        if url.path == '/api/report' and u['role']=='admin':
            day = parse_qs(url.query).get('date',[now()[:10]])[0]
            with connect() as c:
                rows = [dict(r) for r in c.execute('SELECT * FROM cargo WHERE date=? AND (?=\'\' OR branch=?)',(day,branch,branch))]
                receipts = [dict(r) for r in c.execute('SELECT * FROM cargo WHERE substr(collected_at,1,10)=? AND (?=\'\' OR collected_branch=?)',(day,branch,branch))]
                audit = [dict(r) for r in c.execute('SELECT a.*,u.username FROM audit a JOIN users u ON u.id=a.actor JOIN cargo c ON c.id=a.cargo_id WHERE (?=\'\' OR c.branch=?) ORDER BY a.id DESC LIMIT 100',(branch,branch))]
            return self.send(200,{'count':len(rows),'total':sum(r['fee'] for r in rows),'collected':sum(r['fee'] for r in receipts),'destination':sum(r['fee'] for r in rows if r['payment']=='destination' and not r['collected_at']),'debt':sum(r['fee'] for r in rows if r['payment']=='debt' and not r['collected_at']),'audit':audit})
        if url.path == '/api/export' and u['role']=='admin':
            day = parse_qs(url.query).get('date',[now()[:10]])[0]
            out=io.StringIO(); writer=csv.writer(out); writer.writerow(['Ngày nhận','Chi nhánh','SĐT','Người nhận','Hàng','SL','Cước','Thanh toán','Nơi giao','Trạng thái','Ngày đi dự kiến','Xe'])
            with connect() as c:
                for r in c.execute('SELECT * FROM cargo WHERE date=? AND (?=\'\' OR branch=?) ORDER BY id',(day,branch,branch)):
                    values=[r[k] for k in ('date','branch','receiver_phone','receiver_name','goods_description','quantity','fee','payment','delivery_place','status','scheduled_date','vehicle')]
                    writer.writerow([("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r')) else v) for v in values])
            return self.send(200,('\ufeff'+out.getvalue()).encode(),'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="hang-gui.csv"'})
        self.send(404,{'error':'Không tìm thấy hoặc không có quyền'})

    def do_POST(self):
        try:
            self.post()
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:
            self.send(400,{'error':str(e) or 'Dữ liệu không hợp lệ'})
        except sqlite3.Error:
            self.send(500,{'error':'Không lưu được dữ liệu. Vui lòng thử lại.'})

    def post(self):
        d = self.body()
        if self.path == '/api/public/book':
            token = public_booking.token_from_cookie(self.headers.get('Cookie'))
            if not token or not hmac.compare_digest(token, self.headers.get('X-CSRF-Token', '')):
                return self.send(403, {'error': 'Phiên đặt vé hết hạn. Vui lòng tải lại trang.'})
            if d.get('paid') is not False or d.get('bus_id') is not None or d.get('contact_channel') not in ('email', 'sms'):
                return self.send(400, {'error': 'Khách đặt vé chưa thanh toán và cung cấp thông tin liên hệ.'})
            with connect() as c:
                permitted = public_booking.allow(c, self.client_address[0], d.get('phone') if d.get('contact_channel') == 'sms' else d.get('email'))
            if not permitted:
                return self.send(429, {'error': 'Bạn đã gửi nhiều yêu cầu. Vui lòng thử lại sau 30 phút hoặc liên hệ nhà xe.'})
            with connect() as c:
                user = dict(c.execute("SELECT * FROM users WHERE username='__web_booking__'").fetchone())
                user['branch'] = d.get('origin')
                result = tickets.sell(c, d, user, now())
            return self.send(200, result)
        if self.path == '/api/login':
            key=self.client_address[0]; attempts=[t for t in FAILURES.get(key,[]) if t>time.time()-300]
            if len(attempts)>=10:
                return self.send(429,{'error':'Thử lại sau 5 phút'})
            with connect() as c:
                row=c.execute('SELECT * FROM users WHERE username=?',(str(d.get('username',''))[:100],)).fetchone()
            if not row or row['role'] not in ('admin','staff') or not hmac.compare_digest(row['password'],password_hash(str(d.get('password',''))[:200],row['salt'])):
                FAILURES[key]=attempts+[time.time()]
                return self.send(401,{'error':'Sai tài khoản hoặc mật khẩu'})
            token=secrets.token_urlsafe(32)
            SESSIONS[token]={**dict(row),'csrf':secrets.token_urlsafe(32),'expires':time.time()+8*3600}
            return self.send(200,{'ok':True},headers={'Set-Cookie':f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'})
        u=self.user()
        if not u:
            return self.send(401,{'error':'Vui lòng đăng nhập'})
        if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),u['csrf']):
            return self.send(403,{'error':'Phiên thao tác không hợp lệ. Hãy tải lại trang.'})
        if self.path == '/api/logout':
            SESSIONS.pop(SimpleCookie(self.headers['Cookie'])['session'].value,None)
            return self.send(200,{'ok':True},headers={'Set-Cookie':'session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict'})
        if self.path == '/api/tickets/contact':
            if u['role'] != 'admin':
                return self.send(403, {'error': 'Chỉ quản lý được đổi số liên hệ'})
            phone = fleet.text(d, 'phone', 11)
            if not re.fullmatch(r'0[0-9]{8,10}', phone):
                raise ValueError('Số điện thoại phải có 9–11 chữ số, bắt đầu bằng 0')
            with connect() as c:
                c.execute("UPDATE business_settings SET value=? WHERE key='contact_phone'", (phone,))
            return self.send(200, {'ok': True})
        if self.path == '/api/tickets/retry-message':
            if u['role'] != 'admin':
                return self.send(403, {'error': 'Chỉ admin được gửi lại xác nhận'})
            with connect() as c:
                c.execute('BEGIN IMMEDIATE')
                row = c.execute('SELECT * FROM ticket_messages WHERE id=?', (tickets.ident(d.get('id')),)).fetchone()
                if not row or row['status'] not in ('failed','unknown','not_configured'):
                    raise ValueError('Thông báo không ở trạng thái có thể gửi lại')
                if row['status'] == 'unknown' and d.get('checked_provider') is not True:
                    raise ValueError('Kiểm tra dịch vụ chưa gửi thư trước khi thử lại')
                c.execute("UPDATE ticket_messages SET status='pending',error='',updated_at=? WHERE id=?", (now(), row['id']))
            return self.send(200, {'ok': True})
        if self.path in ('/api/tickets/config', '/api/tickets/day', '/api/tickets/book', '/api/tickets/collect', '/api/tickets/cancel', '/api/tickets/confirm-call'):
            kind = self.path.rsplit('/', 1)[-1]
            if kind in ('config', 'day', 'cancel') and u['role'] != 'admin':
                return self.send(403, {'error': 'Chỉ quản lý được chỉnh lịch, cho xe nghỉ hoặc hủy vé'})
            with connect() as c:
                if kind in ('config', 'day'):
                    result = tickets.admin_save(c, kind, d, u, now())
                elif kind == 'book':
                    result = tickets.sell(c, d, u, now())
                else:
                    result = tickets.action(c, kind, d, u, now())
            return self.send(200, result)
        if self.path in ('/api/fleet/employee', '/api/fleet/bus', '/api/fleet/crew'):
            if u['role'] != 'admin':
                return self.send(403, {'error': 'Chỉ quản lý được sửa xe và nhân viên'})
            with connect() as c:
                fleet.save(c, self.path.rsplit('/', 1)[-1], d, u['id'], now())
            return self.send(200, {'ok': True})
        with connect() as c:
            if self.path == '/api/expenses':
                amount=d.get('amount'); note=d.get('note'); request_id=d.get('request_id')
                if isinstance(amount,bool) or not isinstance(amount,int) or not 1<=amount<=100000000:
                    raise ValueError('Khoản chi phải là số nguyên từ 1 đến 100.000.000 đồng')
                if not isinstance(note,str) or not 1<=len(note.strip())<=200:
                    raise ValueError('Nhập lý do chi, tối đa 200 ký tự')
                if not isinstance(request_id,str) or not 16<=len(request_id)<=80:
                    raise ValueError('Mã yêu cầu không hợp lệ. Hãy tải lại trang.')
                expense_branch=d.get('branch') if u['role']=='admin' else u['branch']
                if expense_branch not in ('SG','TK'):
                    raise ValueError('Chọn chi nhánh ghi chi')
                c.execute('BEGIN IMMEDIATE')
                previous=c.execute('SELECT * FROM cash_entries WHERE request_id=?',(request_id,)).fetchone()
                if previous:
                    if (previous['actor'],previous['amount'],previous['note'],previous['branch'])!=(u['id'],amount,note.strip(),expense_branch):
                        raise ValueError('Mã yêu cầu đã dùng cho khoản chi khác')
                else:
                    c.execute("INSERT INTO cash_entries(kind,amount,branch,actor,note,at,request_id) VALUES('expense',?,?,?,?,?,?)",(amount,expense_branch,u['id'],note.strip(),now(),request_id))
            elif self.path == '/api/cargo':
                fields={}
                for name,limit in [('receiver_phone',15),('receiver_name',100),('goods_description',200),('delivery_place',150),('note',500)]:
                    value=d.get(name,'')
                    if not isinstance(value,str) or len(value.strip())>limit:
                        raise ValueError('Thông tin quá dài hoặc sai định dạng')
                    fields[name]=value.strip()
                if not fields['receiver_phone'].isdigit() or not 9<=len(fields['receiver_phone'])<=11:
                    raise ValueError('SĐT cần 9–11 chữ số')
                if any(not fields[k] for k in ('receiver_name','goods_description','delivery_place')):
                    raise ValueError('Vui lòng nhập tên, loại hàng và nơi giao')
                for name,low,high in [('quantity',1,10000),('fee',0,100000000)]:
                    value=d.get(name)
                    if isinstance(value,bool) or not isinstance(value,int) or not low<=value<=high:
                        raise ValueError('Số lượng hoặc cước không hợp lệ')
                    fields[name]=value
                if d.get('payment') not in ('paid','destination','debt'):
                    raise ValueError('Chọn cách thanh toán')
                origin = d.get('branch',u['branch']) if u['role']=='admin' else u['branch']
                if origin not in ('SG','TK'):
                    raise ValueError('Chọn chi nhánh nhận hàng: Sài Gòn hoặc Tam Kỳ')
                stamp=now(); fields.update(date=stamp[:10],branch=origin,payment=d['payment'],created_by=u['id'],created_at=stamp,updated_at=stamp,collected_at=stamp if d['payment']=='paid' else None,collected_branch=origin if d['payment']=='paid' else None)
                fields['scheduled_date']=stamp[:10]
                cur=c.execute(f"INSERT INTO cargo({','.join(fields)}) VALUES({','.join('?' for _ in fields)})",list(fields.values())); ident=cur.lastrowid
                c.execute('INSERT INTO audit(cargo_id,actor,action,after_json,at) VALUES(?,?,?,?,?)',(ident,u['id'],'Nhận hàng',json.dumps(fields,ensure_ascii=False),stamp))
                if d['payment']=='paid':
                    c.execute("INSERT INTO cash_entries(kind,amount,branch,actor,note,at,cargo_id) VALUES('income',?,?,?,?,?,?)",(fields['fee'],origin,u['id'],f'Thu cước đơn #{ident}',stamp,ident))
            elif self.path == '/api/action':
                c.execute('BEGIN IMMEDIATE')
                row=c.execute('SELECT * FROM cargo WHERE id=?',(d.get('id'),)).fetchone()
                if not row:
                    raise ValueError('Không tìm thấy đơn hàng')
                destination='TK' if row['branch']=='SG' else 'SG'
                action=d.get('action')
                allowed_branch=row['branch'] if action=='defer' else destination
                if u['role']!='admin' and u['branch']!=allowed_branch:
                    return self.send(403,{'error':'Chỉ chi nhánh nhận được cập nhật giao hàng / thu tiền'})
                stamp=now()
                if action=='defer':
                    if row['status']!='waiting':
                        raise ValueError('Chỉ chuyển ngày đối với hàng đang chờ đi')
                    if d.get('expected_date')!=row['scheduled_date']:
                        raise ValueError('Ngày đi đã thay đổi. Tải lại danh sách trước khi chuyển tiếp.')
                    vehicle=d.get('vehicle','')
                    if not isinstance(vehicle,str) or not 1<=len(vehicle.strip())<=80:
                        raise ValueError('Nhập tên hoặc biển số xe nhận thay, tối đa 80 ký tự')
                    next_day=(date.fromisoformat(row['scheduled_date'])+timedelta(days=1)).isoformat()
                    c.execute('UPDATE cargo SET scheduled_date=?,vehicle=?,updated_at=? WHERE id=?',(next_day,vehicle.strip(),stamp,row['id']))
                elif action=='collect':
                    if row['collected_at']:
                        raise ValueError('Đơn này đã thu tiền')
                    c.execute('UPDATE cargo SET collected_at=?,collected_branch=?,updated_at=? WHERE id=?',(stamp,destination,stamp,row['id']))
                    c.execute("INSERT INTO cash_entries(kind,amount,branch,actor,note,at,cargo_id) VALUES('income',?,?,?,?,?,?)",(row['fee'],destination,u['id'],f'Thu cước đơn #{row["id"]}',stamp,row['id']))
                elif action in ('arrived','delivered'):
                    expected='waiting' if action=='arrived' else 'arrived'
                    if row['status']!=expected:
                        raise ValueError('Trạng thái đã thay đổi. Hãy tải lại danh sách.')
                    if action=='delivered' and not row['collected_at'] and row['payment']=='destination':
                        raise ValueError('Cần xác nhận thu tiền trước khi giao')
                    c.execute('UPDATE cargo SET status=?,updated_at=? WHERE id=?',(action,stamp,row['id']))
                else:
                    raise ValueError('Thao tác không hợp lệ')
                after=dict(c.execute('SELECT * FROM cargo WHERE id=?',(row['id'],)).fetchone())
                c.execute('INSERT INTO audit(cargo_id,actor,action,before_json,after_json,at) VALUES(?,?,?,?,?,?)',(row['id'],u['id'],action,json.dumps(dict(row),ensure_ascii=False),json.dumps(after,ensure_ascii=False),stamp))
            else:
                return self.send(404,{'error':'Không tìm thấy'})
        self.send(200,{'ok':True})

if __name__=='__main__':
    init_db()
    notifications.start_worker(connect, now, tickets.expire)
    port = int(os.environ.get('PORT','8765'))
    print(f'Nha xe: http://127.0.0.1:{port} | Accounts: TAI-KHOAN.txt',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
