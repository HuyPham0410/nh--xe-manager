"""Guest cookie/CSRF and persistent request limits; no staff privileges."""
import hashlib
import hmac
import secrets
import time
from http.cookies import SimpleCookie

SECRET = secrets.token_bytes(32)


def init_db(c):
    c.execute('CREATE TABLE IF NOT EXISTS booking_limits(key TEXT NOT NULL,at REAL NOT NULL)')
    c.execute('CREATE INDEX IF NOT EXISTS booking_limits_key ON booking_limits(key,at)')
    c.execute('INSERT OR IGNORE INTO users(username,salt,password,branch,role) VALUES(?,?,?,?,?)',
              ('__web_booking__', secrets.token_hex(16), secrets.token_hex(32), 'TK', 'public'))


def token_from_cookie(header):
    try:
        cookie = SimpleCookie(); cookie.load(header or '')
        token = cookie['booking_session'].value
        expiry, nonce, signature = token.split('.')
        body = expiry+'.'+nonce
        if int(expiry) < time.time() or not hmac.compare_digest(signature, hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()):
            return ''
        return token
    except (KeyError, ValueError):
        return ''


def create_token():
    body = str(int(time.time()+1800))+'.'+secrets.token_hex(24)
    return body+'.'+hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()


def allow(c, ip, email):
    current = time.time()
    keys = [('ip:'+ip, 8), ('mail:'+hashlib.sha256(str(email).strip().lower().encode()).hexdigest(), 4)]
    c.execute('BEGIN IMMEDIATE')
    c.execute('DELETE FROM booking_limits WHERE at<?', (current-1800,))
    for key, limit in keys:
        if c.execute('SELECT COUNT(*) FROM booking_limits WHERE key=?', (key,)).fetchone()[0] >= limit:
            return False
    c.executemany('INSERT INTO booking_limits(key,at) VALUES(?,?)', [(key, current) for key, _ in keys])
    return True
