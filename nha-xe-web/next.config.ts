import type { NextConfig } from 'next';

// Trình duyệt gọi cùng origin /api. Chỉ máy chủ Next biết địa chỉ backend.
const config: NextConfig = {
  turbopack: { root: process.cwd() },
  async rewrites() {
    // Production builds save this destination; rebuild after changing the port.
    return [{ source: '/api/:path*', destination: `${process.env.BACKEND_URL || 'http://127.0.0.1:8765'}/api/:path*` }];
  },
};

export default config;
