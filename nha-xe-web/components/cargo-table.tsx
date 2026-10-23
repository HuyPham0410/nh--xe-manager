import type { Cargo, CargoAction, User } from '../lib/types';
import { branchName, money, paymentNames, statusNames } from '../lib/format';

export function CargoTable({ rows, user, busy, onAction }: {
  rows: Cargo[]; user: User; busy: boolean;
  onAction: (row: Cargo, action: CargoAction) => void;
}) {
  return <div className="tableWrap"><table>
    <thead><tr>{['Người nhận','Hàng gửi','Cước','Thanh toán','Nơi giao','Trạng thái','Thao tác'].map(title => <th key={title}>{title}</th>)}</tr></thead>
    <tbody>{rows.map(row => <tr key={row.id}>
      <td><strong>{row.receiver_name}</strong><small>{row.receiver_phone}</small><small>#{row.id} · Nhận: {row.date}</small><small>Ngày đi: {row.scheduled_date}</small>{row.vehicle && <small>Xe: {row.vehicle}</small>}{row.scheduled_date !== row.date && <small>Đã chuyển ngày</small>}</td>
      <td>{row.goods_description}<small>SL: {row.quantity} · {branchName(row.branch)} → {branchName(row.branch === 'SG' ? 'TK' : 'SG')}</small>{row.note && <small>{row.note}</small>}</td>
      <td>{money(row.fee)}</td><td><span className="badge">{row.collected_at ? 'Đã thu' : paymentNames[row.payment]}</span></td>
      <td>{row.delivery_place}</td><td><span className={`badge ${row.status}`}>{statusNames[row.status]}</span></td>
      <td>{row.status === 'waiting' && (user.role === 'admin' || user.branch === row.branch) && <button disabled={busy} className="secondary" onClick={() => onAction(row,'defer')}>Xe đầy — chuyển ngày kế</button>}{(user.role === 'admin' || user.branch !== row.branch) && <>
        {row.status === 'waiting' && <button disabled={busy} className="secondary" onClick={() => onAction(row,'arrived')}>Đã tới</button>}
        {!row.collected_at && <button disabled={busy} className="secondary" onClick={() => onAction(row,'collect')}>Thu tiền</button>}
        {row.status === 'arrived' && <button disabled={busy} className="secondary" onClick={() => onAction(row,'delivered')}>Đã giao</button>}
      </>}</td>
    </tr>)}{rows.length === 0 && <tr><td colSpan={7}>Chưa có đơn phù hợp. Bấm “Nhận hàng” để ghi đơn đầu tiên.</td></tr>}</tbody>
  </table></div>;
}
