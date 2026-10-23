"""Bán nguyên khoang theo ngày, chiều chạy; giá và chống trùng do server quyết định."""
import json
import re
from datetime import date, datetime, timedelta
import fleet
import ticket_routes
import notifications

PRICES = {1: 800000, 2: 1200000}
DEFAULT_CABINS = [f'{floor}{side}{row}' for floor in (1, 2) for row in range(1, 7) for side in ('A', 'B')]


def init_db(c):
    c.executescript('''
        CREATE TABLE IF NOT EXISTS bus_sales(
            bus_id INTEGER PRIMARY KEY REFERENCES buses(id),
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
            tk_parity TEXT NOT NULL CHECK(tk_parity IN ('even','odd','none')),
            cabins_json TEXT NOT NULL DEFAULT '[]');
        CREATE TABLE IF NOT EXISTS bus_days(
            bus_id INTEGER NOT NULL REFERENCES buses(id), day TEXT NOT NULL,
            origin TEXT NOT NULL CHECK(origin IN ('TK','SG','OFF')), PRIMARY KEY(bus_id,day));
        CREATE TABLE IF NOT EXISTS tickets(
            id INTEGER PRIMARY KEY, bus_id INTEGER NOT NULL REFERENCES buses(id),
            day TEXT NOT NULL, origin TEXT NOT NULL CHECK(origin IN ('TK','SG')),
            cabin TEXT NOT NULL, passengers INTEGER NOT NULL CHECK(passengers IN (1,2)),
            price INTEGER NOT NULL CHECK(price IN (800000,1200000)),
            name TEXT NOT NULL, phone TEXT NOT NULL,
            created_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL,
            paid_at TEXT, cancelled_at TEXT, cancel_reason TEXT,
            request_id TEXT UNIQUE NOT NULL, request_json TEXT NOT NULL);
        CREATE UNIQUE INDEX IF NOT EXISTS one_ticket_per_cabin ON tickets(bus_id,day,cabin) WHERE cancelled_at IS NULL;
        CREATE INDEX IF NOT EXISTS ticket_day ON tickets(day,origin);
        CREATE TABLE IF NOT EXISTS ticket_audit(
            id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            actor INTEGER NOT NULL REFERENCES users(id), action TEXT NOT NULL, at TEXT NOT NULL);
    ''')
    columns = {r['name'] for r in c.execute('PRAGMA table_info(cash_entries)')}
    if 'ticket_id' not in columns:
        c.execute('ALTER TABLE cash_entries ADD COLUMN ticket_id INTEGER REFERENCES tickets(id)')
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS ticket_cash_once ON cash_entries(ticket_id,kind) WHERE ticket_id IS NOT NULL')
    ticket_columns = {r['name'] for r in c.execute('PRAGMA table_info(tickets)')}
    for column in ('pickup_json', 'dropoff_json', 'note', 'email', 'hold_until', 'confirmed_at'):
        if column not in ticket_columns:
            c.execute(f"ALTER TABLE tickets ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
    if 'contact_channel' not in ticket_columns:
        c.execute("ALTER TABLE tickets ADD COLUMN contact_channel TEXT NOT NULL DEFAULT 'sms'")
    notifications.init_db(c)
    for bus in c.execute('SELECT id FROM buses').fetchall():
        parity = {1: 'even', 2: 'odd'}.get(bus['id'], 'none')
        c.execute('INSERT OR IGNORE INTO bus_sales(bus_id,tk_parity,cabins_json) VALUES(?,?,?)', (bus['id'], parity, json.dumps(DEFAULT_CABINS)))
    # Upgrade the initially empty layout after the owner confirmed 24 cabins.
    # A marker preserves later intentional empty/custom layouts on restart.
    if not c.execute("SELECT 1 FROM fleet_migrations WHERE name='confirmed-24-cabins'").fetchone():
        c.execute("UPDATE bus_sales SET cabins_json=? WHERE cabins_json='[]'", (json.dumps(DEFAULT_CABINS),))
        c.execute("INSERT INTO fleet_migrations VALUES('confirmed-24-cabins')")


def valid_day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Chọn ngày hợp lệ')
    parsed = date.fromisoformat(value)
    if parsed == date.max:
        raise ValueError('Ngày quá xa để tính ngày trả khách')
    return parsed.isoformat()


def ident(value):
    if type(value) is not int or not 1 <= value <= 2**63-1:
        raise ValueError('Mã không hợp lệ')
    return value


def route(parity, day):
    if parity == 'none':
        return 'OFF'
    from_tk = (date.fromisoformat(day).day % 2 == 0) == (parity == 'even')
    return 'TK' if from_tk else 'SG'


def settings(c, bus_id):
    row = c.execute('SELECT b.*,s.active,s.tk_parity,s.cabins_json FROM buses b JOIN bus_sales s ON s.bus_id=b.id WHERE b.id=?', (bus_id,)).fetchone()
    if not row:
        raise ValueError('Không tìm thấy xe')
    result = dict(row)
    result['cabins'] = json.loads(result.pop('cabins_json'))
    return result


def direction(c, bus, day):
    override = c.execute('SELECT origin FROM bus_days WHERE bus_id=? AND day=?', (bus['id'], day)).fetchone()
    return override['origin'] if override else route(bus['tk_parity'], day)


def listing(c, day, origin, stamp):
    day = valid_day(day)
    if origin not in ('TK', 'SG'):
        raise ValueError('Chọn điểm xuất phát')
    expire(c, stamp)
    buses = []
    for row in c.execute('SELECT id FROM buses ORDER BY id').fetchall():
        bus = settings(c, row['id'])
        bus['direction'] = direction(c, bus, day)
        override = c.execute('SELECT origin FROM bus_days WHERE bus_id=? AND day=?', (bus['id'], day)).fetchone()
        bus['override'] = override['origin'] if override else 'auto'
        bus['tickets'] = [dict(t) for t in c.execute('''SELECT id,bus_id,day,origin,cabin,passengers,price,name,phone,
            created_by,created_at,paid_at,cancelled_at,cancel_reason,pickup_json,dropoff_json,note,email,contact_channel,confirmed_at FROM tickets WHERE bus_id=? AND day=? AND origin=? ORDER BY id DESC''', (bus['id'], day, origin))]
        for ticket in bus['tickets']:
            ticket['messages'] = [dict(row) for row in c.execute('SELECT id,event,channel,status,error,body FROM ticket_messages WHERE ticket_id=? ORDER BY id', (ticket['id'],))]
            for kind in ('pickup', 'dropoff'):
                raw = ticket.pop(kind+'_json')
                ticket[kind] = json.loads(raw) if raw else None
        bus['occupied'] = [r['cabin'] for r in c.execute('SELECT cabin FROM tickets WHERE bus_id=? AND day=? AND cancelled_at IS NULL', (bus['id'], day))]
        bus['can_sell'] = bool(bus['active'] and bus['direction'] == origin and bus['cabins'] and day >= stamp[:10])
        buses.append(bus)
    return {'day': day, 'origin': origin, 'buses': buses, 'prices': PRICES, 'updated_at': stamp, 'contact_phone': notifications.contact_phone(c), **ticket_routes.options(origin, day)}


def expire(c, stamp):
    rows = c.execute("SELECT id FROM tickets WHERE hold_until!='' AND hold_until<=? AND paid_at IS NULL AND cancelled_at IS NULL", (stamp,)).fetchall()
    for row in rows:
        c.execute("UPDATE tickets SET cancelled_at=?,cancel_reason='Hết thời gian giữ chỗ trực tuyến' WHERE id=?", (stamp, row['id']))
        notifications.enqueue(c, row['id'], 'cancel', stamp)


def availability(c, day, origin, stamp):
    result = listing(c, day, origin, stamp)
    cabins = {}
    for bus in result['buses']:
        if not bus['can_sell']: continue
        for label in bus['cabins']:
            cabins.setdefault(label, 0)
            if label not in bus['occupied']: cabins[label] += 1
    return {key: result[key] for key in ('day', 'origin', 'prices', 'updated_at', 'pickups', 'dropoffs')} | {
        'cabins': [{'label': label, 'remaining': count} for label, count in cabins.items()]}


def admin_save(c, kind, d, user, stamp):
    c.execute('BEGIN IMMEDIATE')
    before = fleet.existing(c, 'buses', d)
    bus = settings(c, before['id'])
    if kind == 'config':
        active, parity, cabins = d.get('active'), d.get('tk_parity'), d.get('cabins')
        if type(active) is not bool or parity not in ('even', 'odd', 'none'):
            raise ValueError('Trạng thái hoặc lịch xe không hợp lệ')
        if not isinstance(cabins, list) or len(cabins) > 60 or any(not isinstance(label, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,8}', label) for label in cabins):
            raise ValueError('Tối đa 60 khoang; mã khoang gồm 1–8 chữ cái, chữ số hoặc dấu -')
        cabins = [label.upper() for label in cabins]
        if len(set(cabins)) != len(cabins):
            raise ValueError('Mã khoang không được trùng nhau')
        for ticket in c.execute('SELECT * FROM tickets WHERE bus_id=? AND day>=? AND cancelled_at IS NULL', (bus['id'], stamp[:10])).fetchall():
            if ticket['cabin'] not in cabins:
                raise ValueError('Có vé chưa hủy ở khoang bị xóa. Hãy xử lý vé trước.')
            if parity != bus['tk_parity'] and direction(c, {**bus, 'tk_parity': parity}, ticket['day']) not in (ticket['origin'], 'OFF'):
                raise ValueError('Lịch mới trái chiều vé đã bán. Hãy xử lý vé hoặc đặt ngoại lệ ngày trước.')
        c.execute('UPDATE bus_sales SET active=?,tk_parity=?,cabins_json=? WHERE bus_id=?', (active, parity, json.dumps(cabins), bus['id']))
    else:
        day = valid_day(d.get('day'))
        origin = d.get('origin')
        if day < stamp[:10] or origin not in ('auto', 'OFF', 'TK', 'SG'):
            raise ValueError('Chỉ chỉnh lịch từ hôm nay; chọn chiều chạy hoặc nghỉ')
        target = route(bus['tk_parity'], day) if origin == 'auto' else origin
        if target != 'OFF' and c.execute('SELECT 1 FROM tickets WHERE bus_id=? AND day=? AND origin!=? AND cancelled_at IS NULL', (bus['id'], day, target)).fetchone():
            raise ValueError('Ngày này có vé ở chiều ngược lại. Hãy xử lý vé trước khi đổi chiều.')
        if origin == 'auto':
            c.execute('DELETE FROM bus_days WHERE bus_id=? AND day=?', (bus['id'], day))
        else:
            c.execute('INSERT INTO bus_days(bus_id,day,origin) VALUES(?,?,?) ON CONFLICT(bus_id,day) DO UPDATE SET origin=excluded.origin', (bus['id'], day, origin))
    c.execute('UPDATE buses SET version=version+1 WHERE id=?', (bus['id'],))
    c.execute('INSERT INTO fleet_audit(actor,action,before_json,after_json,at) VALUES(?,?,?,?,?)',
              (user['id'], 'ticket_'+kind, json.dumps(bus, ensure_ascii=False), json.dumps(d, ensure_ascii=False), stamp))
    return {'ok': True}


def cash(c, ticket, user, stamp, refund=False):
    c.execute('INSERT INTO cash_entries(kind,amount,branch,actor,note,at,ticket_id) VALUES(?,?,?,?,?,?,?)',
              ('expense' if refund else 'income', ticket['price'], ticket['origin'], user['id'],
               ('Hoàn tiền vé #' if refund else 'Thu vé #')+str(ticket['id']), stamp, ticket['id']))


def receipt(c, ticket_id):
    row = c.execute('SELECT * FROM tickets WHERE id=?', (ticket_id,)).fetchone()
    bus = c.execute('SELECT name,plate,phone FROM buses WHERE id=?', (row['bus_id'],)).fetchone()
    return {'ok': True, 'id': row['id'], 'price': row['price'], 'hold_until': row['hold_until'], 'vehicle': dict(bus), 'contact_phone': notifications.contact_phone(c)}


def sell(c, d, user, stamp):
    day = valid_day(d.get('day'))
    bus_id = ident(d['bus_id']) if d.get('bus_id') is not None else None
    origin, passengers, paid = d.get('origin'), d.get('passengers'), d.get('paid')
    if origin not in ('TK', 'SG') or type(passengers) is not int or passengers not in PRICES or type(paid) is not bool:
        raise ValueError('Chọn chiều đi, 1 hoặc 2 người và trạng thái thanh toán')
    if user['role'] != 'admin' and origin != user['branch']:
        raise ValueError('Nhân viên chỉ bán vé xuất phát tại chi nhánh của mình')
    name, phone, cabin = fleet.text(d, 'name', 100), fleet.text(d, 'phone', 11, False), fleet.text(d, 'cabin', 8).upper()
    email = fleet.text(d, 'email', 254, False)
    channel = d.get('contact_channel', 'email' if email else 'sms')
    if phone and not re.fullmatch(r'0[0-9]{8,10}', phone):
        raise ValueError('SĐT phải có 9–11 chữ số và bắt đầu bằng 0')
    if email and not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", email):
        raise ValueError('Địa chỉ email không hợp lệ')
    if channel not in ('email', 'sms') or not (email if channel == 'email' else phone):
        raise ValueError('Nhập email hoặc số điện thoại cho kênh nhận xác nhận đã chọn')
    request_id = fleet.text(d, 'request_id', 80)
    if len(request_id) < 16:
        raise ValueError('Mã yêu cầu không hợp lệ')
    pickup = ticket_routes.selected(d, 'pickup', origin, day)
    dropoff = ticket_routes.selected(d, 'dropoff', origin, day)
    note = fleet.text(d, 'note', 300, False)
    payload = json.dumps([bus_id, day, origin, cabin, passengers, name, phone, paid, user['id'], pickup, dropoff, note, email, channel], ensure_ascii=False)
    c.execute('BEGIN IMMEDIATE')
    expire(c, stamp)
    old = c.execute('SELECT * FROM tickets WHERE request_id=?', (request_id,)).fetchone()
    if old:
        if old['request_json'] != payload:
            raise ValueError('Yêu cầu đã được dùng cho vé khác')
        if old['cancelled_at']:
            raise ValueError('Vé của yêu cầu này đã hủy hoặc hết hạn. Vui lòng đặt lại.')
        return receipt(c, old['id'])
    if bus_id is None:
        for candidate in c.execute('SELECT id FROM buses ORDER BY id').fetchall():
            option = settings(c, candidate['id'])
            if option['active'] and direction(c, option, day) == origin and cabin in option['cabins'] and not c.execute(
                    'SELECT 1 FROM tickets WHERE bus_id=? AND day=? AND cabin=? AND cancelled_at IS NULL', (option['id'], day, cabin)).fetchone():
                bus_id = option['id']; break
        if bus_id is None:
            raise ValueError('Khoang đã hết chỗ trong ngày/chiều này. Vui lòng chọn lại.')
    bus = settings(c, bus_id)
    if day < stamp[:10] or not bus['active'] or direction(c, bus, day) != origin:
        raise ValueError('Xe nghỉ, sai chiều hoặc ngày đã qua. Hãy tải lại lịch xe.')
    if day == stamp[:10] and pickup['time'] and pickup['time'] <= stamp[11:16]:
        raise ValueError('Điểm đón đã qua giờ dự kiến hôm nay. Chọn chuyến khác hoặc xác nhận điểm đón khác với nhà xe.')
    if cabin not in bus['cabins']:
        raise ValueError('Khoang không có trên xe. Hãy tải lại sơ đồ.')
    if c.execute('SELECT 1 FROM tickets WHERE bus_id=? AND day=? AND cabin=? AND cancelled_at IS NULL', (bus_id, day, cabin)).fetchone():
        raise ValueError('Khoang vừa được đặt. Hãy chọn khoang khác.')
    ticket_id = c.execute('''INSERT INTO tickets(bus_id,day,origin,cabin,passengers,price,name,phone,created_by,created_at,paid_at,request_id,request_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''', (bus_id, day, origin, cabin, passengers, PRICES[passengers], name, phone, user['id'], stamp, stamp if paid else None, request_id, payload)).lastrowid
    c.execute('UPDATE tickets SET pickup_json=?,dropoff_json=?,note=?,email=?,contact_channel=? WHERE id=?', (json.dumps(pickup, ensure_ascii=False), json.dumps(dropoff, ensure_ascii=False), note, email, channel, ticket_id))
    hold_until = (datetime.fromisoformat(stamp)+timedelta(minutes=20)).isoformat(timespec='seconds') if user['role'] == 'public' else ''
    c.execute('UPDATE tickets SET hold_until=? WHERE id=?', (hold_until, ticket_id))
    if paid:
        cash(c, {'id': ticket_id, 'price': PRICES[passengers], 'origin': origin}, user, stamp)
    c.execute('INSERT INTO ticket_audit(ticket_id,actor,action,at) VALUES(?,?,?,?)', (ticket_id, user['id'], 'book', stamp))
    notifications.enqueue(c, ticket_id, 'paid' if paid else 'book', stamp)
    return receipt(c, ticket_id)


def action(c, kind, d, user, stamp):
    ticket_id = ident(d.get('id'))
    c.execute('BEGIN IMMEDIATE')
    row = c.execute('SELECT * FROM tickets WHERE id=?', (ticket_id,)).fetchone()
    if not row:
        raise ValueError('Không tìm thấy vé')
    if kind == 'confirm-call':
        if user['role'] != 'admin' and user['branch'] != row['origin']:
            raise ValueError('Chỉ chi nhánh xuất phát được xác nhận vé')
        if row['cancelled_at'] or (not row['paid_at'] and row['hold_until'] and row['hold_until'] <= stamp):
            raise ValueError('Vé đã hủy hoặc hết thời gian giữ chỗ')
        if not row['confirmed_at']:
            c.execute("UPDATE tickets SET confirmed_at=?,hold_until='' WHERE id=?", (stamp,ticket_id))
            c.execute('INSERT INTO ticket_audit(ticket_id,actor,action,at) VALUES(?,?,?,?)', (ticket_id,user['id'],kind,stamp))
            c.execute("UPDATE ticket_messages SET status='skipped' WHERE ticket_id=? AND event='book' AND status IN ('pending','not_configured','failed')", (ticket_id,))
            notifications.enqueue(c,ticket_id,'confirmed',stamp)
        return {'ok': True}
    if kind == 'cancel':
        reason = fleet.text(d, 'reason', 200)
        if row['cancelled_at']:
            return {'ok': True}
        if row['paid_at'] and d.get('refund') is not True:
            raise ValueError('Xác nhận đã hoàn đủ tiền cho khách trước khi hủy vé đã thu')
        c.execute('UPDATE tickets SET cancelled_at=?,cancel_reason=? WHERE id=?', (stamp, reason, ticket_id))
        if row['paid_at']:
            cash(c, row, user, stamp, refund=True)
    else:
        if user['role'] != 'admin' and user['branch'] != row['origin']:
            raise ValueError('Chỉ chi nhánh xuất phát được thu vé này')
        if row['cancelled_at']:
            raise ValueError('Vé đã hủy')
        if not row['paid_at'] and row['hold_until'] and row['hold_until'] <= stamp:
            raise ValueError('Vé đã hết thời gian giữ chỗ. Vui lòng tạo vé mới.')
        if row['paid_at']:
            return {'ok': True}
        c.execute('UPDATE tickets SET paid_at=? WHERE id=?', (stamp, ticket_id))
        cash(c, row, user, stamp)
    c.execute('INSERT INTO ticket_audit(ticket_id,actor,action,at) VALUES(?,?,?,?)', (ticket_id, user['id'], kind, stamp))
    if kind == 'collect':
        c.execute("UPDATE ticket_messages SET status='skipped' WHERE ticket_id=? AND event='book' AND status IN ('pending','not_configured','failed')", (ticket_id,))
    notifications.enqueue(c, ticket_id, 'paid' if kind == 'collect' else 'cancel', stamp)
    return {'ok': True}
