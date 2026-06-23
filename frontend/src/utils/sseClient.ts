/** SSE (Server-Sent Events) client for POST-based streaming. */

export interface SSEClientOptions {
  onProgress?: (data: { message: string; progress: number; status: string; wordCount?: number }) => void;
  onChunk?: (content: string) => void;
  onResult?: (data: Record<string, unknown>) => void;
  onError?: (message: string, code?: string) => void;
  onComplete?: () => void;
}

export async function ssePost<T = Record<string, unknown>>(
  url: string,
  data: Record<string, unknown>,
  options: SSEClientOptions = {},
): Promise<T> {
  const controller = new AbortController();
  let accumulatedContent = '';
  let resultData: Record<string, unknown> = {};

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error('No response body');

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
          try {
            const event = JSON.parse(line.slice(6));
            switch (event.type) {
              case 'progress':
                options.onProgress?.(event);
                break;
              case 'chunk':
                accumulatedContent += event.content || '';
                options.onChunk?.(event.content || '');
                break;
              case 'result':
                resultData = event.data || {};
                options.onResult?.(resultData);
                break;
              case 'error':
                options.onError?.(event.message, event.code);
                throw new Error(event.message);
              case 'done':
                options.onComplete?.();
                break;
            }
          } catch (e) {
            if (e instanceof SyntaxError) continue;
            throw e;
          }
        }
      }
    }

    return (resultData as T) || ({ content: accumulatedContent } as unknown as T);
  } finally {
    controller.abort();
  }
}

export function createChapterGenerateStream(
  url: string,
  data: Record<string, unknown>,
  options: SSEClientOptions,
): { abort: () => void } {
  const controller = new AbortController();

  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        options.onError?.(`HTTP ${response.status}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        options.onError?.('No response body');
        return;
      }

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
            try {
              const event = JSON.parse(line.slice(6));
              switch (event.type) {
                case 'progress':
                  options.onProgress?.(event);
                  break;
                case 'chunk':
                  options.onChunk?.(event.content || '');
                  break;
                case 'result':
                  options.onResult?.(event.data || {});
                  break;
                case 'error':
                  options.onError?.(event.message, event.code);
                  break;
                case 'done':
                  options.onComplete?.();
                  break;
              }
            } catch {
              // Skip parse errors from heartbeat comments
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        options.onError?.(err.message);
      }
    });

  return { abort: () => controller.abort() };
}
