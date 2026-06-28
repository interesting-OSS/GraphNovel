export type SSEEventType = 'progress' | 'chunk' | 'result' | 'done' | 'error';
export interface SSEProgress { type: 'progress'; message: string; progress: number; phase?: string; [key: string]: unknown; }
export interface SSEChunk { type: 'chunk'; chunk: string; }
export interface SSEResult { type: 'result'; [key: string]: unknown; }
export interface SSEDone { type: 'done'; message: string; }
export interface SSEError { type: 'error'; message: string; code?: string; }
export type SSEEvent = SSEProgress | SSEChunk | SSEResult | SSEDone | SSEError;
export interface SSEState {
  status: 'idle' | 'connecting' | 'streaming' | 'completed' | 'error';
  progress: number; message: string; partialContent: string;
  result: Record<string, unknown> | null; error: string | null;
}
