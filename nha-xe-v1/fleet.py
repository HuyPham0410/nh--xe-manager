"""Danh bạ xe, nhân viên và tổ xe hiện tại; không tạo tài khoản đăng nhập."""
import json
import re

SLOTS = ('driver1', 'driver2', 'assistant1', 'assistant2')


def init_db(c):
    c.executescript('''
        CREATE TABLE IF NOT EXISTS buses(
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
            plate TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS employees(
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, phone TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('driver','assistant')),
            active INTEGER NOT NULL CHECK(active IN (0,1)), version INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS bus_crew(
            bus_id INTEGER NOT NULL REFERENCES buses(id),
            slot TEXT NOT NULL CHECK(slot IN ('driver1','driver2','assistant1','assistant2')),
            employee_id INTEGER NOT NULL UNIQUE REFERENCES employees(id),
            PRIMARY KEY(bus_id,slot));
        CREATE TABLE IF NOT EXISTS fleet_audit(
            id INTEGER PRIMARY KEY, actor INTEGER NOT NULL REFERENCES users(id),
            action TEXT NOT NULL, before_json TEXT, after_json TEXT NOT NULL, at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fleet_migrations(name TEXT PRIMARY KEY);
    ''')
    # A marker prevents startup from restoring phone numbers edited by the manager.
    c.execute('BEGIN IMMEDIATE')
    if not c.execute("SELECT 1 FROM fleet_migrations WHERE name='initial-three-buses'").fetchone():
        for number in range(1, 4):
            c.execute('INSERT INTO buses(name,phone) VALUES(?,?)', (f'Xe {number}', f'086861231{number}'))
        c.execute("INSERT INTO fleet_migrations VALUES('initial-three-buses')")


def snapshot(c):
    buses = [dict(r) for r in c.execute('SELECT * FROM buses ORDER BY id')]
    for bus in buses:
        bus['crew'] = {r['slot']: r['employee_id'] for r in c.execute('SELECT * FROM bus_crew WHERE bus_id=?', (bus['id'],))}
    return {'buses': buses, 'employees': [dict(r) for r in c.execute('SELECT * FROM employees ORDER BY active DESC,name,id')]}


def text(data, key, limit, required=True):
    value = data.get(key, '')
    if not isinstance(value, str) or len(value.strip()) > limit or (required and not value.strip()):
        raise ValueError(f'Thông tin {key} không hợp lệ (tối đa {limit} ký tự)')
    return value.strip()


def existing(c, table, data):
    if any(type(data.get(key)) is not int or not 1 <= data[key] <= 2**63 - 1 for key in ('id', 'version')):
        raise ValueError('Mã hoặc phiên bản không hợp lệ. Hãy tải lại danh sách.')
    row = c.execute(f'SELECT * FROM {table} WHERE id=?', (data['id'],)).fetchone()
    if not row or row['version'] != data['version']:
        raise ValueError('Dữ liệu đã thay đổi hoặc không còn tồn tại. Hãy tải lại danh sách trước khi sửa.')
    return dict(row)


def save(c, kind, data, actor, stamp):
    # One write lock covers validation, assignment, version and audit together.
    c.execute('BEGIN IMMEDIATE')
    before = None
    if kind in ('employee', 'bus'):
        table = 'employees' if kind == 'employee' else 'buses'
        name, phone = text(data, 'name', 100), text(data, 'phone', 11)
        if not re.fullmatch(r'0[0-9]{8,10}', phone):
            raise ValueError('SĐT phải có 9–11 chữ số và bắt đầu bằng 0')
        if kind == 'bus' or data.get('id') is not None:
            before = existing(c, table, data)
        ident = before['id'] if before else None
        if c.execute(f'SELECT 1 FROM {table} WHERE phone=? AND id!=?', (phone, ident or -1)).fetchone():
            raise ValueError('Số điện thoại này đã có trong danh sách')
        if kind == 'employee':
            role, active = data.get('role'), data.get('active')
            if role not in ('driver', 'assistant') or type(active) is not bool:
                raise ValueError('Chọn vai trò và trạng thái nhân viên hợp lệ')
            if before and (not active or role != before['role']) and c.execute('SELECT 1 FROM bus_crew WHERE employee_id=?', (ident,)).fetchone():
                raise ValueError('Hãy thay người hoặc bỏ phân công xe trước khi đổi vai trò / cho nghỉ nhân viên này')
            if before:
                c.execute('UPDATE employees SET name=?,phone=?,role=?,active=?,version=version+1 WHERE id=?', (name, phone, role, active, ident))
            else:
                ident = c.execute('INSERT INTO employees(name,phone,role,active) VALUES(?,?,?,?)', (name, phone, role, active)).lastrowid
        else:
            plate = text(data, 'plate', 20, False).upper()
            if plate and c.execute('SELECT 1 FROM buses WHERE plate=? AND id!=?', (plate, ident)).fetchone():
                raise ValueError('Biển số này đã được dùng cho xe khác')
            c.execute('UPDATE buses SET name=?,phone=?,plate=?,version=version+1 WHERE id=?', (name, phone, plate, ident))
        after = dict(c.execute(f'SELECT * FROM {table} WHERE id=?', (ident,)).fetchone())
    elif kind == 'crew':
        before = existing(c, 'buses', data)
        ident = before['id']
        before['crew'] = {r['slot']: r['employee_id'] for r in c.execute('SELECT * FROM bus_crew WHERE bus_id=?', (ident,))}
        crew = data.get('crew')
        if not isinstance(crew, dict) or (crew and set(crew) != set(SLOTS)):
            raise ValueError('Phân công đủ 2 lái và 2 phụ, hoặc bỏ toàn bộ phân công')
        if any(type(value) is not int or not 1 <= value <= 2**63 - 1 for value in crew.values()) or len(set(crew.values())) != len(crew):
            raise ValueError('Bốn vị trí phải là bốn nhân viên khác nhau')
        for slot, employee_id in crew.items():
            employee = c.execute('SELECT * FROM employees WHERE id=?', (employee_id,)).fetchone()
            role = 'driver' if slot.startswith('driver') else 'assistant'
            if not employee or not employee['active'] or employee['role'] != role:
                raise ValueError('Nhân viên phải đang làm việc và đúng vai trò lái / phụ')
            if c.execute('SELECT 1 FROM bus_crew WHERE employee_id=? AND bus_id!=?', (employee_id, ident)).fetchone():
                raise ValueError('Nhân viên đã được phân công xe khác. Hãy bỏ phân công ở xe cũ trước.')
        c.execute('DELETE FROM bus_crew WHERE bus_id=?', (ident,))
        c.executemany('INSERT INTO bus_crew(bus_id,slot,employee_id) VALUES(?,?,?)', [(ident, slot, employee_id) for slot, employee_id in crew.items()])
        c.execute('UPDATE buses SET version=version+1 WHERE id=?', (ident,))
        after = {**before, 'crew': crew, 'version': before['version'] + 1}
    else:
        raise ValueError('Thao tác không hợp lệ')
    c.execute('INSERT INTO fleet_audit(actor,action,before_json,after_json,at) VALUES(?,?,?,?,?)',
              (actor, kind, json.dumps(before, ensure_ascii=False), json.dumps(after, ensure_ascii=False), stamp))
