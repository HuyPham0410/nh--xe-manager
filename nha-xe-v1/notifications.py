"""Durable confirmation outbox. Provider acceptance is not proof of delivery."""
import json
import os
import smtplib
import ssl
import threading
from email.message import EmailMessage
from urllib.request import Request, build_opener, HTTPRedirectHandler


def contact_phone(c):
    return c.execute("SELECT value FROM business_settings WHERE key='contact_phone'").fetchone()[0]


def init_db(c):
    c.execute("CREATE TABLE IF NOT EXISTS business_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    c.execute("INSERT OR IGNORE INTO business_settings VALUES('contact_phone','0906808217')")
    c.execute('''CREATE TABLE IF NOT EXISTS ticket_messages(
        id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL REFERENCES tickets(id),
        event TEXT NOT NULL, channel TEXT NOT NULL, recipient TEXT NOT NULL,
        subject TEXT NOT NULL, body TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        provider_id TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '',
        UNIQUE(ticket_id,event))''')


def enqueue(c, ticket_id, event, stamp):
    ticket = c.execute('SELECT * FROM tickets WHERE id=?', (ticket_id,)).fetchone()
    channel = ticket['contact_channel']
    recipient = ticket['email'] if channel == 'email' else ticket['phone']
    if not recipient:
        return
    state = {'book': 'Đã ghi nhận đặt vé — chưa thanh toán', 'paid': 'Xác nhận đã thanh toán vé', 'cancel': 'Xác nhận hủy vé', 'confirmed': 'Nhà xe đã gọi xác nhận đặt vé'}[event]
    origin = 'Sài Gòn' if ticket['origin'] == 'SG' else 'Quảng Nam / Tam Kỳ'
    destination = 'Quảng Nam / Tam Kỳ' if ticket['origin'] == 'SG' else 'Sài Gòn'
    parts = ['Nhà xe Thanh Tĩnh', state, f"Mã vé: #{ticket_id}", f"Khách: {ticket['name']}",
             f"Ngày đi: {ticket['day']}", f'{origin} → {destination}',
             f"Khoang {ticket['cabin']} · {ticket['passengers']} người",
             f"Giá vé: {ticket['price']:,} VND".replace(',', '.')]
    bus = c.execute('SELECT name,phone,plate FROM buses WHERE id=?', (ticket['bus_id'],)).fetchone()
    parts.extend([f"Xe: {bus['name']} — Biển số: {bus['plate'] or 'Nhà xe sẽ cập nhật'}", f"SĐT xe: {bus['phone']}", f'Liên hệ nhà xe: {contact_phone(c)}'])
    for column, label in [('pickup_json', 'Đón'), ('dropoff_json', 'Trả')]:
        stop = json.loads(ticket[column]) if ticket[column] else None
        if stop:
            parts.append(f"{label}: {stop['name']} — {stop['address']}" +
                         (f" · {stop['time']} ngày {stop['day']} (dự kiến)" if stop['time'] else ' · Giờ cần xác nhận với nhà xe'))
    if event == 'book': parts.append('Vui lòng liên hệ nhà xe để thanh toán. Đây chưa phải xác nhận đã nhận tiền.')
    if event == 'book' and ticket['hold_until']: parts.append('Giữ chỗ đến: '+ticket['hold_until']+'. Chưa thanh toán sẽ tự hết hạn.')
    if event == 'cancel': parts.append('Đã ghi nhận hoàn đủ tiền.' if ticket['paid_at'] else 'Vé chưa thanh toán đã được hủy.')
    c.execute('''INSERT OR IGNORE INTO ticket_messages(ticket_id,event,channel,recipient,subject,body,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?)''', (ticket_id, event, channel, recipient, f'Thanh Tĩnh — {state} #{ticket_id}', '\n'.join(parts), stamp, stamp))


def configured(channel):
    if channel == 'email':
        return bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM') and os.getenv('SMTP_USER') and os.getenv('SMTP_PASSWORD'))
    return bool(os.getenv('SMS_GATEWAY_URL', '').startswith('https://') and os.getenv('SMS_GATEWAY_TOKEN'))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def deliver(message):
    if message['channel'] == 'email':
        email = EmailMessage()
        email['From'] = os.environ['SMTP_FROM']; email['To'] = message['recipient']
        email['Subject'] = message['subject']
        email['Message-ID'] = f"<ticket-message-{message['id']}@{os.environ['SMTP_FROM'].rsplit('@', 1)[-1]}>"
        email.set_content(message['body'])
        context = ssl.create_default_context()
        mode = os.getenv('SMTP_SECURITY', 'ssl')
        if mode not in ('ssl', 'starttls'):
            raise ValueError('SMTP_SECURITY must be ssl or starttls')
        host = os.environ['SMTP_HOST']; port = int(os.getenv('SMTP_PORT') or ('465' if mode == 'ssl' else '587'))
        client = smtplib.SMTP_SSL(host, port, timeout=15, context=context) if mode == 'ssl' else smtplib.SMTP(host, port, timeout=15)
        try:
            if mode == 'starttls': client.starttls(context=context)
            client.login(os.environ['SMTP_USER'], os.environ['SMTP_PASSWORD'])
            refused = client.send_message(email)
            if refused: raise smtplib.SMTPRecipientsRefused(refused)
        finally:
            # Close without QUIT: an error after DATA acceptance must not hide success.
            client.close()
        return str(email['Message-ID'])
    recipient = '+84'+message['recipient'][1:]
    payload = json.dumps({'to': recipient, 'text': message['body'], 'idempotency_key': f"ticket-message-{message['id']}"}).encode()
    request = Request(os.environ['SMS_GATEWAY_URL'], payload,
                      {'Content-Type': 'application/json', 'Authorization': 'Bearer '+os.environ['SMS_GATEWAY_TOKEN']}, method='POST')
    with build_opener(NoRedirect).open(request, timeout=15) as response:
        result = json.loads(response.read(16384))
    if result.get('accepted') is not True or not isinstance(result.get('message_id'), str) or not result['message_id']:
        raise ValueError('Gateway did not confirm acceptance')
    return result['message_id'][:200]


def process_one(connect, now, sender=deliver):
    # Claim under the write lock; release it before making a network request.
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        rows = c.execute("SELECT * FROM ticket_messages WHERE status IN ('pending','not_configured') ORDER BY id").fetchall()
        message = None
        for row in rows:
            if not configured(row['channel']):
                c.execute("UPDATE ticket_messages SET status='not_configured',error='Chưa cấu hình dịch vụ gửi' WHERE id=?", (row['id'],))
                continue
            # Suppress obsolete pending booking/paid messages after cancellation.
            cancelled = c.execute('SELECT cancelled_at FROM tickets WHERE id=?', (row['ticket_id'],)).fetchone()['cancelled_at']
            if cancelled and row['event'] != 'cancel':
                c.execute("UPDATE ticket_messages SET status='skipped',updated_at=? WHERE id=?", (now(), row['id']))
                continue
            message = dict(row)
            c.execute("UPDATE ticket_messages SET status='sending',attempts=attempts+1,updated_at=?,error='' WHERE id=?", (now(), row['id']))
            break
    if message is None: return False
    try:
        provider_id = sender(message)
        status, error = 'accepted', ''
    except (smtplib.SMTPAuthenticationError, smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, ConnectionRefusedError):
        status, error, provider_id = 'failed', 'Dịch vụ từ chối gửi. Kiểm tra cấu hình/người nhận trước khi thử lại.', ''
    except Exception:
        # A timeout may occur after provider acceptance; no automatic duplicate retry.
        status, error, provider_id = 'unknown', 'Chưa xác định dịch vụ đã nhận hay chưa. Kiểm tra nhà cung cấp trước khi gửi lại.', ''
    with connect() as c:
        c.execute('UPDATE ticket_messages SET status=?,error=?,provider_id=?,updated_at=? WHERE id=?', (status, error, provider_id, now(), message['id']))
    return True


def start_worker(connect, now, expire=None):
    with connect() as c:
        c.execute("UPDATE ticket_messages SET status='unknown',error='Máy chủ khởi động lại khi đang gửi; kiểm tra dịch vụ trước khi gửi lại.' WHERE status='sending'")
    stopped = threading.Event()
    def work():
        while not stopped.is_set():
            try:
                if expire:
                    with connect() as c:
                        c.execute('BEGIN IMMEDIATE')
                        expire(c, now())
                if process_one(connect, now): continue
            except Exception:
                pass  # No customer data or credentials in logs; outbox remains persistent.
            stopped.wait(5)
    threading.Thread(target=work, daemon=True).start()
    return stopped
