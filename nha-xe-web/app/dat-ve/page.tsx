import { SimpleBooking } from '../../components/simple-booking';

export default function BookingPage() {
  return <><header className="public-header"><a className="brand" href="/dat-ve"><span className="brand-mark" aria-hidden="true">TT</span><span>NHÀ XE THANH TĨNH<small>Quảng Nam · Tam Kỳ · Sài Gòn</small></span></a><span className="header-note">Đặt vé trực tuyến</span></header><main><SimpleBooking /></main><footer className="site-footer"><strong>Nhà xe Thanh Tĩnh</strong><p>Văn phòng Sài Gòn: 121 Nguyễn Hữu Tiến, Phường Tây Thạnh, Hồ Chí Minh</p><p>Văn phòng Quảng Nam: 35 Hà Huy Tập, Phường Bàn Thạch, Đà Nẵng</p><a href="/">Dành cho nhân viên nhà xe →</a></footer></>;
}
