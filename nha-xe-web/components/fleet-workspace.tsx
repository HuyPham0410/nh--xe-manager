'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { api, ApiError, errorMessage } from '../lib/api';
import type { User } from '../lib/types';

type Employee = { id: number; name: string; phone: string; role: 'driver' | 'assistant'; active: number; version: number };
type Slot = 'driver1' | 'driver2' | 'assistant1' | 'assistant2';
type Bus = { id: number; name: string; phone: string; plate: string; version: number; crew: Partial<Record<Slot, number>> };
type Fleet = { buses: Bus[]; employees: Employee[] };
type Editor = { kind: 'employee'; value: Employee | null } | { kind: 'bus'; value: Bus } | { kind: 'crew'; value: Bus };
const slots: [Slot, string][] = [['driver1', 'Lái xe 1'], ['driver2', 'Lái xe 2'], ['assistant1', 'Phụ xe 1'], ['assistant2', 'Phụ xe 2']];

export function FleetWorkspace({ user, onExpired }: { user: User; onExpired: () => void }) {
  const [data, setData] = useState<Fleet | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [query, setQuery] = useState('');
  const editorHeading = useRef<HTMLHeadingElement>(null);
  const admin = user.role === 'admin';
  useEffect(() => { if (editor) editorHeading.current?.focus(); }, [editor]);

  useEffect(() => {
    const controller = new AbortController();
    api<Fleet>('/fleet', { signal: controller.signal }).then(setData).catch(error => {
      if (!controller.signal.aborted) {
        setMessage(errorMessage(error));
        if (error instanceof ApiError && error.status === 401) onExpired();
      }
    });
    return () => controller.abort();
  }, [onExpired]);

  async function reload() {
    setBusy(true);
    try { setData(await api<Fleet>('/fleet')); setEditor(null); setMessage('Đã tải lại danh sách.'); }
    catch (error) { setMessage(errorMessage(error)); if (error instanceof ApiError && error.status === 401) onExpired(); }
    finally { setBusy(false); }
  }

  async function save(kind: Editor['kind'], payload: object) {
    setBusy(true); setMessage('');
    try {
      await api(`/fleet/${kind}`, { data: payload, csrf: user.csrf });
      setEditor(null);
      try { setData(await api<Fleet>('/fleet')); setMessage('Đã lưu thay đổi.'); }
      catch { setData(null); setMessage('Đã lưu, nhưng chưa tải được danh sách mới. Bấm Tải lại.'); }
    } catch (error) { setMessage(errorMessage(error)); if (error instanceof ApiError && error.status === 401) onExpired(); }
    finally { setBusy(false); }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editor) return;
    const fields = new FormData(event.currentTarget);
    const identity = editor.value ? { id: editor.value.id, version: editor.value.version } : {};
    if (editor.kind === 'crew') {
      const crew = Object.fromEntries(slots.map(([slot]) => [slot, Number(fields.get(slot))]));
      void save('crew', { ...identity, crew });
    } else {
      void save(editor.kind, { ...identity, name: fields.get('name'), phone: fields.get('phone'),
        ...(editor.kind === 'bus' ? { plate: fields.get('plate') } : { role: fields.get('role'), active: fields.get('active') === 'true' }) });
    }
  }

  const employees = data?.employees ?? [];
  const visible = employees.filter(employee => `${employee.name} ${employee.phone}`.toLocaleLowerCase('vi').includes(query.toLocaleLowerCase('vi')));
  return <>
    <div className="heading"><div><span className="eyebrow">Quản lý nhà xe</span><h1>Xe & nhân viên</h1><p>Mỗi xe gồm 2 lái và 2 phụ. Số điện thoại giúp nhận diện và liên hệ từng xe.</p></div>
      <button className="secondary" disabled={busy} onClick={reload}>Tải lại</button></div>
    <p role="status" className="fleet-message">{message || (!data ? 'Đang tải danh sách…' : '')}</p>
    {data && <>
      <div className="fleet-grid">{data.buses.map(bus => <section className="panel fleet-card" key={bus.id}>
        <h2>{bus.name}</h2><a href={`tel:${bus.phone}`}>{bus.phone}</a><p>Biển số: {bus.plate || 'Chưa bổ sung'}</p>
        <strong>{Object.keys(bus.crew).length === 4 ? 'Đủ 2 lái + 2 phụ' : 'Chưa phân công'}</strong>
        <dl>{slots.map(([slot, label]) => { const employee = employees.find(person => person.id === bus.crew[slot]); return <div key={slot}><dt>{label}</dt><dd>{employee ? <>{employee.name}<br /><a href={`tel:${employee.phone}`}>{employee.phone}</a></> : 'Chưa phân công'}</dd></div>; })}</dl>
        {admin && <div className="fleet-actions"><button disabled={busy} onClick={() => setEditor({ kind: 'crew', value: bus })}>Phân công</button><button disabled={busy} className="secondary" onClick={() => setEditor({ kind: 'bus', value: bus })}>Sửa xe</button></div>}
      </section>)}</div>
      {admin && editor && <section className="panel fleet-editor" aria-label="Biểu mẫu quản lý"><h2 ref={editorHeading} tabIndex={-1}>{editor.kind === 'crew' ? `Phân công ${editor.value.name}` : editor.kind === 'bus' ? `Sửa ${editor.value.name}` : editor.value ? 'Sửa nhân viên' : 'Thêm nhân viên'}</h2>
        <form key={`${editor.kind}-${editor.value?.id ?? 'new'}-${editor.value?.version ?? 0}`} onSubmit={submit}><fieldset disabled={busy}><div className="formGrid">
          {editor.kind === 'crew' ? slots.map(([slot, label]) => <label key={slot}>{label}<select name={slot} required defaultValue={editor.value.crew[slot] ?? ''}>
            <option value="">Chọn nhân viên</option>{employees.filter(person => person.active && person.role === (slot.startsWith('driver') ? 'driver' : 'assistant')).map(person => {
              const other = data.buses.find(bus => bus.id !== editor.value.id && Object.values(bus.crew).includes(person.id));
              return <option key={person.id} value={person.id} disabled={!!other}>{person.name} · {person.phone}{other ? ` · Đang ở ${other.name}` : ''}</option>;
            })}</select></label>) : <>
            <label>{editor.kind === 'bus' ? 'Tên xe' : 'Họ tên'}<input name="name" required maxLength={100} defaultValue={editor.value?.name ?? ''} /></label>
            <label>Số điện thoại<input name="phone" type="tel" inputMode="numeric" pattern="0[0-9]{8,10}" required maxLength={11} defaultValue={editor.value?.phone ?? ''} /></label>
            {editor.kind === 'bus' ? <label>Biển số<input name="plate" maxLength={20} defaultValue={editor.value.plate} /></label> : <>
              <label>Vai trò<select name="role" defaultValue={editor.value?.role ?? 'driver'}><option value="driver">Lái xe</option><option value="assistant">Phụ xe</option></select></label>
              <label>Trạng thái<select name="active" defaultValue={editor.value?.active === 0 ? 'false' : 'true'}><option value="true">Đang làm việc</option><option value="false">Đã nghỉ</option></select></label>
            </>}
          </>}
        </div>{message && <p role="alert">{message}</p>}<div className="fleet-actions"><button type="submit">{busy ? 'Đang lưu…' : 'Lưu'} </button><button type="button" className="secondary" onClick={() => setEditor(null)}>Hủy</button>
          {editor.kind === 'crew' && Object.keys(editor.value.crew).length > 0 && <button type="button" className="secondary" onClick={() => { if (window.confirm(`Bỏ toàn bộ phân công của ${editor.value.name}?`)) void save('crew', { id: editor.value.id, version: editor.value.version, crew: {} }); }}>Bỏ phân công</button>}
        </div></fieldset></form>
      </section>}
      <section className="panel fleet-employees"><div className="heading"><div><h2>Nhân viên nhà xe</h2><p>{employees.filter(person => person.active).length} người đang làm việc · Cần 6 lái và 6 phụ để đủ tổ cho 3 xe.</p></div>{admin && <button disabled={busy} onClick={() => setEditor({ kind: 'employee', value: null })}>+ Thêm nhân viên</button>}</div>
        <label>Tìm tên hoặc SĐT<input type="search" value={query} onChange={event => setQuery(event.target.value)} /></label>
        <p>Đây là hồ sơ nhân viên và phân công hiện tại, chưa phải lịch theo chuyến hoặc tài khoản đăng nhập. {admin ? 'Thêm nhân viên thật trước khi phân công xe.' : 'Liên hệ quản lý để cập nhật phân công.'}</p>
        {!visible.length ? <p>Chưa có nhân viên phù hợp.</p> : <div className="tableWrap"><table><thead><tr><th>Họ tên</th><th>SĐT</th><th>Vai trò</th><th>Xe</th><th>Trạng thái</th>{admin && <th>Thao tác</th>}</tr></thead><tbody>{visible.map(person => <tr key={person.id}><td>{person.name}</td><td><a href={`tel:${person.phone}`}>{person.phone}</a></td><td>{person.role === 'driver' ? 'Lái xe' : 'Phụ xe'}</td><td>{data.buses.find(bus => Object.values(bus.crew).includes(person.id))?.name ?? 'Chưa phân công'}</td><td>{person.active ? 'Đang làm việc' : 'Đã nghỉ'}</td>{admin && <td><button className="secondary" disabled={busy} onClick={() => setEditor({ kind: 'employee', value: person })}>Sửa</button></td>}</tr>)}</tbody></table></div>}
      </section>
    </>}
  </>;
}
