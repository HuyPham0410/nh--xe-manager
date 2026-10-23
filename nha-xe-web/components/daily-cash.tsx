'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, errorMessage } from '../lib/api';
import { branchName, money } from '../lib/format';
import type { Branch, User } from '../lib/types';

interface CashReport {
  date: string; start: string; end: string; income: number; expense: number; net: number; count: number;
  entries: { id: number; kind: 'income' | 'expense'; amount: number; note: string; username: string; branch: Branch; at: string }[];
}

export function DailyCash({ user, branch, revision }: { user: User; branch: Branch | ''; revision: number }) {
  const [report, setReport] = useState<CashReport | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [period, setPeriod] = useState('today');
  const [anchor, setAnchor] = useState(user.today);
  const [month, setMonth] = useState(user.today.slice(0,7));
  // Retry an uncertain network request with the same key and payload.
  const pending = useRef<{ request_id: string; amount: number; note: string; branch: Branch | '' } | null>(null);

  useEffect(() => {
    const timer = setInterval(() => setReload(value => value + 1), 30000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setReport(null);
    api<CashReport>(`/cash-report?${new URLSearchParams({ branch, period, ...(period === 'today' ? {} : { anchor: period === 'month' ? month : anchor }) })}`, { signal: controller.signal })
      .then(data => { setReport(data); setError(''); })
      .catch(error => { if (!controller.signal.aborted) setError(errorMessage(error)); });
    return () => controller.abort();
  }, [branch, revision, reload, period, anchor, month]);

  async function expense(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    if (!pending.current) pending.current = {
      request_id: crypto.randomUUID(), amount: Number(values.get('amount')),
      note: String(values.get('note') ?? '').trim(),
      branch: user.role === 'admin' ? String(values.get('branch') ?? '') as Branch | '' : user.branch,
    };
    setBusy(true); setNotice('');
    try {
      await api('/expenses', { data: pending.current, csrf: user.csrf });
      pending.current = null; form.reset(); setShowForm(false);
      setNotice('Đã ghi khoản chi.'); setReload(value => value + 1);
    } catch (error) {
      // A rejected validation/authorization did not create an entry; allow correction.
      if (error instanceof Error && 'status' in error && Number(error.status) >= 400 && Number(error.status) < 500) pending.current = null;
      setNotice(errorMessage(error));
    } finally { setBusy(false); }
  }

  return <section className="panel cash-panel" aria-label="Tổng thu chi">
    <div className="cash-title"><div><h2>Tổng thu chi</h2>
      <p>{user.role === 'admin' ? (branch ? `Tất cả tài khoản tại ${branchName(branch)}` : 'Tất cả tài khoản, cả hai đầu') : `Của tài khoản ${user.username}`}</p></div>
      <button className="secondary" onClick={() => setShowForm(true)}>+ Ghi khoản chi</button></div>
    <div className="tools"><label>Khoảng thời gian<select value={period} onChange={event => setPeriod(event.target.value)}><option value="today">Hôm nay</option><option value="fortnight">2 tuần (14 ngày)</option><option value="month">1 tháng</option></select></label>
      {period === 'fortnight' && <label>Ngày kết thúc<input type="date" value={anchor} onChange={event => { if (event.target.value) setAnchor(event.target.value); }} /></label>}
      {period === 'month' && <label>Chọn tháng<input type="month" value={month} onChange={event => { if (event.target.value) setMonth(event.target.value); }} /></label>}
    </div>
    {error ? <p role="alert">{error} <button className="secondary" onClick={() => setReload(value => value + 1)}>Thử lại</button></p> : report ? <>
      <div className="cash-metrics">{[['Đã thu', report.income], ['Đã chi', report.expense], ['Thu − Chi', report.net]].map(([label,amount]) => <div className="metric" key={label}><span>{label}</span><strong>{money(Number(amount))}</strong></div>)}</div>
      <p>Từ {report.start} đến hết {report.end}, theo giờ Việt Nam. Thu − Chi không bao gồm tồn đầu kỳ hoặc bàn giao quỹ.</p>
      <details><summary>Chi tiết thu chi ({report.count} khoản)</summary><div className="tableWrap"><table><thead><tr><th>Giờ</th><th>Nội dung</th><th>Người ghi</th><th>Chi nhánh</th><th>Thu</th><th>Chi</th></tr></thead><tbody>
        {report.entries.map(entry => <tr key={entry.id}><td>{entry.at.slice(0,10)} {entry.at.slice(11,19)}</td><td>{entry.note}</td><td>{entry.username}</td><td>{branchName(entry.branch)}</td><td>{entry.kind === 'income' ? money(entry.amount) : '—'}</td><td>{entry.kind === 'expense' ? money(entry.amount) : '—'}</td></tr>)}
        {!report.entries.length && <tr><td colSpan={6}>Chưa có phát sinh trong khoảng này.</td></tr>}
      </tbody></table></div>{report.count > 100 && <p>Hiển thị 100 khoản gần nhất. Tổng tiền tính toàn bộ khoản trong khoảng đã chọn.</p>}</details>
    </> : <p role="status">Đang tải thu chi…</p>}
    {showForm && <form onSubmit={expense} className="expense-form"><h3>Ghi khoản chi hôm nay</h3>
      <fieldset disabled={busy || pending.current !== null}>
        {user.role === 'admin' && <label>Chi nhánh<select name="branch" defaultValue={branch} required><option value="" disabled>Chọn chi nhánh</option><option value="SG">Sài Gòn</option><option value="TK">Tam Kỳ</option></select></label>}
        <label>Số tiền (đồng)<input name="amount" type="number" min={1} max={100000000} step={1} required /></label>
        <label>Lý do chi<input name="note" maxLength={200} required placeholder="Ví dụ: bốc xếp, mua bao đựng hàng" /></label>
      </fieldset>
      <button disabled={busy}>{busy ? 'Đang ghi…' : pending.current ? 'Thử gửi lại khoản chi này' : 'Lưu khoản chi'}</button>{!pending.current && <button type="button" className="secondary" disabled={busy} onClick={() => setShowForm(false)}>Đóng</button>}
      {pending.current && !busy && <p>Chưa xác nhận được kết quả. Gửi lại cùng khoản chi sẽ không ghi trùng.</p>}
    </form>}
    <p role="status">{notice}</p>
  </section>;
}
