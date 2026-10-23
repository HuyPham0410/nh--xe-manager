export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

// Một cửa gọi API: các component không cần lặp lại xử lý cookie, CSRF và lỗi.
// T chỉ mô tả kiểu dữ liệu khi lập trình; nó không validate JSON ở runtime.
export async function api<T>(path: string, options: {
  data?: unknown; csrf?: string; signal?: AbortSignal;
} = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method: options.data === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: options.data === undefined ? {} : {
      'Content-Type': 'application/json', 'X-CSRF-Token': options.csrf ?? '',
    },
    body: options.data === undefined ? undefined : JSON.stringify(options.data),
    signal: options.signal,
  });
  const result = await response.json().catch(() => null);
  if (!response.ok || result === null) {
    throw new ApiError(result?.error ?? 'Không kết nối được máy chủ. Kiểm tra backend đang chạy.', response.status);
  }
  return result as T;
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Đã xảy ra lỗi, vui lòng thử lại.';
}
