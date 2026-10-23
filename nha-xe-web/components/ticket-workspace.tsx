'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, errorMessage } from '../lib/api';
import { branchName, money } from '../lib/format';
import type { Branch, User } from '../lib/types';

type Stop = { id: string; name: string; address: string; time: string; day: string; transfer: boolean };
type Ticket = { id: number; cabin: string; passengers: number; price: number; name: string; phone: string; email: string; confirmed_at: string; messages: { id: number; event: string; status: string; error: string; channel: string; body: string }[]; paid_at: string | null; cancelled_at: string | null; pickup: Stop | null; dropoff: Stop | null; note: string };
type SalesBus = { id: number; version: number; name: string; phone: string; active: number; tk_parity: 'even' | 'odd' | 'none'; cabins: string[]; direction: 'TK' | 'SG' | 'OFF'; override: string; can_sell: boolean; occupied: string[]; tickets: Ticket[] };
type Listing = { contact_phone: string; day: string; origin: Branch; buses: SalesBus[]; prices: Record<string, number>; updated_at: string; pickups: Stop[]; dropoffs: Stop[] };
type Change = (path: string, payload: object) => Promise<boolean>;
const sampleCabins = [1, 2].flatMap(floor => Array.from({ length: 6 }, (_, i) => [`${floor}A${i + 1}`, `${floor}B${i + 1}`]).flat());
const displayDay = (value: string) => value.split('-').reverse().join('/');

function StopInfo({ stop }: { stop: Stop | null }) {
  if (!stop) return <span>Chưa ghi điểm</span>;
  return <><strong>{stop.name}</strong><small>{stop.address}</small><small>{stop.time ? `${stop.time} · ${displayDay(stop.day)} (dự kiến)` : 'Giờ đón/trả cần xác nhận'}{stop.transfer && ' · Xe trung chuyển'}</small></>;
}

function BusSettings({ bus, day, busy, change, close }: { bus: SalesBus; day: string; busy: boolean; change: Change; close: () => void }) {
  const [cabins, setCabins] = useState(bus.cabins.join(', '));
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  async function config(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    if (await change('config', { id: bus.id, version: bus.version, active: fields.get('active') === 'true', tk_parity: fields.get('tk_parity'), cabins: cabins.split(/[\s,;]+/).filter(Boolean) })) close();
  }
  async function exception(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const fields = new FormData(event.currentTarget);
    if (await change('day', { id: bus.id, version: bus.version, day, origin: fields.get('origin') })) close();
  }
  return <section className="panel ticket-editor"><h2 ref={heading} tabIndex={-1}>Điều hành {bus.name}</h2>
    <p>Cho xe nghỉ sẽ ngừng bán mới, giữ nguyên vé đã bán để quản lý liên hệ khách. Đổi chiều hoặc xóa khoang có vé sẽ bị chặn.</p>
    <form onSubmit={config}><fieldset disabled={busy}><div className="formGrid">
      <label>Trạng thái chung<select name="active" defaultValue={bus.active ? 'true' : 'false'}><option value="true">Hoạt động</option><option value="false">Nghỉ / ngừng mở bán</option></select></label>
      <label>Lịch xuất phát từ Quảng Nam / Tam Kỳ<select name="tk_parity" defaultValue={bus.tk_parity}><option value="even">Ngày chẵn (ngày lẻ từ Sài Gòn)</option><option value="odd">Ngày lẻ (ngày chẵn từ Sài Gòn)</option><option value="none">Chưa có lịch thường lệ</option></select></label>
      <label className="wide">Mã khoang, cách nhau bằng dấu phẩy<textarea value={cabins} maxLength={600} onChange={e => setCabins(e.target.value)} rows={3} placeholder="1A1, 1B1, 1A2, 1B2, …" /></label>
    </div><p>Mã 1A/1B thuộc tầng dưới, 2A/2B thuộc tầng trên. Với mã khác, danh sách được chia đôi theo thứ tự. Xác nhận số khoang thật trước khi lưu.</p>
      <div className="fleet-actions"><button type="button" className="secondary" onClick={() => setCabins(sampleCabins.join(', '))}>Điền mẫu 24 khoang như ảnh</button><button type="submit">Lưu cấu hình xe</button></div>
    </fieldset></form>
    <hr /><form onSubmit={exception}><fieldset disabled={busy}><label>Riêng ngày {displayDay(day)}<select name="origin" defaultValue={bus.override}><option value="auto">Theo lịch chẵn/lẻ</option><option value="TK">Xuất phát Quảng Nam / Tam Kỳ</option><option value="SG">Xuất phát Sài Gòn</option><option value="OFF">Nghỉ ngày này</option></select></label>
      <p>Lịch riêng không mở bán nếu trạng thái chung của xe đang nghỉ.</p><button type="submit">Lưu lịch ngày này</button></fieldset></form>
    <button className="secondary" disabled={busy} onClick={close}>Đóng</button>
  </section>;
}

