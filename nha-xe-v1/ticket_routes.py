"""Điểm đón/trả do nhà xe cung cấp; giờ là dự kiến, không suy diễn chiều về."""
from datetime import date, timedelta

SG_PICKUPS = [
    ('sg-office', 'Văn phòng Sài Gòn', '121 Nguyễn Hữu Tiến, Phường Tây Thạnh, Hồ Chí Minh', '', 0),
    ('an-suong', 'Ngã Tư An Sương', 'Ngã Tư An Sương, Hóc Môn, Hồ Chí Minh', '13:10', 0),
    ('nga-tu-ga', 'Ngã tư Ga', 'Ngã Tư Ga, Phường An Phú Đông, Hồ Chí Minh', '13:20', 0),
    ('quan-12', 'Quận 12', 'Quận 12, Phường Tân Thới Hiệp, Hồ Chí Minh', '13:20', 0),
    ('cho-thu-duc', 'Chợ đầu mối Thủ Đức', '180 QL1A, Phường Tam Bình, Hồ Chí Minh', '13:30', 0),
    ('binh-phuoc', 'Ngã tư Bình Phước', 'Ngã tư Bình Phước, Thủ Đức, Hồ Chí Minh', '13:30', 0),
    ('suoi-tien', 'Suối Tiên', '120 XL Hà Nội, Thủ Đức, Hồ Chí Minh', '14:00', 0),
    ('song-than', 'Cầu vượt Sóng Thần', 'Quốc Lộ 1A, Phường An Bình, Dĩ An, Bình Dương', '14:15', 0),
    ('thu-duc', 'Thủ Đức', 'Thủ Đức, Hồ Chí Minh', '14:15', 0),
    ('linh-xuan', 'Cầu vượt Linh Xuân', 'Cầu vượt Linh Xuân, Phường Linh Xuân, Hồ Chí Minh', '14:15', 0),
    ('vung-tau', 'Ngã ba Vũng Tàu', 'Kp10 An Bình, Thành phố Biên Hòa, Phường Trấn Biên, Đồng Nai', '14:30', 0),
    ('cong-11', 'Cổng 11', 'Cổng 11, Phường Long Hưng, Đồng Nai', '14:30', 0),
]
QN_DROPOFFS = [
    ('hoi-an', 'Trung chuyển nội thành Hội An', 'Nội thành Hội An, Phường Minh An, Hội An, Quảng Nam', '02:00', 1),
    ('tam-ky', 'Tam Kỳ', 'Tam Kỳ, Quảng Nam', '23:50', 0),
    ('ky-ly', 'Kỳ Lý', 'Kỳ Lý, Tam Kỳ, Quảng Nam', '00:00', 1),
    ('tam-phuoc', 'Tam Phước', 'Tam Phước, Phú Ninh, Quảng Nam', '00:20', 1),
    ('phu-ninh', 'Phú Ninh', 'Phú Ninh, Quảng Nam', '00:30', 1),
    ('tam-dan', 'Tam Dân', 'Tam Dân, Phú Ninh, Quảng Nam', '00:40', 1),
    ('suoi-da', 'Suối Đá', 'Suối Đá, Xã Tam Dân, Phú Ninh, Quảng Nam', '00:45', 1),
    ('tien-tho', 'Tiên Thọ', 'Tiên Thọ, Tiên Phước, Quảng Nam', '01:00', 1),
    ('tien-ky', 'Tiên Kỳ', 'Tiên Kỳ, Xã Tiên Phước, Đà Nẵng', '01:10', 1),
    ('tien-chau', 'Tiên Châu', 'Tiên Châu, Xã Sơn Cẩm Hà, Đà Nẵng', '01:30', 1),
    ('cu-huynh', 'Cụ Huỳnh', 'Cụ Huỳnh, Xã Tiên Cảnh, Tiên Phước, Quảng Nam', '01:50', 1),
    ('tien-hiep', 'Tiên Hiệp', 'Tiên Hiệp, Tiên Phước, Quảng Nam', '02:00', 1),
    ('qn-office', 'Văn phòng Quảng Nam', '35 Hà Huy Tập, Phường Bàn Thạch, Đà Nẵng', '02:20', 1),
]
QN_PICKUPS = [
    ('hoi-an', 'Trung chuyển nội thành Hội An', 'Nội thành Hội An, Phường Minh An, Hội An, Quảng Nam', '13:30', 0),
    ('tam-thanh-transfer', 'Tam Thành (trung chuyển)', 'Tam Thành, Xã Tam Thanh, Tam Kỳ, Quảng Nam', '15:00', 0),
    ('duy-hai', 'Duy Hải', 'Trạm Y Tế xã Duy Hải, Xã Duy Nghĩa, Đà Nẵng', '11:30', 0),
    ('nam-phuoc', 'Ngã 3 Nam Phước Duy Xuyên', 'Xã Nam Phước, Đà Nẵng', '11:30', 0),
    ('binh-hai', 'Bình Hải', 'Xã Bình Hải, Thăng Bình, Quảng Nam', '12:00', 0),
    ('binh-sa', 'Bình Sa', 'Xã Bình Sa, Thăng Bình, Quảng Nam', '12:15', 0),
    ('binh-dao', 'Bình Đào', 'Bình Đào, Thăng Bình, Quảng Nam, Xã Thăng An, Đà Nẵng', '12:15', 0),
    ('quan-go', 'Quán Gò', 'Quán Gò, Xã Thăng Điền, Đà Nẵng', '12:30', 0),
    ('tam-thanh', 'Tam Thành (đón trực tiếp)', 'Tam Thành, Xã Tam Thanh, Tam Kỳ, Quảng Nam', '12:45', 0),
    ('cua-dai', 'Cầu Cửa Đại (trung chuyển)', 'Quảng Nam, Xã Duy Nghĩa, Đà Nẵng', '13:30', 0),
    ('qn-office', 'Văn phòng Quảng Nam', '35 Hà Huy Tập, Phường Bàn Thạch, Đà Nẵng', '14:00', 0),
    ('tien-hiep', 'Tiên Hiệp', 'Tiên Hiệp, Tiên Phước, Quảng Nam', '14:00', 0),
    ('cu-huynh', 'Cụ Huỳnh', 'Cụ Huỳnh, Xã Tiên Cảnh, Tiên Phước, Quảng Nam', '14:10', 0),
    ('tien-chau', 'Tiên Châu', 'Tiên Châu, Xã Sơn Cẩm Hà, Đà Nẵng', '14:30', 0),
    ('tien-ky', 'Tiên Kỳ', 'Tiên Kỳ, Xã Tiên Phước, Đà Nẵng', '14:50', 0),
    ('tien-tho', 'Tiên Thọ', 'Tiên Thọ, Tiên Phước, Quảng Nam', '15:00', 0),
    ('suoi-da', 'Suối Đá', 'Suối Đá, Xã Tam Dân, Phú Ninh, Quảng Nam', '15:15', 0),
    ('tam-dan', 'Tam Dân', 'Tam Dân, Phú Ninh, Quảng Nam', '15:20', 0),
    ('phu-ninh', 'Phú Ninh', 'Phú Ninh, Quảng Nam', '15:30', 0),
    ('tam-phuoc', 'Tam Phước', 'Tam Phước, Phú Ninh, Quảng Nam', '15:40', 0),
    ('ky-ly', 'Kỳ Lý', 'Kỳ Lý, Tam Kỳ, Quảng Nam', '16:00', 0),
    ('tam-ky', 'Tam Kỳ', 'Tam Kỳ, Quảng Nam', '16:10', 0),
]
SG_DROPOFFS = [(key, next(row[1] for row in SG_PICKUPS if row[0] == key),
                next(row[2] for row in SG_PICKUPS if row[0] == key), time, 1)
               for key, time in [('sg-office', '03:20'), ('vung-tau', '06:30'), ('cong-11', '06:30'),
                                 ('song-than', '06:45'), ('thu-duc', '06:45'), ('linh-xuan', '06:45'),
                                 ('suoi-tien', '07:00'), ('cho-thu-duc', '07:30'), ('nga-tu-ga', '07:40'),
                                 ('quan-12', '07:40'), ('an-suong', '07:50')]]


