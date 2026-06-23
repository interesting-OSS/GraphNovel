/** Text diff viewer for comparing chapter versions. */
import { Card, Empty } from 'antd';
import { SwapOutlined } from '@ant-design/icons';

interface DiffViewerProps {
  oldText: string;
  newText: string;
  oldLabel?: string;
  newLabel?: string;
}

export default function DiffViewer({ oldText, newText, oldLabel = '原版本', newLabel = '新版本' }: DiffViewerProps) {
  if (!oldText && !newText) {
    return <Empty description="无可对比内容" />;
  }

  return (
    <div style={{ display: 'flex', gap: 16 }}>
      <Card title={oldLabel} size="small" style={{ flex: 1 }}>
        <pre style={{ whiteSpace: 'pre-wrap', margin: 0, maxHeight: 500, overflow: 'auto' }}>
          {oldText || '(空)'}
        </pre>
      </Card>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <SwapOutlined style={{ fontSize: 24, color: '#999' }} />
      </div>
      <Card title={newLabel} size="small" style={{ flex: 1 }}>
        <pre style={{ whiteSpace: 'pre-wrap', margin: 0, maxHeight: 500, overflow: 'auto' }}>
          {newText || '(空)'}
        </pre>
      </Card>
    </div>
  );
}