function BookingForm({ bus, cabin, data, busy, available, change, close }: { bus: SalesBus; cabin: string; data: Listing; busy: boolean; available: boolean; change: Change; close: () => void }) {
  const [passengers, setPassengers] = useState('1');
  const [pickup, setPickup] = useState('');
  const [dropoff, setDropoff] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  const request = useRef({ signature: '', id: '' });
  useEffect(() => { heading.current?.focus(); }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const payload = { bus_id: bus.id, day: data.day, origin: data.origin, cabin, passengers: Number(passengers), name: form.get('name'), phone: form.get('phone'), paid: form.get('paid') === 'yes', pickup_id: pickup, dropoff_id: dropoff, pickup_custom: form.get('pickup_custom') ?? '', dropoff_custom: form.get('dropoff_custom') ?? '', note: form.get('note') };
    const signature = JSON.stringify(payload);
    if (request.current.signature !== signature) request.current = { signature, id: crypto.randomUUID() };
    if (await change('book', { ...payload, request_id: request.current.id })) close();
  }
  return <section className="panel ticket-editor"><h2 ref={heading} tabIndex={-1}>Đặt khoang {cabin} · {bus.name}</h2><p>{branchName(data.origin)} → {branchName(data.origin === 'SG' ? 'TK' : 'SG')} · {displayDay(data.day)}</p>
    {!available && <p role="alert">Khoang đã có người đặt hoặc xe đã ngừng bán. Chọn khoang khác / tải lại trước khi tiếp tục.</p>}
    <form onSubmit={submit}><fieldset disabled={busy}><div className="formGrid">
      <label>Số người trong khoang<select value={passengers} onChange={event => setPassengers(event.target.value)}><option value="1">1 người — {money(data.prices['1'])}</option><option value="2">2 người — {money(data.prices['2'])}</option></select></label>
      <label>Thanh toán<select name="paid" defaultValue="no"><option value="no">Chưa thu tiền</option><option value="yes">Đã thu đủ tiền</option></select></label>
      <label>Tên khách / người đại diện<input name="name" required maxLength={100} autoComplete="name" /></label><label>Số điện thoại<input name="phone" type="tel" inputMode="numeric" required pattern="0[0-9]{8,10}" maxLength={11} autoComplete="tel" /></label>
      {([['pickup', 'Điểm đón', data.pickups, pickup, setPickup], ['dropoff', 'Điểm trả', data.dropoffs, dropoff, setDropoff]] as const).map(([kind, title, options, selected, setSelected]) => <div key={kind}><label>{title}<select required value={selected} onChange={event => setSelected(event.target.value)}><option value="">Chọn {title.toLowerCase()}</option>{options.map(stop => <option key={stop.id} value={stop.id}>{stop.name}{stop.time ? ` · ${stop.time} ${displayDay(stop.day)}` : ' · Chưa có giờ'}</option>)}<option value="custom">Địa chỉ khác đã thỏa thuận</option></select></label>
        {selected === 'custom' ? <label>Địa chỉ cụ thể<input name={`${kind}_custom`} required maxLength={250} /></label> : selected && <div className="ticket-stop"><StopInfo stop={options.find(stop => stop.id === selected) ?? null} /></div>}
      </div>)}
      <label className="wide">Ghi chú / địa chỉ trung chuyển cụ thể / tên khách thứ hai<textarea name="note" maxLength={300} rows={2} /></label>
    </div><p>Giữ nguyên cả khoang cho vé này. Tổng tiền: <strong>{money(data.prices[passengers])}</strong>. Khoản thu được ghi vào chi nhánh xuất phát khi xác nhận đã thu.</p>
      <div className="fleet-actions"><button type="submit" disabled={!available}>{busy ? 'Đang lưu…' : 'Xác nhận bán vé'}</button><button type="button" className="secondary" onClick={close}>Hủy thao tác</button></div>
    </fieldset></form>
  </section>;
}

