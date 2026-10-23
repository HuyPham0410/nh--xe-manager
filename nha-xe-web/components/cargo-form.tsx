'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, errorMessage } from '../lib/api';
import type { Branch, CargoInput, Payment, User } from '../lib/types';
import { branchName } from '../lib/format';

export function CargoForm({ user, initialBranch, onSaved, onClose }: {
  user: User; initialBranch: Branch | ''; onSaved: () => void; onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const phone = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [origin, setOrigin] = useState<Branch | ''>(initialBranch);

  useEffect(() => { dialog.current?.showModal(); phone.current?.focus(); }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const text = (key: string) => String(values.get(key) ?? '').trim();
    const input: CargoInput = {
      receiver_phone: text('receiver_phone'), receiver_name: text('receiver_name'),
      goods_description: text('goods_description'), quantity: Number(text('quantity')),
      fee: Number(text('fee')), payment: text('payment') as Payment,
      delivery_place: text('delivery_place'), note: text('note'),
    };
    setBusy(true); setMessage('');
    try {
      await api('/cargo', { data: user.role === 'admin' ? { ...input, branch: origin } : input, csrf: user.csrf });
      form.reset(); setMessage('✓ Đã lưu. Nhập đơn tiếp theo.');
      phone.current?.focus(); onSaved();
    } catch (error) { setMessage(errorMessage(error)); }
    finally { setBusy(false); }
  }

  return <dialog ref={dialog} onCancel={event => { if (busy) event.preventDefault(); }} onClose={onClose} aria-labelledby="cargo-title">
    <form onSubmit={submit}>
      <div className="dialogHead"><div><span className="eyebrow">NHẬN HÀNG MỚI</span><h2 id="cargo-title">Ghi thêm một đơn</h2></div>
        <button type="button" disabled={busy} className="secondary" onClick={onClose} aria-label="Đóng">✕</button></div>
      <div className="formGrid">
        {user.role === 'admin' && <label className="wide">Nhận hàng tại chi nhánh<select required value={origin} disabled={busy} onChange={event => setOrigin(event.target.value as Branch | '')}><option value="" disabled>Chọn chi nhánh nhận hàng</option><option value="SG">Sài Gòn → Tam Kỳ</option><option value="TK">Tam Kỳ → Sài Gòn</option></select></label>}
        {origin && <p className="wide">Chiều gửi: {branchName(origin)} → {branchName(origin === 'SG' ? 'TK' : 'SG')}</p>}
        <label>SĐT người nhận<input ref={phone} name="receiver_phone" inputMode="tel" pattern="[0-9]{9,11}" maxLength={11} required /></label>
        <label>Tên người nhận<input name="receiver_name" maxLength={100} required /></label>
        <label className="wide">Loại hàng<input name="goods_description" list="goods" maxLength={200} required placeholder="Ví dụ: 1 xọt + 2 bao" /><datalist id="goods"><option>Xọt</option><option>Xọt + bao</option><option>Giấy + bao</option></datalist></label>
        <label>Số lượng<input name="quantity" type="number" min={1} max={10000} defaultValue={1} required /></label>
        <label>Cước (đồng)<input name="fee" type="number" min={0} max={100000000} step={1} required /></label>
        <label className="wide">Thanh toán<select name="payment"><option value="paid">Đã trả</option><option value="destination">Trả đầu kia</option><option value="debt">Cho nợ</option></select></label>
        <label className="wide">Nơi giao<input name="delivery_place" maxLength={150} required /></label>
        <label className="wide">Ghi chú<input name="note" maxLength={500} /></label>
      </div>
      <p role="status">{message}</p><button disabled={busy} className="saveButton">{busy ? 'Đang lưu…' : 'Lưu & nhập đơn tiếp →'}</button>
    </form>
  </dialog>;
}
