'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, ApiError, errorMessage } from '../lib/api';
import { branchName, money } from '../lib/format';
import type { Branch, Cargo, CargoAction, CargoList, User } from '../lib/types';
import { LoginForm } from './login-form';
import { CargoForm } from './cargo-form';
import { CargoTable } from './cargo-table';
import { DailyReport } from './daily-report';
import { DailyCash } from './daily-cash';
import { FleetWorkspace } from './fleet-workspace';
import { TicketWorkspace } from './ticket-workspace';
import { SimpleBooking } from './simple-booking';

type View = 'cargo' | 'search' | 'report' | 'fleet' | 'tickets' | 'ticket_admin';

export function CargoWorkspace() {
  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(true);
  const [view, setView] = useState<View>('cargo');
  const [date, setDate] = useState('');
  const [query, setQuery] = useState('');
  const [list, setList] = useState<CargoList>({ rows: [], truncated: false });
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [revision, setRevision] = useState(0);
  const [selectedBranch, setSelectedBranch] = useState<Branch | ''>('');
  const [flow, setFlow] = useState<'outbound' | 'inbound'>('outbound');
  const branchFilter = user?.role === 'admin' ? selectedBranch : '';
  const expireSession = useCallback(() => setUser(null), []);

  function loggedIn(value: User) { setUser(value); setDate(value.today); setMessage(''); setSelectedBranch(''); setFlow('outbound'); }
  useEffect(() => {
    const controller = new AbortController();
    api<User>('/me', { signal: controller.signal }).then(loggedIn).catch(error => {
      if (!controller.signal.aborted && !(error instanceof ApiError && error.status === 401)) setMessage(errorMessage(error));
    }).finally(() => { if (!controller.signal.aborted) setBooting(false); });
    return () => controller.abort();
  }, []);

  // Hủy yêu cầu cũ khi người dùng gõ tiếp để kết quả chậm không ghi đè kết quả mới.
  useEffect(() => {
    if (!user || view === 'report' || view === 'fleet' || view === 'tickets' || view === 'ticket_admin') return;
    const controller = new AbortController(); setLoading(true);
    const timer = setTimeout(() => {
      api<CargoList>(`/cargo?${new URLSearchParams({ date, q: query, branch: branchFilter, flow })}`, { signal: controller.signal })
        .then(setList).catch(error => {
          if (!controller.signal.aborted) {
            setMessage(errorMessage(error));
            if (error instanceof ApiError && error.status === 401) setUser(null);
          }
        }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [user, date, query, revision, view, branchFilter, flow]);

  async function logout() {
    setBusy(true);
    try { await api('/logout', { data: {}, csrf: user?.csrf }); setUser(null); setList({ rows: [], truncated: false }); setShowForm(false); setView('cargo'); setQuery(''); }
    catch (error) { setMessage(errorMessage(error)); }
    finally { setBusy(false); }
  }

  async function action(row: Cargo, action: CargoAction) {
    const label = { arrived: 'Đã tới', delivered: 'Đã giao', collect: 'Thu tiền', defer: 'Chuyển sang ngày kế tiếp' }[action];
    let vehicle: string | null = null;
    if (action === 'defer') {
      vehicle = window.prompt(`Đơn #${row.id} đang dự kiến đi ngày ${row.scheduled_date}. Nhập tên/biển số xe nhận thay vào ngày kế tiếp:`, row.vehicle);
      if (!vehicle?.trim()) return;
    }
    if (!window.confirm(`${label} — đơn #${row.id}, ${row.receiver_name}${action === 'collect' ? ' — ' + money(row.fee) + ' tại ' + branchName(row.branch === 'SG' ? 'TK' : 'SG') : ''}?`)) return;
    setBusy(true);
    try {
      await api('/action', { data: { id: row.id, action, ...(action === 'defer' ? { vehicle, expected_date: row.scheduled_date } : {}) }, csrf: user?.csrf });
      setRevision(value => value + 1); setMessage(action === 'defer' ? `Đơn #${row.id} đã sang sổ ngày kế tiếp. Chọn ngày kế hoặc Mọi ngày để xem.` : `Đã cập nhật đơn #${row.id}.`);
    } catch (error) { setMessage(errorMessage(error)); }
    finally { setBusy(false); }
  }

  function changeView(next: View) {
    setView(next);
    if (next === 'search') setDate('');
    if (next === 'report' && !date) setDate(user?.today ?? '');
  }

  return <><header><div className="brand"><span className="brand-mark" aria-hidden="true">TT</span><span>NHÀ XE THANH TĨNH<small>Quản lý hàng hóa · Vé xe · Nhân viên</small></span></div>
    {user && <div id="account">{user.username} · {user.role === 'admin' ? 'Quản lý hai đầu' : branchName(user.branch)} <button className="secondary" disabled={busy} onClick={logout}>Đăng xuất</button></div>}</header>
    <main>{booting ? <p role="status">Đang mở sổ…</p> : !user ? <LoginForm onLogin={loggedIn} /> : <>
      <nav aria-label="Chức năng"><button className={view === 'cargo' ? 'active' : ''} onClick={() => changeView('cargo')}>📦 Hàng gửi</button>
        <button className={view === 'search' ? 'active' : ''} onClick={() => changeView('search')}>⌕ Tìm hàng</button>
        {user.role === 'admin' && <button className={view === 'report' ? 'active' : ''} onClick={() => changeView('report')}>Tiền & lịch sử</button>}
        <button className={view === 'fleet' ? 'active' : ''} onClick={() => changeView('fleet')}>Xe & nhân viên</button>
        <button className={view === 'tickets' ? 'active' : ''} onClick={() => changeView('tickets')}>Bán vé</button>
        <button className={view === 'ticket_admin' ? 'active' : ''} onClick={() => changeView('ticket_admin')}>Sổ vé nội bộ</button></nav>
      {view === 'tickets' ? <SimpleBooking user={user} onExpired={expireSession} /> : view === 'ticket_admin' ? <TicketWorkspace user={user} onExpired={expireSession} /> : view === 'fleet' ? <FleetWorkspace user={user} onExpired={expireSession} /> : <>
      {user.role === 'admin' && <section className="branch-switch" aria-label="Chọn chi nhánh quản lý"><strong>Quản lý chi nhánh</strong><div className="branch-options">
        {([['', 'Tất cả hai đầu'], ['SG', 'Sài Gòn'], ['TK', 'Tam Kỳ']] as const).map(([value, label]) => <button key={value} className={selectedBranch === value ? '' : 'secondary'} aria-pressed={selectedBranch === value} disabled={busy} onClick={() => { setSelectedBranch(value); setMessage(''); }}>{label}</button>)}
      </div></section>}
      <DailyCash key={`${user.username}-${branchFilter}`} user={user} branch={branchFilter} revision={revision} />
      <div className="heading"><div><span className="eyebrow">{user.role === 'admin' ? (selectedBranch ? `Chi nhánh ${branchName(selectedBranch)}` : 'Tổng quan Sài Gòn & Tam Kỳ') : `${branchName(user.branch)} → ${branchName(user.branch === 'SG' ? 'TK' : 'SG')}`}</span>
        <h1>{{ cargo: 'Sổ hàng gửi', search: 'Tìm hàng', report: 'Tiền & lịch sử' }[view]}</h1><p>Nhập nhanh như viết tay, tìm lại chỉ trong vài giây.</p></div>
        <button onClick={() => setShowForm(true)}>+ Nhận hàng</button></div>
      <section className="panel"><div className="tools">
        {user.role === 'admin' && selectedBranch && view !== 'report' && <label>Chiều hàng<select value={flow} onChange={event => setFlow(event.target.value as 'outbound' | 'inbound')}><option value="outbound">Hàng gửi từ {branchName(selectedBranch)}</option><option value="inbound">Hàng đến {branchName(selectedBranch)}</option></select></label>}
        {view !== 'report' && <label className="search">Tìm SĐT / tên / hàng<input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Nhập số điện thoại, tên hoặc loại hàng…" /></label>}
        <label>{view === 'report' ? 'Ngày tổng kết' : 'Ngày đi trên sổ'}<input type="date" value={date} onChange={event => setDate(event.target.value || (view === 'report' ? user.today : ''))} /></label>
        {view !== 'report' && <button className="secondary" onClick={() => setDate('')}>Mọi ngày</button>}
        <button className="secondary" onClick={() => setRevision(value => value + 1)}>Tải lại</button>
        {view !== 'report' && <button className="secondary" disabled={loading} onClick={() => window.print()}>In danh sách</button>}
      </div>{view !== 'report' && <><p role="status">{loading ? 'Đang tìm…' : `${list.rows.length} đơn · ${date || 'Mọi ngày'} · ${branchFilter ? `${flow === 'outbound' ? 'Gửi từ' : 'Đến'} ${branchName(branchFilter)}` : 'Cả hai chiều'}`}{list.truncated && ' · Hơn 1.000 kết quả, hãy thu hẹp tìm kiếm.'}</p>
        {!loading && <CargoTable rows={list.rows} user={user} busy={busy} onAction={action} />}</>}</section>
      {view === 'report' && user.role === 'admin' && <DailyReport key={`${date}-${branchFilter}`} date={date || user.today} branch={branchFilter} revision={revision} />}
      {showForm && <CargoForm user={user} initialBranch={user.role === 'admin' ? selectedBranch : user.branch} onSaved={() => setRevision(value => value + 1)} onClose={() => setShowForm(false)} />}
      </>}
    </>}<p id="message" role="status">{message}</p></main></>;
}
