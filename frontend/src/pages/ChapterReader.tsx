import { useState, useEffect } from 'react';
import { Card, Select, Typography, Tag, Space, List, Empty, Spin, Divider, Tabs } from 'antd';
import { ReadOutlined, BookOutlined, EyeOutlined, TeamOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { useStore } from '../store';
import { memoryApi } from '../services/api';

const { Title, Text, Paragraph } = Typography;

export default function ChapterReader() {
  const { currentProject, chapters, characters } = useStore();
  const [chapterId, setChapterId] = useState('');
  const [chapter, setChapter] = useState<any>(null);
  const [memories, setMemories] = useState<any[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const projectId = currentProject?.id || '';

  useEffect(() => {
    if (chapters.length > 0 && !chapterId) setChapterId(chapters[0].id);
  }, [chapters]);

  useEffect(() => {
    const ch = chapters.find((c: any) => c.id === chapterId);
    setChapter(ch || null);
    if (chapterId && projectId) {
      setLoading(true);
      memoryApi.search(projectId, { query: '', n_results: 10 })
        .then((d: any) => setMemories(d.items || d.results || []))
        .catch(() => setMemories([]))
        .finally(() => setLoading(false));
    }
  }, [chapterId, projectId]);

  // Find relevant characters mentioned in content
  const mentionedChars = characters.filter((c: any) =>
    chapter?.content && c.name && chapter.content.includes(c.name)
  );

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 120px)' }}>
      {/* Reading area */}
      <div style={{ flex: 1, overflow: 'auto', paddingRight: sidebarOpen ? 320 : 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Title level={4}><ReadOutlined style={{ marginRight: 8 }} />阅读模式</Title>
          <Space>
            <Select showSearch placeholder="选择章节" value={chapterId || undefined}
              onChange={setChapterId} style={{ width: 260 }}
              options={chapters.map((ch: any) => ({
                value: ch.id, label: `第${ch.chapter_index}章 ${ch.title}`,
              }))}
              filterOption={(input, option) => (option?.label as string)?.includes(input)} />
            <Tag style={{ cursor: 'pointer' }} onClick={() => setSidebarOpen(!sidebarOpen)}>
              <BookOutlined /> {sidebarOpen ? '隐藏注解' : '显示注解'}
            </Tag>
          </Space>
        </div>

        {!chapter ? (
          <Empty description="选择章节开始阅读" />
        ) : (
          <Card style={{ maxWidth: 800, margin: '0 auto' }}>
            <Title level={2} style={{ textAlign: 'center' }}>{chapter.title}</Title>
            <Divider />
            {chapter.content ? (
              <div className="markdown-content" style={{ fontSize: 17, lineHeight: 2.2, letterSpacing: '0.02em' }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                  {chapter.content}
                </ReactMarkdown>
              </div>
            ) : (
              <Empty description="该章节暂无内容" />
            )}
            <Divider />
            <Space>
              <Tag>{chapter.status}</Tag>
              <Text type="secondary">{chapter.word_count?.toLocaleString()} 字</Text>
            </Space>
          </Card>
        )}
      </div>

      {/* Memory sidebar */}
      {sidebarOpen && (
        <div style={{ width: 320, borderLeft: '1px solid #f0f0f0', padding: 16, overflow: 'auto' }}>
          <Tabs items={[
            {
              key: 'characters',
              label: <span><TeamOutlined /> 出场角色 ({mentionedChars.length})</span>,
              children: mentionedChars.length === 0 ? <Empty description="未检测到角色出场" /> : (
                <List size="small" dataSource={mentionedChars} renderItem={(c: any) => (
                  <Card size="small" style={{ marginBottom: 8 }}>
                    <Text strong>{c.name}</Text>
                    <Tag style={{ marginLeft: 8 }}>{c.role_type === 'protagonist' ? '主角' : c.role_type === 'antagonist' ? '反派' : '配角'}</Tag>
                    {c.mental_state && <div><Text type="secondary">心理: {c.mental_state}</Text></div>}
                    {c.personality && <div><Text type="secondary">性格: {c.personality}</Text></div>}
                  </Card>
                )} />
              ),
            },
            {
              key: 'memories',
              label: <span><EyeOutlined /> 关联记忆 ({memories.length})</span>,
              children: memories.length === 0 ? <Empty description="暂无关联记忆" /> : (
                <List size="small" dataSource={memories} renderItem={(m: any) => (
                  <Card size="small" style={{ marginBottom: 8 }}>
                    <Tag color="blue">{m.memory_type || '记忆'}</Tag>
                    {m.chapter_index && <Tag>第{m.chapter_index}章</Tag>}
                    <Paragraph ellipsis={{ rows: 2 }} style={{ marginTop: 4, fontSize: 13 }}>
                      {m.content || m.summary || ''}
                    </Paragraph>
                  </Card>
                )} />
              ),
            },
          ]} />
        </div>
      )}
    </div>
  );
}
