export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  has_next: boolean;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: PaginationMeta;
  trace_id: string;
  timestamp: string;
}

export interface ApiError {
  success: false;
  error_code: string;
  message: string;
  details?: Record<string, unknown>;
  trace_id: string;
  timestamp: string;
}