def options(origin, day):
    pickups = SG_PICKUPS if origin == 'SG' else QN_PICKUPS
    dropoffs = QN_DROPOFFS if origin == 'SG' else SG_DROPOFFS
    def expand(rows):
        return [{'id': key, 'name': name, 'address': address, 'time': time,
                 'day': (date.fromisoformat(day)+timedelta(days=offset)).isoformat() if time else '',
                 'transfer': key in ('hoi-an', 'tam-thanh-transfer', 'cua-dai')} for key, name, address, time, offset in rows]
    return {'pickups': expand(pickups), 'dropoffs': expand(dropoffs)}


def selected(d, kind, origin, day):
    key = d.get(kind+'_id')
    if key == 'custom':
        address = d.get(kind+'_custom')
        if not isinstance(address, str) or not 1 <= len(address.strip()) <= 250:
            raise ValueError('Nhập địa chỉ đón / trả cụ thể, tối đa 250 ký tự')
        return {'id': 'custom', 'name': 'Điểm đã thỏa thuận', 'address': address.strip(), 'time': '', 'day': '', 'transfer': False}
    item = next((item for item in options(origin, day)['pickups' if kind == 'pickup' else 'dropoffs'] if item['id'] == key), None)
    if item is None:
        raise ValueError('Chọn điểm đón và điểm trả đúng chiều đi')
    return item
