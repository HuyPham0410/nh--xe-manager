'use client';

import { useState, type FormEvent } from 'react';
import { api, errorMessage } from '../lib/api';
import type { User } from '../lib/types';

export function LoginForm({ onLogin }: { onLogin: (user: User) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true); setError('');
    try {
      await api('/login', { data: Object.fromEntries(form) });
      onLogin(await api<User>('/me'));
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }

  return <section className="login panel">
    <span className="eyebrow">CHÀO BẠN, MỘT NGÀY LÀM VIỆC MỚI</span>
    <h1>Xin chào,<br />Thanh Tĩnh.</h1><p>Không gian làm việc của nhà xe. Theo dõi hàng hóa, vé xe và đội ngũ trong cùng một nơi.</p>
    <form onSubmit={submit}>
      <label>Tài khoản<input name="username" autoComplete="username" required /></label>
      <label>Mật khẩu<input name="password" type="password" autoComplete="current-password" required /></label>
      <p role="alert">{error}</p><button disabled={busy}>{busy ? 'Đang đăng nhập…' : 'Mở sổ →'}</button>
    </form>
    <a className="login-booking-link" href="/dat-ve">Bạn cần đặt vé? Đi đến trang khách hàng →</a>
  </section>;
}
