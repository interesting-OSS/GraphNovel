import { useState, useCallback, useRef } from 'react';
import { sseRequest } from '../api/client';
import type { SSEEvent, SSEState } from '../types/sse';

export function useSSE() {
  const [state, setState] = useState<SSEState>({
    status: 'idle', progress: 0, message: '',
    partialContent: '', result: null, error: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const handleEvent = useCallback((event: SSEEvent) => {
    switch (event.type) {
      case 'progress':
        setState(prev => ({ ...prev, status: 'streaming', progress: event.progress, message: event.message }));
        break;
      case 'chunk':
        setState(prev => ({ ...prev, status: 'streaming', partialContent: prev.partialContent + (event.chunk || '') }));
        break;
      case 'result':
        setState(prev => ({ ...prev, result: event as unknown as Record<string, unknown> }));
        break;
      case 'done':
        setState(prev => ({ ...prev, status: 'completed', message: event.message }));
        break;
      case 'error':
        setState(prev => ({ ...prev, status: 'error', error: event.message }));
        break;
    }
  }, []);

  const startStream = useCallback(async (path: string, body: Record<string, unknown>) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ status: 'connecting', progress: 0, message: '连接中...', partialContent: '', result: null, error: null });

    try {
      const response = await sseRequest(path, body, controller.signal);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try { handleEvent(JSON.parse(line.slice(6))); }
            catch { /* skip malformed */ }
          }
        }
      }
      if (state.status !== 'error') setState(prev => ({ ...prev, status: 'completed' }));
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== 'AbortError') {
        setState(prev => ({ ...prev, status: 'error', error: err.message }));
      }
    }
  }, [handleEvent, state.status]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setState({ status: 'idle', progress: 0, message: '', partialContent: '', result: null, error: null });
  }, []);

  const reset = useCallback(() => {
    setState({ status: 'idle', progress: 0, message: '', partialContent: '', result: null, error: null });
  }, []);

  return { ...state, startStream, cancel, reset };
}
