import { useState, useEffect, useRef } from 'react';
import { Card, Input, Button, Select, Typography, Space, List, Tag, Empty, Spin, message } from 'antd';
import { ThunderboltOutlined, SendOutlined, RobotOutlined, UserOutlined, ClearOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { skillApi } from '../services/api';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export default function SkillChat() {
  const [skills, setSkills] = useState<any[]>([]);
  const [selectedSkill, setSelectedSkill] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState('');
  const abortRef = useRef<AbortController | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    skillApi.list().then((d: any) => setSkills(d.skills || d.items || [])).catch(() => {});
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, streaming]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setInput('');
    setLoading(true);
    setStreaming('');

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch('/api/skills/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_name: selectedSkill || undefined,
          message: text,
          history: messages.slice(-10),
        }),
        signal: controller.signal,
      });

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No stream');

      const decoder = new TextDecoder();
      let buffer = '';
      let acc = '';

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
              if (event.type === 'chunk') {
                acc += event.content || '';
                setStreaming(acc);
              }
            } catch { /* skip parse errors */ }
          }
        }
      }

      if (acc) setMessages((prev) => [...prev, { role: 'assistant', content: acc }]);
    } catch (err: any) {
      if (err.name !== 'AbortError') message.error('对话失败');
    } finally {
      setLoading(false);
      setStreaming('');
      abortRef.current = null;
    }
  };

  const handleClear = () => setMessages([]);

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 120px)', gap: 16 }}>
      {/* Skill selector sidebar */}
      <Card size="small" style={{ width: 200 }}>
        <Title level={5}><ThunderboltOutlined /> 技能包</Title>
        <Select placeholder="选择技能" allowClear value={selectedSkill || undefined}
          onChange={(v) => setSelectedSkill(v || '')} style={{ width: '100%', marginBottom: 8 }}
          options={skills.map((s: any) => ({ value: s.name, label: s.name }))} />
        <List size="small" dataSource={skills} rowKey="name"
          renderItem={(s: any) => (
            <List.Item style={{ cursor: 'pointer', padding: '4px 8px' }}
              onClick={() => setSelectedSkill(s.name)}>
              <Text style={{ fontWeight: selectedSkill === s.name ? 600 : 400 }}>{s.name}</Text>
            </List.Item>
          )} />
      </Card>

      {/* Chat area */}
      <Card style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
        title={<Space><RobotOutlined />AI 技能对话 {selectedSkill && <Tag color="blue">{selectedSkill}</Tag>}</Space>}
        extra={<Button icon={<ClearOutlined />} onClick={handleClear} size="small">清空</Button>}>
        <div ref={listRef} style={{ flex: 1, overflow: 'auto', marginBottom: 12, minHeight: 300 }}>
          {messages.length === 0 && !streaming && (
            <Empty description="选择一个技能包，开始与 AI 对话创作" style={{ marginTop: 80 }} />
          )}
          {messages.map((msg, i) => (
            <div key={i} style={{ marginBottom: 12, textAlign: msg.role === 'user' ? 'right' : 'left' }}>
              <Tag icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                color={msg.role === 'user' ? 'blue' : 'green'}>
                {msg.role === 'user' ? '你' : 'AI'}
              </Tag>
              <div style={{
                display: 'inline-block', maxWidth: '80%', padding: '8px 14px', borderRadius: 12,
                background: msg.role === 'user' ? '#e6f7ff' : '#f6ffed',
                textAlign: 'left', whiteSpace: 'pre-wrap',
              }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
              </div>
            </div>
          ))}
          {streaming && (
            <div style={{ marginBottom: 12 }}>
              <Tag color="green" icon={<RobotOutlined />}>AI</Tag>
              <div style={{ display: 'inline-block', maxWidth: '80%', padding: '8px 14px',
                borderRadius: 12, background: '#f6ffed', whiteSpace: 'pre-wrap' }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{streaming}</ReactMarkdown>
              </div>
            </div>
          )}
          {loading && !streaming && <Spin style={{ display: 'block' }} />}
        </div>
        <Space.Compact style={{ width: '100%' }}>
          <TextArea value={input} onChange={(e) => setInput(e.target.value)}
            onPressEnter={(e) => { if (!e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="输入你的创作问题..." rows={2} style={{ flex: 1 }} />
          <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading} style={{ height: 'auto' }}>
            发送
          </Button>
        </Space.Compact>
      </Card>
    </div>
  );
}
