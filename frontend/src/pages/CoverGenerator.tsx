import { useState, useEffect } from 'react';
import { Card, Button, Select, Image, Space, Typography, Input, Empty, Spin, message, Row, Col } from 'antd';
import { PictureOutlined, ThunderboltOutlined, DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import { useStore } from '../store';
import { coverApi, projectApi } from '../services/api';

const { Title, Text, Paragraph } = Typography;

const COVER_STYLES = [
  { value: 'anime', label: '日系动漫' },
  { value: 'realistic', label: '写实风格' },
  { value: 'chinese', label: '国风古韵' },
  { value: 'dark', label: '暗黑风格' },
  { value: 'light', label: '清新明亮' },
  { value: 'minimal', label: '极简主义' },
];

export default function CoverGenerator() {
  const { currentProject, setCurrentProject } = useStore();
  const [generating, setGenerating] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [style, setStyle] = useState('anime');
  const [styles, setStyles] = useState<any[]>(COVER_STYLES);
  const projectId = currentProject?.id || '';

  useEffect(() => {
    coverApi.styles().then((d: any) => { if (d.styles) setStyles(d.styles); }).catch(() => {});
  }, []);

  useEffect(() => {
    if (currentProject?.cover_prompt) setPrompt(currentProject.cover_prompt);
  }, [currentProject?.cover_prompt]);

  const handleGenerate = async () => {
    if (!projectId) return;
    setGenerating(true);
    try {
      const result: any = await projectApi.generateCover(projectId, { prompt, style });
      message.success('封面生成中...');
      if (currentProject) {
        setCurrentProject({ ...currentProject, cover_prompt: prompt, cover_url: result.cover_url });
      }
    } catch { /* handled */ }
    finally { setGenerating(false); }
  };

  const handleDownload = async () => {
    try {
      const result: any = await coverApi.download(projectId);
      if (result.url) window.open(result.url, '_blank');
    } catch { /* handled */ }
  };

  return (
    <div>
      <Title level={4}><PictureOutlined style={{ marginRight: 8 }} />AI 封面生成</Title>

      <Row gutter={24}>
        <Col xs={24} md={12}>
          <Card title="生成设置" style={{ marginBottom: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <Text>封面风格</Text>
                <Select value={style} onChange={setStyle} style={{ width: '100%', marginTop: 4 }}
                  options={styles.map((s: any) => ({ value: s.value || s, label: s.label || s }))} />
              </div>
              <div>
                <Text>提示词（描述你想要的封面）</Text>
                <Input.TextArea value={prompt} onChange={(e) => setPrompt(e.target.value)}
                  rows={4} placeholder="例如：一个修仙世界的宏大场景，主角站在山巅..." style={{ marginTop: 4 }} />
              </div>
              <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerate}
                loading={generating} block size="large">
                生成封面
              </Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24} md={12}>
          <Card title="预览">
            {currentProject?.cover_url ? (
              <div style={{ textAlign: 'center' }}>
                <Image src={currentProject.cover_url} alt="封面预览"
                  style={{ maxHeight: 400, borderRadius: 8 }} />
                <div style={{ marginTop: 12 }}>
                  <Button icon={<DownloadOutlined />} onClick={handleDownload}>下载封面</Button>
                  <Button icon={<ReloadOutlined />} onClick={handleGenerate}
                    style={{ marginLeft: 8 }} loading={generating}>重新生成</Button>
                </div>
              </div>
            ) : (
              <Empty description="尚未生成封面，填写提示词后点击生成">
                <Spin spinning={generating} />
              </Empty>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
