'use client';

import { useEffect, useState } from 'react';
import { api, errorMessage } from '../lib/api';
import { branchName, money } from '../lib/format';
import type { Branch, Report } from '../lib/types';

export function DailyReport({ date, branch, revision }: { date: string; branch: Branch | ''; revision: number }) {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController(); setReport(null); setError('');
    api<Report>(`/report?${new URLSearchParams({ date, branch })}`, { signal: controller.signal })
      .then(setReport).catch(error => { if (!controller.signal.aborted) setError(errorMessage(error)); });
    return () => controller.abort();
  }, [date, branch, revision]);

  if (error) return <p role="alert">{error}</p>;
  if (!report) return <p role="status">Đang tính tổng…</p>;
  const metrics = [['Đơn nhận', report.count], ['Tổng cước', money(report.total)],
    ['Thực thu cước hàng', money(report.collected)], ['Đầu kia chưa thu', money(report.destination)], ['Nợ chưa thu', money(report.debt)]];
  return <section><div className="metrics">{metrics.map(([title,value]) => <div key={title} className="metric"><span>{title}</span><strong>{value}</strong></div>)}</div>
    <p>{branch ? `Đơn nhận, cước, nợ và CSV tính cho hàng gửi từ ${branchName(branch)}. Thực thu là tiền thu tại ${branchName(branch)}, bao gồm hàng đến từ đầu kia.` : 'Tổng hợp hàng và tiền của cả hai chi nhánh.'} Dư chưa thu tính theo tình trạng hiện tại của đơn nhận ngày {date}.</p>
    <div className="panel"><a href={`/api/export?${new URLSearchParams({ date, branch })}`}>Xuất CSV mở bằng Excel</a>
      <h2>Lịch sử 100 thao tác gần nhất{branch ? ` của hàng gửi từ ${branchName(branch)}` : ''}</h2>
      {report.audit.map(item => <div key={item.id} className="auditRow">Đơn #{item.cargo_id} · {item.username} · {({ arrived:'Đã tới', delivered:'Đã giao', collect:'Thu tiền', defer:'Xe đầy — chuyển sang ngày kế' } as Record<string,string>)[item.action] ?? item.action}<small>{item.at}</small></div>)}
    </div></section>;
}