export function TicketWorkspace({ user, onExpired }: { user: User; onExpired: () => void }) {
  const [day, setDay] = useState(user.today);
  const [origin, setOrigin] = useState<Branch>(user.branch);
  const [data, setData] = useState<Listing | null>(null);
  const [revision, setRevision] = useState(0);
  const [fresh, setFresh] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [connection, setConnection] = useState('Đang tải…');
  const [selected, setSelected] = useState<{ bus: SalesBus; cabin: string } | null>(null);
  const [editing, setEditing] = useState<SalesBus | null>(null);
  const admin = user.role === 'admin';
  const canSell = admin || user.branch === origin;

  useEffect(() => {
    const controller = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    setFresh(false);
    async function load() {
      try {
        const value = await api<Listing>(`/tickets?${new URLSearchParams({ day, origin })}`, { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]) });
        if (!controller.signal.aborted) { setData(value); setFresh(true); setConnection(`Đã cập nhật ${value.updated_at.slice(11, 19)} · Tự tải mỗi 5 giây`); }
      } catch (error) {
        if (!controller.signal.aborted) { setFresh(false); setConnection(`Chưa cập nhật: ${errorMessage(error)}. Tạm khóa bán vé.`); if (error instanceof ApiError && error.status === 401) onExpired(); }
      } finally { if (!controller.signal.aborted) timer = setTimeout(load, 5000); }
    }
    void load();
    function focus() { setRevision(value => value + 1); }
    window.addEventListener('focus', focus);
    return () => { controller.abort(); clearTimeout(timer); window.removeEventListener('focus', focus); };
  }, [day, origin, revision, onExpired]);

  async function change(path: string, payload: object) {
    setBusy(true); setMessage('');
    try {
      const result = await api<{ id?: number; price?: number }>(`/tickets/${path}`, { data: payload, csrf: user.csrf });
      setMessage(path === 'book' ? `Đã lưu vé #${result.id} · ${money(result.price ?? 0)}` : 'Đã lưu thay đổi.');
      return true;
    } catch (error) { setMessage(errorMessage(error)); if (error instanceof ApiError && error.status === 401) onExpired(); return false; }
    finally { setBusy(false); setFresh(false); setRevision(value => value + 1); }
  }
  async function cancel(ticket: Ticket) {
    const reason = window.prompt(`Lý do hủy vé #${ticket.id}:`);
    if (!reason?.trim()) return;
    if (!window.confirm(ticket.paid_at ? `Xác nhận đã hoàn đủ ${money(ticket.price)} cho khách? Hệ thống sẽ ghi khoản chi hoàn tiền và giải phóng khoang.` : `Hủy vé #${ticket.id} và giải phóng khoang?`)) return;
    await change('cancel', { id: ticket.id, reason, refund: !!ticket.paid_at });
  }
  function reset() { setData(null); setFresh(false); setSelected(null); setEditing(null); setMessage(''); }
  const current = data?.day === day && data.origin === origin ? data : null;
  const chosenBus = current?.buses.find(bus => bus.id === selected?.bus.id);
  const selectedAvailable = !!(fresh && canSell && chosenBus?.can_sell && selected && chosenBus.cabins.includes(selected.cabin) && !chosenBus.occupied.includes(selected.cabin));

  return <>
    <div className="heading"><div><span className="eyebrow">Dành cho nhân viên và quản lý</span><h1>Sổ vé nội bộ</h1><p>Thu tiền, xử lý vé, kiểm tra xác nhận và điều hành lịch chạy.</p><a href="/dat-ve" target="_blank" rel="noreferrer">Mở trang đặt vé cho khách</a></div></div>
    <section className="panel"><div className="tools"><label>Ngày xuất phát<input type="date" required value={day} disabled={busy} onChange={event => { if (event.target.value) { reset(); setDay(event.target.value); } }} /></label>
      <label>Xuất phát từ<select value={origin} disabled={busy} onChange={event => { reset(); setOrigin(event.target.value as Branch); }}><option value="TK">Quảng Nam / Tam Kỳ</option><option value="SG">Sài Gòn</option></select></label><button className="secondary" disabled={busy} onClick={() => setRevision(value => value + 1)}>Tải lại</button></div>
      <p role="status">{connection}</p><p>Lịch chẵn/lẻ theo ngày trong tháng. Ngày 31 rồi ngày 1 đều là ngày lẻ; quản lý kiểm tra và chỉnh lịch riêng khi cần.</p>
      {!canSell && <p>Bạn đang xem chiều ngược lại. Nhân viên bán vé tại chi nhánh của mình.</p>}
      <p>Giờ tại các điểm là dự kiến. Ngày đi tính theo ngày xuất phát, kể cả điểm trả sau nửa đêm.</p>
    </section>
    {current && <section className="panel ticket-bus"><h2>Số liên hệ xác nhận</h2><p><a href={`tel:${current.contact_phone}`}>{current.contact_phone}</a> · Nhân viên dùng SIM này để gọi và gửi SMS.</p>{admin && <form onSubmit={event => { event.preventDefault(); void change('contact', {phone: new FormData(event.currentTarget).get('phone')}); }}><label>Số điện thoại nhà xe<input key={current.contact_phone} name="phone" type="tel" required pattern="0[0-9]{8,10}" maxLength={11} defaultValue={current.contact_phone}/></label><button disabled={busy}>Lưu số liên hệ</button></form>}<p>Mở tin nhắn trên điện thoại có SIM nhà xe, chọn đúng SIM trước khi gửi. Website không tự gửi SMS.</p></section>}
    <p className="ticket-message" role="status">{message}</p>
    {editing && <BusSettings key={`${editing.id}-${editing.version}-${day}`} bus={editing} day={day} busy={busy} change={change} close={() => setEditing(null)} />}
    {selected && current && <BookingForm key={`${selected.bus.id}-${selected.cabin}-${day}-${origin}`} bus={selected.bus} cabin={selected.cabin} data={current} busy={busy} available={selectedAvailable} change={change} close={() => setSelected(null)} />}
    {current?.buses.map(bus => {
      const validTickets = bus.tickets.filter(ticket => !ticket.cancelled_at);
      const matches = bus.direction === origin;
      return <section key={bus.id} className="panel ticket-bus"><div className="heading"><div><h2>{bus.name} · <a href={`tel:${bus.phone}`}>{bus.phone}</a></h2>
        <p>{!bus.active ? 'Xe đang nghỉ' : bus.direction === 'OFF' ? 'Nghỉ / chưa có lịch ngày này' : `Chạy từ ${branchName(bus.direction)}`} · {bus.occupied.length}/{bus.cabins.length} khoang đã đặt{bus.override !== 'auto' ? ' · Lịch riêng ngày này' : ''}</p></div>
        {admin && <button className="secondary" disabled={busy || !fresh} onClick={() => { setSelected(null); setEditing(bus); }}>Lịch xe / nghỉ / số khoang</button>}</div>
        {!bus.cabins.length && <p>Chưa cấu hình khoang. Admin mở cấu hình và nhập đúng sơ đồ xe trước khi bán.</p>}
        {(!bus.active || !matches) && validTickets.length > 0 && <p role="alert" className="ticket-warning">Có {validTickets.length} vé chưa hủy cần quản lý kiểm tra vì xe nghỉ hoặc lịch đã thay đổi. Vé không tự hủy.</p>}
        {matches && bus.cabins.length > 0 && <><p className="ticket-legend">Trống · Đã đặt (khóa) · Đang chọn. Chọn khoang rồi chọn 1 hoặc 2 người.</p><div className="ticket-decks">{[1, 2].map(floor => <div key={floor} className="ticket-deck"><h3>{floor === 1 ? 'Tầng dưới' : 'Tầng trên'}</h3><div className="ticket-cabins">{bus.cabins.filter((label, index) => Number(label.match(/^([12])[AB]\d+$/)?.[1] ?? (index < Math.ceil(bus.cabins.length / 2) ? 1 : 2)) === floor).map(cabin => {
          const occupied = bus.occupied.includes(cabin); const chosen = selected?.bus.id === bus.id && selected.cabin === cabin;
          return <button key={cabin} className={`ticket-cabin ${occupied ? 'occupied' : chosen ? 'chosen' : ''}`} aria-pressed={chosen} disabled={busy || !fresh || !canSell || !bus.can_sell || occupied} onClick={() => { setEditing(null); setSelected({ bus, cabin }); setMessage(''); }}><span>{cabin}</span><small>{occupied ? 'Đã đặt' : chosen ? 'Đang chọn' : '1–2 người'}</small></button>;
        })}</div></div>)}</div></>}
        {bus.tickets.length > 0 && <><h3>Vé ngày {displayDay(day)} · {branchName(origin)}</h3><div className="tableWrap"><table><thead><tr><th>Vé / khoang</th><th>Khách</th><th>Điểm đón</th><th>Điểm trả</th><th>Tiền vé</th><th>Trạng thái / thao tác</th></tr></thead><tbody>{bus.tickets.map(ticket => <tr key={ticket.id}><td>#{ticket.id} · {ticket.cabin}<small>{ticket.passengers} người</small></td><td>{ticket.name}<small><a href={`tel:${ticket.phone}`}>{ticket.phone}</a></small><small>{ticket.email}</small><small>{ticket.note}</small></td><td><StopInfo stop={ticket.pickup} /></td><td><StopInfo stop={ticket.dropoff} /></td><td>{money(ticket.price)}</td><td>{ticket.confirmed_at && <small>Đã gọi xác nhận</small>}{ticket.cancelled_at ? 'Đã hủy' : ticket.paid_at ? 'Đã thu' : 'Chưa thu'}
          {!ticket.cancelled_at && !ticket.confirmed_at && canSell && <button disabled={busy || !fresh} onClick={() => { if(window.confirm('Đã gọi và khách đồng ý chuyến đi? Vé sẽ được giữ đến khi thu tiền hoặc quản lý hủy.')) void change('confirm-call',{id:ticket.id}); }}>Đã gọi xác nhận</button>}
          {!ticket.cancelled_at && !ticket.paid_at && canSell && <button disabled={busy || !fresh} onClick={() => { if (window.confirm(`Xác nhận đã thu đủ ${money(ticket.price)} cho vé #${ticket.id}?`)) void change('collect', { id: ticket.id }); }}>Thu tiền</button>}
          {!ticket.cancelled_at && admin && <button className="secondary" disabled={busy || !fresh} onClick={() => void cancel(ticket)}>Hủy vé{ticket.paid_at ? ' / hoàn tiền' : ''}</button>}
        {ticket.messages?.map(message => <div key={message.id}><small>{({ book: 'Đặt vé', paid: 'Thanh toán', cancel: 'Hủy vé', confirmed: 'Đã gọi xác nhận' } as Record<string,string>)[message.event]}: {({ pending: 'Chờ gửi', not_configured: 'Chưa cấu hình gửi', sending: 'Đang gửi', accepted: 'Dịch vụ đã nhận thư', failed: 'Gửi thất bại', unknown: 'Cần kiểm tra dịch vụ', skipped: 'Đã bỏ qua thông báo cũ' } as Record<string,string>)[message.status]}</small>{message.error && <small>{message.error}</small>}{message.channel === 'sms' && message.status !== 'skipped' && (!ticket.cancelled_at || message.event === 'cancel') && <details><summary>Nội dung SMS cho khách</summary><p style={{whiteSpace:'pre-line'}}>{message.body}</p><a href={`sms:${ticket.phone}?body=${encodeURIComponent(message.body)}`}>Mở SMS trên điện thoại</a><p>Chọn SIM {current.contact_phone} và tự bấm Gửi. Mở ứng dụng chưa có nghĩa tin đã được gửi.</p></details>}{admin && ['failed','unknown','not_configured'].includes(message.status) && <button className="secondary" disabled={busy || !fresh} onClick={() => { if (window.confirm('Đã kiểm tra cấu hình và xác nhận dịch vụ chưa gửi thư này?')) void change('retry-message', { id: message.id, checked_provider: true }); }}>Thử gửi lại</button>}</div>)}
        </td></tr>)}</tbody></table></div></>}
      </section>;
    })}
  </>;
}
