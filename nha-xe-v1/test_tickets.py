import http.client
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
import app


class QuietHandler(app.Handler):
    def log_message(self, *args):
        pass


class TicketTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_root, cls.old_db = app.ROOT, app.DB
        cls.tmp = tempfile.TemporaryDirectory()
        app.ROOT = Path(cls.tmp.name); app.DB = app.ROOT/'test.sqlite3'
        app.init_db()
        cls.passwords = dict(line.split(': ', 1) for line in (app.ROOT/'TAI-KHOAN.txt').read_text(encoding='utf-8').splitlines()[1:])
        cls.server = app.ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        app.ROOT, app.DB = cls.old_root, cls.old_db
        cls.tmp.cleanup()

    def setUp(self):
        self.clock = patch.object(app, 'now', return_value='2026-10-24T08:00:00+07:00')
        self.clock.start(); self.addCleanup(self.clock.stop)
        with app.connect() as c:
            c.execute('DELETE FROM ticket_messages'); c.execute('DELETE FROM booking_limits')
            c.execute('DELETE FROM cash_entries'); c.execute('DELETE FROM ticket_audit'); c.execute('DELETE FROM tickets')
            c.execute('DELETE FROM fleet_audit'); c.execute('DELETE FROM bus_days')
            c.execute('UPDATE buses SET version=1')
            for i, parity in [(1, 'even'), (2, 'odd'), (3, 'none')]:
                c.execute('UPDATE bus_sales SET active=1,tk_parity=?,cabins_json=? WHERE bus_id=?', (parity, json.dumps(app.tickets.DEFAULT_CABINS), i))
        self.admin = self.login('admin'); self.tk = self.login('nhanvien_tk'); self.sg = self.login('nhanvien_sg')

    def request(self, path, data=None, auth=None, csrf=True):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        headers = {'Content-Type': 'application/json'}
        if auth:
            headers['Cookie'] = auth[0]
            if csrf: headers['X-CSRF-Token'] = auth[1]
        connection.request('GET' if data is None else 'POST', path, None if data is None else json.dumps(data), headers)
        response = connection.getresponse()
        result = response.status, json.loads(response.read()), response.getheader('Set-Cookie')
        connection.close(); return result

    def login(self, name):
        status, _, cookie = self.request('/api/login', {'username': name, 'password': self.passwords[name]})
        self.assertEqual(status, 200)
        cookie = cookie.split(';')[0]
        return cookie, self.request('/api/me', auth=(cookie, ''))[1]['csrf']

    def listing(self, day='2026-10-24', origin='TK'):
        status, data, _ = self.request(f'/api/tickets?day={day}&origin={origin}', auth=self.admin)
        self.assertEqual(status, 200)
        return data

    def booking(self, **changes):
        return {'bus_id': 1, 'day': '2026-10-24', 'origin': 'TK', 'cabin': '1A1', 'passengers': 1,
                'name': 'Khách thử', 'phone': '0901234567', 'paid': False,
                'pickup_id': 'qn-office', 'dropoff_id': 'sg-office', 'note': '',
                'request_id': 'request-ticket-00001', **changes}

    def post(self, kind, data, auth=None):
        return self.request('/api/tickets/'+kind, data, auth or self.admin)

    def config(self, bus_id=1, **changes):
        bus = next(bus for bus in self.listing()['buses'] if bus['id'] == bus_id)
        return {**bus, 'active': bool(bus['active']), **changes}

    def test_schedule_seed_and_day_rollovers(self):
        initial = self.listing()
        self.assertEqual([bus['direction'] for bus in initial['buses']], ['TK', 'SG', 'OFF'])
        self.assertEqual([len(bus['cabins']) for bus in initial['buses']], [24, 24, 24])
        self.assertEqual(len(set(initial['buses'][0]['cabins'])), 24)
        self.assertEqual([bus['direction'] for bus in self.listing('2026-10-25')['buses']], ['SG', 'TK', 'OFF'])
        for day in ('2026-10-31', '2026-11-01'):
            self.assertEqual(self.listing(day)['buses'][0]['direction'], 'SG')
        for day, next_day in [('2026-12-31', '2027-01-01'), ('2028-02-29', '2028-03-01')]:
            stops = self.listing(day, 'SG')['dropoffs']
            self.assertEqual(next(s for s in stops if s['id']=='tam-ky')['day'], day)
            self.assertEqual(next(s for s in stops if s['id']=='qn-office')['day'], next_day)
        self.assertEqual(len(initial['pickups']), 22)
        self.assertEqual(len(initial['dropoffs']), 11)
        app.init_db()
        self.assertEqual(self.listing()['buses'], initial['buses'])

    def test_upgrade_empty_layout_does_not_overwrite_custom_layout(self):
        with app.connect() as c:
            c.execute("DELETE FROM fleet_migrations WHERE name='confirmed-24-cabins'")
            c.execute("UPDATE bus_sales SET cabins_json='[]' WHERE bus_id=1")
            c.execute('UPDATE bus_sales SET cabins_json=? WHERE bus_id=2', (json.dumps(['CUSTOM1']),))
        app.init_db()
        self.assertEqual(len(self.listing()['buses'][0]['cabins']), 24)
        self.assertEqual(self.listing()['buses'][1]['cabins'], ['CUSTOM1'])
        self.assertEqual(self.post('config', self.config(cabins=[]))[0], 200)
        app.init_db()
        self.assertEqual(self.listing()['buses'][0]['cabins'], [])

    def test_prices_income_idempotency_and_cancellation(self):
        payload = self.booking(paid=True, price=1)
        status, result, _ = self.post('book', payload, self.tk)
        self.assertEqual(status, 200); self.assertEqual(result['price'], 800000)
        self.assertEqual(self.post('book', payload, self.tk)[1], result)
        self.assertEqual(self.post('book', {**payload, 'passengers': 2}, self.tk)[0], 400)
        status, second, _ = self.post('book', self.booking(cabin='1B1', passengers=2, request_id='request-ticket-00002'), self.tk)
        self.assertEqual((status, second['price']), (200, 1200000))
        self.assertEqual(self.post('collect', {'id': second['id']}, self.sg)[0], 400)
        for _ in range(2): self.assertEqual(self.post('collect', {'id': second['id']}, self.tk)[0], 200)
        self.assertEqual(self.post('cancel', {'id': result['id'], 'reason': 'Khách đổi lịch'}, self.tk)[0], 403)
        self.assertEqual(self.post('cancel', {'id': result['id'], 'reason': 'Khách đổi lịch'})[0], 400)
        for _ in range(2): self.assertEqual(self.post('cancel', {'id': result['id'], 'reason': 'Khách đổi lịch', 'refund': True})[0], 200)
        self.assertEqual(self.post('collect', {'id': result['id']}, self.tk)[0], 400)
        self.assertEqual(self.listing()['buses'][0]['occupied'], ['1B1'])
        with app.connect() as c:
            totals = dict(c.execute('SELECT kind,SUM(amount) FROM cash_entries GROUP BY kind').fetchall())
            self.assertEqual(totals, {'income': 2000000, 'expense': 800000})
            self.assertEqual(c.execute('SELECT COUNT(*) FROM cash_entries').fetchone()[0], 3)
            self.assertEqual(c.execute("SELECT COUNT(*) FROM cash_entries WHERE branch='TK'").fetchone()[0], 3)
        self.assertEqual(self.post('book', self.booking(request_id='request-ticket-00003'), self.tk)[0], 200)
        report = self.request('/api/cash-report?period=month&anchor=2026-10', auth=self.admin)[1]
        self.assertEqual((report['income'], report['expense']), (2000000, 800000))

    def test_concurrent_buyers_cannot_sell_same_cabin(self):
        gate = threading.Barrier(2, timeout=10)
        def buy(index, auth):
            gate.wait()
            return self.post('book', self.booking(paid=True, request_id=f'parallel-request-{index}'), auth)[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(buy, 1, self.admin), pool.submit(buy, 2, self.tk)]
            self.assertEqual(sorted(f.result(timeout=15) for f in futures), [200, 400])
        with app.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0], 1)
            self.assertEqual(c.execute('SELECT SUM(amount) FROM cash_entries').fetchone()[0], 800000)

    def test_vehicle_rest_preserves_tickets_and_blocks_new_sales(self):
        self.assertEqual(self.post('book', self.booking())[0], 200)
        config = self.config(active=False)
        self.assertEqual(self.post('config', config, self.tk)[0], 403)
        self.assertEqual(self.post('config', config)[0], 200)
        bus = self.listing()['buses'][0]
        self.assertFalse(bus['can_sell']); self.assertEqual(len(bus['tickets']), 1)
        self.assertIsNone(bus['tickets'][0]['cancelled_at'])
        self.assertEqual(self.post('book', self.booking(cabin='1B1', request_id='rest-ticket-000002'))[0], 400)
        self.assertEqual(self.post('config', {**config, 'active': True})[0], 400)  # Stale editor.
        self.assertEqual(self.post('config', self.config(active=True))[0], 200)
        self.assertTrue(self.listing()['buses'][0]['can_sell'])

    def test_day_override_and_existing_booking_guards(self):
        self.assertEqual(self.post('book', self.booking())[0], 200)
        self.assertEqual(self.post('config', self.config(tk_parity='odd'))[0], 400)
        self.assertEqual(self.post('config', self.config(cabins=['1B1']))[0], 400)
        self.assertEqual(self.post('day', {**self.config(), 'day': '2026-10-24', 'origin': 'SG'})[0], 400)
        self.assertEqual(self.post('day', {**self.config(), 'day': '2026-10-24', 'origin': 'OFF'})[0], 200)
        self.assertEqual(self.listing()['buses'][0]['direction'], 'OFF')
        self.assertEqual(self.post('day', {**self.config(), 'day': '2026-10-24', 'origin': 'auto'})[0], 200)
        self.assertEqual(self.listing()['buses'][0]['direction'], 'TK')
        self.assertEqual(self.post('config', self.config(bus_id=3, tk_parity='even'))[0], 200)
        self.assertTrue(self.listing()['buses'][2]['can_sell'])
        self.assertEqual(self.post('day', {**self.config(bus_id=3), 'day': '2026-10-31', 'origin': 'TK'})[0], 200)
        self.assertEqual(self.listing('2026-10-31')['buses'][2]['direction'], 'TK')
        app.init_db()
        self.assertEqual(self.listing('2026-10-31')['buses'][2]['direction'], 'TK')

    def test_validation_authorization_and_stop_snapshots(self):
        self.assertEqual(self.request('/api/tickets')[0], 401)
        self.assertEqual(self.request('/api/tickets/book', self.booking(), self.tk, csrf=False)[0], 403)
        self.assertEqual(self.post('book', self.booking(), self.sg)[0], 400)
        for changes in ({'passengers': 3}, {'passengers': True}, {'day': '2026-10-23'}, {'day': '2026-02-30'}, {'day': '9999-12-31'},
                        {'origin': 'SG'}, {'cabin': 'missing'}, {'paid': 'true'}, {'phone': 'bad'},
                        {'pickup_id': 'an-suong'}, {'bus_id': 2}, {'bus_id': 3}):
            self.assertEqual(self.post('book', self.booking(**changes))[0], 400, changes)
        self.assertEqual(self.request('/api/tickets?day=bad&origin=SG', auth=self.admin)[0], 400)
        self.assertEqual(self.post('config', self.config(cabins=['1a1', '1A1']))[0], 400)
        with patch.object(app, 'now', return_value='2026-10-24T14:01:00+07:00'):
            self.assertEqual(self.post('book', self.booking())[0], 400)
        payload = self.booking(bus_id=2, origin='SG', pickup_id='an-suong', dropoff_id='hoi-an', note='Địa chỉ trung chuyển đã xác nhận')
        self.assertEqual(self.post('book', payload, self.sg)[0], 200)
        ticket = self.listing(origin='SG')['buses'][1]['tickets'][0]
        self.assertEqual(ticket['pickup']['time'], '13:10')
        self.assertEqual(ticket['dropoff']['day'], '2026-10-25')
        self.assertTrue(ticket['dropoff']['transfer'])
        self.assertEqual(ticket['note'], payload['note'])

    def guest(self):
        status, data, cookie = self.request('/api/public/availability?day=2026-10-24&origin=TK')
        self.assertEqual(status, 200)
        return (cookie.split(';')[0], data['csrf']), data

    def guest_payload(self, **changes):
        payload = self.booking(**{'email': 'customer@example.com', 'phone': '', 'contact_channel': 'email', **changes})
        payload.pop('bus_id', None)
        return payload

    def test_phone_booking_call_confirmation_and_contact_permissions(self):
        guest, _ = self.guest()
        payload = self.guest_payload(email='', phone='0901234567', contact_channel='sms')
        status, receipt, _ = self.request('/api/public/book', payload, guest)
        self.assertEqual(status, 200)
        self.assertEqual(receipt['vehicle']['phone'], '0868612311')
        self.assertIn('plate', receipt['vehicle'])
        self.assertEqual(self.post('contact', {'phone': '0906808217'}, self.tk)[0], 403)
        self.assertEqual(self.post('contact', {'phone': 'bad'})[0], 400)
        self.assertEqual(self.post('contact', {'phone': '0906808217'})[0], 200)
        self.assertEqual(self.post('confirm-call', {'id': receipt['id']}, self.sg)[0], 400)
        self.assertEqual(self.post('confirm-call', {'id': receipt['id']}, self.tk)[0], 200)
        self.assertEqual(self.post('confirm-call', {'id': receipt['id']}, self.tk)[0], 200)
        with patch.object(app, 'now', return_value='2026-10-24T09:00:00+07:00'):
            ticket = self.listing()['buses'][0]['tickets'][0]
        self.assertTrue(ticket['confirmed_at'])
        self.assertIsNone(ticket['paid_at'])
        self.assertIsNone(ticket['cancelled_at'])
        messages = [m for m in ticket['messages'] if m['event'] == 'confirmed']
        self.assertEqual(len(messages), 1)
        self.assertIn('0906808217', messages[0]['body'])
        self.assertIn('0868612311', messages[0]['body'])
        with app.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM cash_entries').fetchone()[0], 0)

    def test_guest_privacy_permissions_and_automatic_assignment(self):
        guest, available = self.guest()
        self.assertEqual(len(available['cabins']), 24)
        for key in ('buses', 'tickets', 'employees', 'users'):
            self.assertNotIn(key, available)
        self.assertNotIn('0868612311', json.dumps(available))
        for path in ('/api/tickets', '/api/fleet', '/api/cash-today', '/api/me'):
            self.assertEqual(self.request(path, auth=guest)[0], 401)
        payload = self.guest_payload()
        self.assertEqual(self.request('/api/public/book', payload, guest, csrf=False)[0], 403)
        for changes in ({'paid': True}, {'bus_id': 1}, {'contact_channel': 'sms'}):
            self.assertEqual(self.request('/api/public/book', {**payload, **changes}, guest)[0], 400)
        status, result, _ = self.request('/api/public/book', payload, guest)
        self.assertEqual(status, 200)
        self.assertEqual(result['hold_until'], '2026-10-24T08:20:00+07:00')
        self.assertEqual(self.request('/api/public/book', payload, guest)[1], result)
        with app.connect() as c:
            row = c.execute('SELECT * FROM tickets WHERE id=?', (result['id'],)).fetchone()
            self.assertEqual(row['bus_id'], 1)
            self.assertIsNone(row['paid_at'])
            self.assertEqual(c.execute('SELECT COUNT(*) FROM cash_entries').fetchone()[0], 0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM ticket_messages').fetchone()[0], 1)

    def test_auto_assignment_uses_next_available_service(self):
        self.assertEqual(self.post('config', self.config(bus_id=3, tk_parity='even'))[0], 200)
        first = self.booking(bus_id=None)
        second = self.booking(bus_id=None, request_id='auto-second-ticket')
        self.assertEqual(self.post('book', first)[0], 200)
        self.assertEqual(self.post('book', second)[0], 200)
        self.assertEqual(self.post('book', self.booking(bus_id=None, request_id='auto-third-ticket'))[0], 400)
        with app.connect() as c:
            self.assertEqual([row['bus_id'] for row in c.execute('SELECT bus_id FROM tickets ORDER BY id')], [1, 3])

    def test_guest_hold_expires_but_paid_ticket_survives(self):
        guest, _ = self.guest()
        result = self.request('/api/public/book', self.guest_payload(), guest)[1]
        result2 = self.request('/api/public/book', self.guest_payload(cabin='1B1', request_id='second-guest-ticket'), guest)[1]
        self.assertEqual(self.post('collect', {'id': result2['id']})[0], 200)
        with patch.object(app, 'now', return_value='2026-10-24T08:21:00+07:00'):
            self.assertEqual(self.post('collect', {'id': result['id']})[0], 400)
            self.assertEqual(self.listing()['buses'][0]['occupied'], ['1B1'])
            self.assertEqual(self.request('/api/public/book', self.guest_payload(), guest)[0], 400)
        with app.connect() as c:
            self.assertEqual(c.execute('SELECT SUM(amount) FROM cash_entries').fetchone()[0], 800000)
            self.assertIsNotNone(c.execute('SELECT cancelled_at FROM tickets WHERE id=?', (result['id'],)).fetchone()[0])

    def test_outbox_acceptance_failure_and_deduplication(self):
        payload = self.booking(email='customer@example.com', contact_channel='email', paid=True)
        result = self.post('book', payload)[1]
        self.post('book', payload)
        sent = []
        def sender(message):
            sent.append(message)
            return 'provider-message-1'
        with patch.object(app.notifications, 'configured', return_value=False):
            self.assertFalse(app.notifications.process_one(app.connect, app.now, sender))
        self.assertEqual(sent, [])
        with patch.object(app.notifications, 'configured', return_value=True):
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(app.notifications.process_one, app.connect, app.now, sender) for _ in range(2)]
                self.assertEqual(sorted(job.result(timeout=10) for job in jobs), [False, True])
        self.assertEqual(len(sent), 1)
        self.assertIn('Xác nhận đã thanh toán', sent[0]['body'])
        self.assertIn('0868612311', sent[0]['body'])
        with app.connect() as c:
            self.assertEqual(c.execute('SELECT status FROM ticket_messages').fetchone()[0], 'accepted')
        self.assertEqual(self.post('retry-message', {'id': sent[0]['id']})[0], 400)
        self.assertEqual(self.post('book', self.booking(cabin='1B1', email='other@example.com', contact_channel='email', request_id='outbox-second-ticket'))[0], 200)
        def timeout(_): raise TimeoutError('provider response missing')
        with patch.object(app.notifications, 'configured', return_value=True):
            self.assertTrue(app.notifications.process_one(app.connect, app.now, timeout))
            self.assertFalse(app.notifications.process_one(app.connect, app.now, sender))
        with app.connect() as c:
            message_id = c.execute("SELECT id FROM ticket_messages WHERE status='unknown'").fetchone()[0]
        self.assertEqual(self.post('retry-message', {'id': message_id})[0], 400)
        self.assertEqual(self.post('retry-message', {'id': message_id, 'checked_provider': True}, self.tk)[0], 403)
        self.assertEqual(self.post('retry-message', {'id': message_id, 'checked_provider': True})[0], 200)

    def test_guest_rate_limit_and_email_validation(self):
        guest, _ = self.guest()
        payload = self.guest_payload(email='bad\r\nBcc: hidden@example.com')
        self.assertEqual(self.request('/api/public/book', payload, guest)[0], 400)
        with app.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM ticket_messages').fetchone()[0], 0)
        for index in range(4):
            response = self.request('/api/public/book', self.guest_payload(request_id=f'limited-ticket-{index}', cabin=f'1A{index+1}'), guest)
            self.assertEqual(response[0], 200)
        self.assertEqual(self.request('/api/public/book', self.guest_payload(request_id='limited-ticket-more', cabin='1A5'), guest)[0], 429)


if __name__ == '__main__':
    unittest.main()
