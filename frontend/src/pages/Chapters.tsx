import { useState, useEffect } from 'react';
import { Card, Button, List, Tag, Space, Modal, Progress, Typography, Input, theme, Empty } from 'antd';
import { PlusOutlined, ThunderboltOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useChapterSync } from '../store/hooks';
import { useStore } from '../store';
import { createChapterGenerateStream } from '../utils/sseClient';
import type { Chapter } from '../types';

const { Title, Text } = Typography;
const { TextArea } = Input;

export default function Chapters() {
  const { token } = theme.useToken();
  const { chapters, currentProject } = useStore();
  const { refreshChapters, createChapter, updateChapter, deleteChapter } = useChapterSync();
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingChapter, setEditingChapter] = useState<Chapter | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [generating, setGenerating] = useState(false);
  const [genProgress, setGenProgress] = useState(0);
  const [genContent, setGenContent] = useState('');
  const [genStatus, setGenStatus] = useState('');

  const projectId = currentProject?.id || '';

  useEffect(() => {
    if (projectId) refreshChapters(projectId);
  }, [projectId, refreshChapters]);

  const statusMap: Record<string, { color: string; label: string }> = {
    draft: { color: 'default', label: '草稿' },
    polished: { color: 'blue', label: '已润色' },
    final: { color: 'green', label: '定稿' },
  };

  const [genAbort, setGenAbort] = useState<(() => void) | null>(null);

  const handleGenerate = (chapterId: string) => {
    setGenerating(true);
    setGenContent('');
    setGenProgress(0);
    setGenStatus('正在准备上下文...');

    const { abort } = createChapterGenerateStream(
      `/api/chapters/${chapterId}/generate-stream`,
      { project_id: projectId },
      {
        onProgress: (data) => {
          setGenProgress(data.progress);
          setGenStatus(data.message);
        },
        onChunk: (content) => {
          setGenContent((prev) => prev + content);
        },
        onComplete: () => {
          setGenerating(false);
          setGenStatus('生成完成');
          setGenAbort(null);
          refreshChapters(projectId);
        },
        onError: (msg) => {
          setGenerating(false);
          setGenStatus(`错误: ${msg}`);
          setGenAbort(null);
        },
      },
    );
    setGenAbort(() => abort);
  };

  const handleCloseGen = () => {
    genAbort?.();
    setGenerating(false);
    setGenContent('');
    setGenAbort(null);
  };

  const handleEditOpen = (chapter: Chapter) => {
    setEditingChapter(chapter);
    setEditTitle(chapter.title);
    setEditContent(chapter.content || '');
    setEditModalOpen(true);
  };

  const handleEditSave = async () => {
    if (editingChapter) {
      await updateChapter(editingChapter.id, {
        title: editTitle,
        content: editContent,
        project_id: projectId,
      });
    }
    setEditModalOpen(false);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>章节管理</Title>
        <Button type="primary" icon={<PlusOutlined />}
          onClick={() => createChapter({ project_id: projectId, chapter_index: chapters.length + 1 })}>
          新建章节
        </Button>
      </div>

      {chapters.length === 0 ? (
        <Empty description="暂无章节" />
      ) : (
        <List
          dataSource={chapters}
          renderItem={(chapter: Chapter) => {
            const status = statusMap[chapter.status] || statusMap.draft;
            return (
              <Card
                size="small"
                style={{ marginBottom: 8 }}
                title={
                  <Space>
                    <Text strong>第{chapter.chapter_index}章</Text>
                    <Text>{chapter.title}</Text>
                    <Tag color={status.color}>{status.label}</Tag>
                    <Text type="secondary">{chapter.word_count} 字</Text>
                  </Space>
                }
                extra={
                  <Space>
                    <Button size="small" icon={<ThunderboltOutlined />}
                      onClick={() => handleGenerate(chapter.id)} loading={generating}>
                      AI 生成
                    </Button>
                    <Button size="small" icon={<EditOutlined />}
                      onClick={() => handleEditOpen(chapter)}>
                      编辑
                    </Button>
                    <Button size="small" danger icon={<DeleteOutlined />}
                      onClick={() => deleteChapter(chapter.id, projectId)} />
                  </Space>
                }
              >
                {chapter.content ? (
                  <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }} style={{ marginBottom: 0 }}>{chapter.content.slice(0, 200)}</Typography.Paragraph>
                ) : (
                  <Text type="secondary" italic>暂无内容，点击 AI 生成</Text>
                )}
              </Card>
            );
          }}
        />
      )}

      <Modal
        title="AI 章节生成"
        open={generating || !!genContent}
        onCancel={handleCloseGen}
        footer={null}
        width={800}
      >
        <Progress percent={genProgress} status={generating ? 'active' : 'success'} />
        <Text type="secondary">{genStatus}</Text>
        <div
          className="markdown-content"
          style={{
            marginTop: 16, maxHeight: 500, overflow: 'auto',
            padding: 16, background: token.colorFillSecondary,
            borderRadius: 8, whiteSpace: 'pre-wrap',
          }}
        >
          {genContent || '等待生成...'}
        </div>
      </Modal>

      <Modal
        title="编辑章节"
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        onOk={handleEditSave}
        width={800}
      >
        <Input
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          style={{ marginBottom: 16 }}
          placeholder="章节标题"
        />
        <TextArea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          rows={20}
          placeholder="章节内容..."
        />
      </Modal>
    </div>
  );
}
