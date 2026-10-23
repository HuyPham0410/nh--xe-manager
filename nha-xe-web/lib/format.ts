export const money = (amount: number) => new Intl.NumberFormat('vi-VN').format(amount) + ' đ';
export const branchName = (branch: string) => branch === 'SG' ? 'Sài Gòn' : 'Tam Kỳ';
export const paymentNames = { paid: 'Đã trả', destination: 'Trả đầu kia', debt: 'Cho nợ' };
export const statusNames = { waiting: 'Chờ đi', arrived: 'Đã tới', delivered: 'Đã giao' };
