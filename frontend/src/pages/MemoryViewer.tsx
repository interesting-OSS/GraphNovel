import { useState, useEffect } from 'react';
import { Card, Input, Button, Tag, Space, Typography, Empty, Spin, List } from 'antd';
import { SearchOutlined, DatabaseOutlined } from '@ant-design/icons';
import { useStore } from '../store';
import { memoryApi } from '../services/api';

const { Title, Text, Paragraph } = Typography;

export default function MemoryViewer() {
  const { currentProject } = useStore();
  const [memories, setMemories] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const projectId = currentProject?.id || '';

  const loadAll = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data: any = await memoryApi.list(projectId);
      setMemories(data.items || []);
    } catch { /* handled */ }
    finally { setLoading(false); }
  };

  const handleSearch = async () => {
    if (!projectId || !query.trim()) { loadAll(); return; }
    setLoading(true);
    try {
      const data: any = await memoryApi.search(projectId, { query, n_results: 20 });
      setMemories(data.results || data.items || []);
    } catch { /* handled */ }
    finally { setLoading(false); }
  };

  useEffect(() => { loadAll(); }, [projectId]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}><DatabaseOutlined style={{ marginRight: 8 }} />记忆检索</Title>
        <Space>
          <Input.Search placeholder="搜索情节/角色/事件..." value={query}
            onChange={(e) => setQuery(e.target.value)} onSearch={handleSearch}
            style={{ width: 300 }} enterButton={<SearchOutlined />} />
          <Button onClick={loadAll}>全部</Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        {memories.length === 0 ? (
          <Empty description="暂无记忆数据，完成章节分析后自动生成" />
        ) : (
          <List
            dataSource={memories}
            renderItem={(item: any) => (
              <Card size="small" style={{ marginBottom: 8 }}>
                <Space wrap style={{ marginBottom: 4 }}>
                  <Tag color="blue">{item.memory_type || item.type || '记忆'}</Tag>
                  {item.memory_layer && <Tag>{item.memory_layer}</Tag>}
                  {item.importance && <Text type="secondary">重要性: {Math.round((item.importance || 0.5) * 100)}%</Text>}
                  {item.chapter_index !== undefined && <Tag>第{item.chapter_index}章</Tag>}
                </Space>
                <Paragraph ellipsis={{ rows: 3 }} style={{ marginBottom: 0 }}>
                  {item.content || item.summary || item.text || JSON.stringify(item)}
                </Paragraph>
              </Card>
            )}
          />
        )}
      </Spin>
    </div>
  );
}
