'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, errorMessage } from '../lib/api';
import { money } from '../lib/format';
import type { Branch, User } from '../lib/types';

type Stop = { id: string; name: string; address: string; day: string; time: string; transfer: boolean };
type Availability = { day: string; origin: Branch; csrf?: string; email_ready: boolean; cabins: { label: string; remaining: number }[]; pickups: Stop[]; dropoffs: Stop[]; prices: Record<string, number> };
const dateLabel = (value: string) => value.split('-').reverse().join('/');

export function SimpleBooking({ user, onExpired }: { user?: User; onExpired?: () => void }) {
  const [day, setDay] = useState(user?.today ?? new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }).format(new Date()));
  const [origin, setOrigin] = useState<Branch>(user?.branch ?? 'TK');
  const [data, setData] = useState<Availability | null>(null);
  const [fresh, setFresh] = useState(false);
  const [revision, setRevision] = useState(0);
  const [cabin, setCabin] = useState('');
  const [passengers, setPassengers] = useState('1');
  const channel = 'sms';
  const [pickup, setPickup] = useState('');
  const [dropoff, setDropoff] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState<{ id: number; price: number; paid: boolean; hold_until?: string; vehicle: {name: string; plate: string; phone: string}; contact_phone: string } | null>(null);
  const request = useRef({ signature: '', id: '' });
  const prefix = user ? '/tickets' : '/public';
  useEffect(() => {
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    setFresh(false);
    async function load() {
      try {
        const next = await api<Availability>(`${prefix}/availability?${new URLSearchParams({ day, origin })}`, { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]) });
        if (!controller.signal.aborted) { setData(next); setFresh(true); }
      } catch (err) {
        if (!controller.signal.aborted) { setFresh(false); if (err instanceof ApiError && err.status === 401) onExpired?.(); }
      } finally { if (!controller.signal.aborted) timer = setTimeout(load, 5000); }
    }
    void load();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [day, origin, revision, prefix, onExpired]);
  function reset() { setCabin(''); setPickup(''); setDropoff(''); setData(null); setFresh(false); setSuccess(null); setError(''); }
  async function book(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!data) return;
    const form = new FormData(event.currentTarget);
    const paid = !!user && form.get('paid') === 'yes';
    const payload = { day, origin, cabin, passengers: Number(passengers), paid, name: form.get('name'), phone: form.get('contact'), email: '', contact_channel: channel,
      pickup_id: pickup, dropoff_id: dropoff, pickup_custom: form.get('pickup_custom') ?? '', dropoff_custom: form.get('dropoff_custom') ?? '', note: form.get('note') };
    const signature = JSON.stringify(payload);
    if (request.current.signature !== signature) request.current = { signature, id: crypto.randomUUID() };
    setBusy(true); setError('');
    try {
      const result = await api<{ id: number; price: number; hold_until?: string; vehicle: {name: string; plate: string; phone: string}; contact_phone: string }>(`${prefix}/book`, { data: { ...payload, request_id: request.current.id }, csrf: user?.csrf ?? data.csrf });
      setSuccess({ ...result, paid }); setCabin('');
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); setRevision(value => value + 1); }
  }
  const current = data?.day === day && data.origin === origin ? data : null;
  const available = fresh && !!current?.cabins.some(item => item.label === cabin && item.remaining > 0) && (!user || user.role === 'admin' || user.branch === origin);
  return <div className="simple-booking">
    <div className="heading booking-hero"><div><span className="eyebrow">THANH TĨNH · ĐỒNG HÀNH CÙNG BẠN</span><h1>Đặt vé dễ dàng.<br />An tâm chuyến đi.</h1><p>Quảng Nam / Tam Kỳ ↔ Sài Gòn</p><div className="fare-chips"><span>1 người / khoang <strong>800.000đ</strong></span><span>2 người / khoang <strong>1.200.000đ</strong></span></div></div></div>
    <ol className="booking-steps" aria-label="Các bước đặt vé"><li><b>1</b> Ngày &amp; nơi đi</li><li><b>2</b> Chọn giường</li><li><b>3</b> Điểm đón, trả</li><li><b>4</b> Thông tin khách</li></ol>
    <section className="panel"><h2><span className="step-number">1</span>Bạn muốn đi ngày nào?</h2><div className="formGrid"><label>Ngày đi<input type="date" value={day} disabled={busy} onChange={e => { if (e.target.value) { reset(); setDay(e.target.value); } }} /></label>
      <label>Nơi xuất phát<select value={origin} disabled={busy} onChange={e => { reset(); setOrigin(e.target.value as Branch); }}><option value="TK">Quảng Nam / Tam Kỳ → Sài Gòn</option><option value="SG">Sài Gòn → Quảng Nam / Tam Kỳ</option></select></label></div>
      <small className="booking-status" role="status">{fresh ? 'Tình trạng chỗ tự cập nhật.' : 'Đang kết nối để cập nhật chỗ…'}</small>
    </section>
    {success ? <section className="panel ticket-editor" role="status"><h2>Đã ghi nhận vé #{success.id}</h2><p>{success.paid ? 'Đã ghi nhận thanh toán' : 'Chưa thanh toán — vui lòng liên hệ nhà xe để hoàn tất'} · {money(success.price)}</p>{success.hold_until && <p>Giữ chỗ đến {success.hold_until.slice(11, 16)} ngày {dateLabel(success.hold_until.slice(0, 10))}. Chưa được nhà xe xác nhận hoặc thanh toán sẽ tự hết hạn.</p>}<p>Nhà xe đã lưu thông tin và sẽ gọi điện xác nhận. Tin nhắn do nhân viên gửi sau khi kiểm tra; vui lòng lưu mã vé này.</p><div className="booking-help"><strong>{success.vehicle.name}</strong><p>Biển số: {success.vehicle.plate || 'Nhà xe sẽ cập nhật khi xác nhận'}</p><p>Điện thoại xe: <a href={`tel:${success.vehicle.phone}`}>{success.vehicle.phone}</a></p><p>Nhà xe Thanh Tĩnh: <a href={`tel:${success.contact_phone}`}>{success.contact_phone}</a></p></div><button onClick={() => { setSuccess(null); setError(''); }}>Đặt thêm vé</button></section> : current && <form onSubmit={book}><fieldset disabled={busy} className="booking-fieldset">
      <section className="panel ticket-bus"><h2><span className="step-number">2</span>Chọn giường của bạn</h2><p className="booking-help">Bấm vào ô ghi “Còn chỗ” để chọn. Mỗi khoang là một giường riêng cho 1 hoặc 2 người. Ô xám là hết chỗ.</p>
        {!current.cabins.length && <p>Chưa có chỗ mở bán cho ngày và chiều này. Vui lòng chọn ngày khác.</p>}
        <div className="ticket-decks">{[1, 2].map(floor => <div key={floor} className="ticket-deck"><h3>{floor === 1 ? 'Tầng dưới' : 'Tầng trên'}</h3><div className="ticket-cabins">{current.cabins.filter((item, index) => Number(item.label.match(/^([12])[AB]\d+$/)?.[1] ?? (index < Math.ceil(current.cabins.length / 2) ? 1 : 2)) === floor).map(item => <button type="button" key={item.label} aria-pressed={cabin === item.label} className={`ticket-cabin ${item.remaining === 0 ? 'occupied' : cabin === item.label ? 'chosen' : ''}`} disabled={!fresh || item.remaining === 0} onClick={() => setCabin(item.label)}><span>{item.label}</span><small>{item.remaining === 0 ? 'Hết chỗ' : cabin === item.label ? 'Đang chọn' : 'Còn chỗ'}</small></button>)}</div></div>)}</div>
        <label>Số người<select value={passengers} onChange={e => setPassengers(e.target.value)}><option value="1">1 người — {money(current.prices['1'])}</option><option value="2">2 người — {money(current.prices['2'])}</option></select></label>
      </section>
      <section className="panel ticket-bus"><h2><span className="step-number">3</span>Chọn điểm đón và trả</h2><div className="formGrid">{([['pickup', 'Điểm đón', current.pickups, pickup, setPickup], ['dropoff', 'Điểm trả', current.dropoffs, dropoff, setDropoff]] as const).map(([kind, title, options, selected, choose]) => {
        const stop = options.find(item => item.id === selected);
        return <div key={kind}><label>{title}<select required value={selected} onChange={e => choose(e.target.value)}><option value="">Chọn {title.toLowerCase()}</option>{options.map(item => <option key={item.id} value={item.id}>{item.name}{item.time ? ` · ${item.time} ${dateLabel(item.day)}` : ''}</option>)}<option value="custom">Địa chỉ khác đã thỏa thuận</option></select></label>
          {selected === 'custom' ? <label>Địa chỉ cụ thể<input name={`${kind}_custom`} required maxLength={250} /></label> : stop && <p>{stop.address}<br />{stop.time ? `${stop.time} ngày ${dateLabel(stop.day)} (dự kiến)` : 'Giờ sẽ được xác nhận với nhà xe'}{stop.transfer && ' · Xe trung chuyển'}</p>}</div>;
      })}</div></section>
      <section className="panel ticket-bus"><h2><span className="step-number">4</span>Thông tin của bạn</h2><div className="formGrid"><label>Họ tên<input name="name" required maxLength={100} autoComplete="name" /></label>
        <label>Số điện thoại để nhà xe gọi xác nhận<input name="contact" required type="tel" inputMode="tel" pattern="0[0-9]{8,10}" maxLength={11} autoComplete="tel" placeholder="Ví dụ: 0901234567" /></label>
        {user && <label>Ghi nhận thanh toán<select name="paid" defaultValue="no"><option value="no">Chưa thu tiền</option><option value="yes">Nhân viên đã thu đủ tiền</option></select></label>}
        <label className="wide">Ghi chú / địa chỉ trung chuyển<input name="note" maxLength={300} /></label></div>
        <p><strong>{cabin ? `Khoang ${cabin}` : 'Chưa chọn khoang'} · {money(current.prices[passengers])}</strong></p><p>Nhà xe lưu họ tên và số điện thoại để gọi xác nhận chuyến đi, sau đó nhân viên gửi tin nhắn cho bạn. {!user && 'Giữ chỗ 20 phút chờ nhà xe xác nhận; quá hạn chưa xác nhận hoặc thanh toán, chỗ sẽ được mở lại.'} Đặt vé chưa đồng nghĩa đã thanh toán.</p>
        {error && <p role="alert" className="ticket-message">{error}</p>}<button type="submit" disabled={!available}>{busy ? 'Đang xác nhận…' : 'Đặt vé — nhận mã xác nhận'}</button>
      </section>
    </fieldset></form>}
  </div>;
}
