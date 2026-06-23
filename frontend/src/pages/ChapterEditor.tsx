import { useState, useEffect, useRef } from 'react';
import {
  Card, Button, Space, Typography, Tag, Input, Select,
  Progress, Modal, Tabs, Empty, Spin, message, Row, Col, Divider,
} from 'antd';
import {
  ThunderboltOutlined, EditOutlined, SaveOutlined, EyeOutlined,
  SwapOutlined, HighlightOutlined, ExpandOutlined, CompressOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { useStore } from '../store';
import { useChapterSync } from '../store/hooks';
import { writingStyleApi } from '../services/api';
import { createChapterGenerateStream } from '../utils/sseClient';
import type { Chapter } from '../types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const REWRITE_STRATEGIES = [
  { key: 'similar', label: '保持风格', icon: <SwapOutlined />, desc: '保持原有风格改写' },
  { key: 'expand', label: '扩展细节', icon: <ExpandOutlined />, desc: '扩展描写和细节' },
  { key: 'condense', label: '精简内容', icon: <CompressOutlined />, desc: '精简冗余内容' },
  { key: 'custom', label: '自定义', icon: <EditOutlined />, desc: '按指令重写' },
];

export default function ChapterEditor() {
  const { currentProject, chapters, currentChapter, setCurrentChapter } = useStore();
  const { refreshChapters, updateChapter } = useChapterSync();
  const [activeTab, setActiveTab] = useState('write');
  const [editContent, setEditContent] = useState('');
  const [editTitle, setEditTitle] = useState('');
  const [saving, setSaving] = useState(false);

  // AI generation state
  const [genOpen, setGenOpen] = useState(false);
  const [genContent, setGenContent] = useState('');
  const [genProgress, setGenProgress] = useState(0);
  const [genStatus, setGenStatus] = useState('');
  const [genAbort, setGenAbort] = useState<(() => void) | null>(null);

  // Partial rewrite state
  const [selectedText, setSelectedText] = useState('');
  const [rewriteOpen, setRewriteOpen] = useState(false);
  const [rewriteStrategy, setRewriteStrategy] = useState('similar');
  const [rewriteInstruction, setRewriteInstruction] = useState('');
  const [rewriting, setRewriting] = useState(false);
  const [rewriteContent, setRewriteContent] = useState('');

  // Per-chapter config
  const [modelOverride, setModelOverride] = useState('');
  const [writingStyleId, setWritingStyleId] = useState('');
  const [styles, setStyles] = useState<any[]>([]);

  const textareaRef = useRef<any>(null);
  const projectId = currentProject?.id || '';

  useEffect(() => {
    if (projectId) {
      refreshChapters(projectId);
      writingStyleApi.list().then((d: any) => setStyles(d.items || [])).catch(() => {});
    }
  }, [projectId]);

  useEffect(() => {
    if (currentChapter) {
      setEditContent(currentChapter.content || '');
      setEditTitle(currentChapter.title || '');
      setModelOverride(currentChapter.model_override || '');
      setWritingStyleId(currentChapter.writing_style_id || '');
    }
  }, [currentChapter?.id]);

  const handleSave = async () => {
    if (!currentChapter) return;
    setSaving(true);
    await updateChapter(currentChapter.id, {
      title: editTitle,
      content: editContent,
      project_id: projectId,
      model_override: modelOverride || undefined,
      writing_style_id: writingStyleId || undefined,
    });
    setSaving(false);
    message.success('已保存');
    refreshChapters(projectId);
  };

  const handleGenerate = () => {
    if (!currentChapter) return;
    setGenOpen(true);
    setGenContent('');
    setGenProgress(0);
    setGenStatus('准备上下文...');

    const { abort } = createChapterGenerateStream(
      `/api/chapters/${currentChapter.id}/generate-stream`,
      {
        project_id: projectId,
        model_override: modelOverride || undefined,
        writing_style_id: writingStyleId || undefined,
      },
      {
        onProgress: (d) => { setGenProgress(d.progress); setGenStatus(d.message); },
        onChunk: (c) => setGenContent((p) => p + c),
        onComplete: () => { setGenStatus('生成完成'); setGenProgress(100); },
        onError: (msg) => { setGenStatus(`错误: ${msg}`); },
      },
    );
    setGenAbort(() => abort);
  };

  const handleAcceptGeneration = () => {
    setEditContent(genContent);
    setGenOpen(false);
    setGenContent('');
  };

  const handleTextSelect = () => {
    const textarea = textareaRef.current?.resizableTextArea?.textArea;
    if (textarea) {
      const selected = textarea.value.substring(textarea.selectionStart, textarea.selectionEnd);
      if (selected.trim()) {
        setSelectedText(selected);
        setRewriteOpen(true);
      }
    }
  };

  const handleRewrite = async () => {
    if (!currentChapter || !selectedText) return;
    setRewriting(true);
    setRewriteContent('');

    const { abort } = createChapterGenerateStream(
      `/api/chapters/${currentChapter.id}/partial-regenerate-stream`,
      {
        project_id: projectId,
        selected_text: selectedText,
        strategy: rewriteStrategy,
        instruction: rewriteInstruction,
      },
      {
        onChunk: (c) => setRewriteContent((p) => p + c),
        onComplete: () => { setRewriting(false); message.success('重写完成'); },
        onError: (msg) => { setRewriting(false); message.error(msg); },
      },
    );
  };

  const handleAcceptRewrite = () => {
    setEditContent((prev) => prev.replace(selectedText, rewriteContent));
    setRewriteOpen(false);
    setRewriteContent('');
    setSelectedText('');
  };

  const wordCount = editContent.length;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>章节写作</Title>
        <Space>
          <Button icon={<SaveOutlined />} onClick={handleSave} loading={saving} type="primary">保存</Button>
        </Space>
      </div>

      {/* Chapter selector */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Select
            showSearch
            placeholder="选择章节"
            value={currentChapter?.id || undefined}
            onChange={(id) => {
              const ch = chapters.find((c: Chapter) => c.id === id);
              setCurrentChapter(ch || null);
            }}
            options={chapters.map((ch: Chapter) => ({
              value: ch.id,
              label: `第${ch.chapter_index}章 ${ch.title} (${ch.word_count}字) [${ch.status}]`,
            }))}
            style={{ width: '100%' }}
            filterOption={(input, option) => (option?.label as string)?.includes(input)}
          />
        </Col>
        <Col>
          <Select placeholder="写作风格" allowClear value={writingStyleId || undefined}
            onChange={(v) => setWritingStyleId(v || '')} style={{ width: 140 }}
            options={styles.map((s: any) => ({ value: s.id, label: s.name }))} />
        </Col>
        <Col>
          <Input placeholder="模型覆盖" allowClear value={modelOverride}
            onChange={(e) => setModelOverride(e.target.value)} style={{ width: 150 }} />
        </Col>
        <Col>
          <Button type="primary" icon={<ThunderboltOutlined />}
            onClick={handleGenerate} disabled={!currentChapter}>
            AI 生成
          </Button>
        </Col>
      </Row>

      {!currentChapter ? (
        <Empty description="请选择一个章节开始写作" />
      ) : (
        <>
          <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
            {
              key: 'write',
              label: <span><EditOutlined />编辑</span>,
              children: (
                <div>
                  <Input value={editTitle} onChange={(e) => setEditTitle(e.target.value)}
                    placeholder="章节标题" style={{ marginBottom: 8, fontSize: 18, fontWeight: 600 }} />

                  <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                    <Space>
                      <Button size="small" icon={<HighlightOutlined />} onClick={handleTextSelect}>
                        选中文本部分重写
                      </Button>
                    </Space>
                    <Space>
                      <Tag>{currentChapter.status}</Tag>
                      <Text type="secondary">字数: {wordCount.toLocaleString()}</Text>
                      <Progress percent={Math.min(100, Math.round(wordCount / 3000 * 100))}
                        size="small" style={{ width: 80 }}
                        format={() => `${Math.round(wordCount / 3000 * 100)}%`} />
                    </Space>
                  </div>

                  <TextArea
                    ref={textareaRef}
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows={24}
                    placeholder="开始写作，或点击「AI 生成」..."
                    style={{ fontFamily: '"Source Han Serif SC", "Noto Serif CJK SC", serif', fontSize: 15, lineHeight: 1.8 }}
                  />
                </div>
              ),
            },
            {
              key: 'preview',
              label: <span><EyeOutlined />预览</span>,
              children: (
                <Card>
                  <Title level={3} style={{ textAlign: 'center' }}>{editTitle}</Title>
                  <Divider />
                  {editContent ? (
                    <div className="markdown-content" style={{ maxWidth: 800, margin: '0 auto', fontSize: 16, lineHeight: 2 }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                        {editContent}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <Empty description="暂无内容" />
                  )}
                </Card>
              ),
            },
          ]} />
        </>
      )}

      {/* AI Generation Modal */}
      <Modal title="AI 章节生成" open={genOpen} onCancel={() => { genAbort?.(); setGenOpen(false); }}
        footer={genContent ? [
          <Button key="cancel" onClick={() => setGenOpen(false)}>取消</Button>,
          <Button key="accept" type="primary" onClick={handleAcceptGeneration}>采用此版本</Button>,
        ] : null}
        width={900}
      >
        <Progress percent={genProgress} status={genProgress < 100 ? 'active' : 'success'} />
        <Text type="secondary">{genStatus}</Text>
        <div style={{
          marginTop: 16, maxHeight: 500, overflow: 'auto', padding: 16,
          background: '#fafafa', borderRadius: 8, fontSize: 15, lineHeight: 2,
          whiteSpace: 'pre-wrap', minHeight: 200,
        }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
            {genContent || '等待 AI 生成...'}
          </ReactMarkdown>
        </div>
      </Modal>

      {/* Partial Rewrite Modal */}
      <Modal title="部分重写" open={rewriteOpen}
        onCancel={() => { setRewriteOpen(false); setSelectedText(''); }}
        footer={rewriteContent ? [
          <Button key="cancel" onClick={() => { setRewriteOpen(false); setRewriteContent(''); }}>取消</Button>,
          <Button key="accept" type="primary" onClick={handleAcceptRewrite}>采用</Button>,
        ] : null}
        width={800}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Card size="small" title="选中的原文">
            <Paragraph ellipsis={{ rows: 3 }} style={{ whiteSpace: 'pre-wrap' }}>{selectedText}</Paragraph>
          </Card>

          <Text strong>重写策略：</Text>
          <Select value={rewriteStrategy} onChange={setRewriteStrategy} style={{ width: '100%' }}
            options={REWRITE_STRATEGIES.map((s) => ({ value: s.key, label: `${s.label} — ${s.desc}` }))} />

          {rewriteStrategy === 'custom' && (
            <Input.TextArea placeholder="自定义重写指令..." value={rewriteInstruction}
              onChange={(e) => setRewriteInstruction(e.target.value)} rows={2} />
          )}

          <Button type="primary" icon={<ThunderboltOutlined />}
            onClick={handleRewrite} loading={rewriting} block>
            开始重写
          </Button>

          {rewriteContent && (
            <Card size="small" title="重写结果">
              <div style={{ whiteSpace: 'pre-wrap', fontSize: 15, lineHeight: 1.8 }}>{rewriteContent}</div>
            </Card>
          )}
        </Space>
      </Modal>
    </div>
  );
}
