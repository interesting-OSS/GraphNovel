export interface PaginatedResponse<T> { items: T[]; total: number; }
export interface LoadingState { loading: boolean; error: string | null; }
