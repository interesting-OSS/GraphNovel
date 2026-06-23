import { useState, useEffect } from 'react';
import { Card, Select, Typography, Space, Tag, List, Empty, Spin, Button, Modal } from 'antd';
import { HistoryOutlined } from '@ant-design/icons';
import { useStore } from '../store';
import { chapterApi } from '../services/api';
import DiffViewerComponent from '../components/DiffViewer';
import type { GenerationHistory } from '../types';

const { Title, Text } = Typography;

export default function ChapterDiff() {
  const { currentProject, chapters } = useStore();
  const [selectedChapterId, setSelectedChapterId] = useState('');
  const [history, setHistory] = useState<GenerationHistory[]>([]);
  const [loading, setLoading] = useState(false);
  const [compareA, setCompareA] = useState<number>(0);
  const [compareB, setCompareB] = useState<number>(1);
  const [diffOpen, setDiffOpen] = useState(false);
  const projectId = currentProject?.id || '';

  useEffect(() => {
    if (chapters.length > 0 && !selectedChapterId) {
      setSelectedChapterId(chapters[chapters.length - 1].id);
    }
  }, [chapters]);

  useEffect(() => {
    if (!selectedChapterId) return;
    setLoading(true);
    chapterApi.getGenerationHistory(selectedChapterId)
      .then((data: any) => setHistory(data.items || data.history || []))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  }, [selectedChapterId]);

  const selectedChapter = chapters.find((ch: any) => ch.id === selectedChapterId);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4}><HistoryOutlined style={{ marginRight: 8 }} />版本历史与差异对比</Title>
        <Select showSearch placeholder="选择章节" value={selectedChapterId || undefined}
          onChange={setSelectedChapterId} style={{ width: 300 }}
          options={chapters.map((ch: any) => ({
            value: ch.id,
            label: `第${ch.chapter_index}章 ${ch.title}`,
          }))}
          filterOption={(input, option) => (option?.label as string)?.includes(input)} />
      </div>

      <Spin spinning={loading}>
        {history.length === 0 ? (
          <Empty description="该章节暂无生成历史，使用 AI 生成后会自动记录版本" />
        ) : (
          <>
            <Card title={`${selectedChapter?.title || '章节'} — 共 ${history.length} 个版本`} size="small" style={{ marginBottom: 16 }}>
              <List
                dataSource={history}
                renderItem={(item: GenerationHistory, idx: number) => (
                  <List.Item
                    actions={[
                      <Button size="small" key="compare"
                        onClick={() => { setCompareA(idx); setCompareB(idx - 1); setDiffOpen(true); }}
                        disabled={idx === 0}>
                        与上一版对比
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Tag color="blue">v{item.version}</Tag>
                          <Text>{item.word_count?.toLocaleString()} 字</Text>
                          <Text type="secondary">{new Date(item.created_at).toLocaleString('zh-CN')}</Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            </Card>

            <Modal title={`版本对比: v${history[compareA]?.version} vs v${history[compareB]?.version}`}
              open={diffOpen} onCancel={() => setDiffOpen(false)} footer={null} width={1000}>
              {history[compareA] && history[compareB] ? (
                <DiffViewerComponent
                  oldText={history[compareB].content || ''}
                  newText={history[compareA].content || ''}
                  oldLabel={`v${history[compareB].version}`}
                  newLabel={`v${history[compareA].version}`}
                />
              ) : (
                <Empty description="无法对比" />
              )}
            </Modal>
          </>
        )}
      </Spin>
    </div>
  );
}
