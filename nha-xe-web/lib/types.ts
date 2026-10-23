// Union types giúp phát hiện lỗi như gõ nhầm "arrived" ngay khi viết code.
export type Branch = 'SG' | 'TK';
export type Payment = 'paid' | 'destination' | 'debt';
export type CargoStatus = 'waiting' | 'arrived' | 'delivered';
export type CargoAction = 'arrived' | 'delivered' | 'collect' | 'defer';

export interface User {
  username: string;
  branch: Branch;
  role: 'admin' | 'staff';
  csrf: string;
  today: string;
}

export interface CargoInput {
  receiver_phone: string;
  receiver_name: string;
  goods_description: string;
  quantity: number;
  fee: number;
  payment: Payment;
  delivery_place: string;
  note: string;
}

export interface Cargo extends CargoInput {
  id: number;
  date: string;
  scheduled_date: string;
  vehicle: string;
  branch: Branch;
  status: CargoStatus;
  collected_at: string | null;
}

export interface CargoList { rows: Cargo[]; truncated: boolean }
export interface Report {
  count: number;
  total: number;
  collected: number;
  destination: number;
  debt: number;
  audit: { id: number; cargo_id: number; username: string; action: string; at: string }[];
}
