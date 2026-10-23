import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Nhà xe Thanh Tĩnh', description: 'Nhà xe Thanh Tĩnh — đặt vé Quảng Nam, Tam Kỳ và Sài Gòn.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="vi"><body>{children}</body></html>;
}
