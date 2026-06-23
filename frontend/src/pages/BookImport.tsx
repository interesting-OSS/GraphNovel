import { useState } from 'react';
import { Card, Button, Upload, Steps, Typography, List, Tag, Spin, message, Space } from 'antd';
import { InboxOutlined, FileTextOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { useStore } from '../store';
import { bookImportApi } from '../services/api';

const { Title, Text } = Typography;
const { Dragger } = Upload;

export default function BookImport() {
  const { currentProject } = useStore();
  const [step, setStep] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [taskId, setTaskId] = useState('');
  const [preview, setPreview] = useState<any>(null);
  const [applied, setApplied] = useState<{ outlines: number; characters: number } | null>(null);

  const projectId = currentProject?.id || '';

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.txt,.epub',
    maxCount: 1,
    beforeUpload: async (file) => {
      if (file.size > 50 * 1024 * 1024) {
        message.error('文件大小超过 50MB 限制');
        return false;
      }
      setUploading(true);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('project_id', projectId);
      try {
        const result: any = await bookImportApi.upload(formData);
        if (result.task_id) {
          setTaskId(result.task_id);
          setStep(1);
          // Load preview
          const prev: any = await bookImportApi.preview(result.task_id);
          setPreview(prev.preview);
          setStep(2);
        } else {
          message.error(result.error || '上传失败');
        }
      } catch { /* handled */ }
      finally { setUploading(false); }
      return false;
    },
  };

  const handleApply = async () => {
    if (!taskId || !projectId) return;
    setUploading(true);
    try {
      const result: any = await bookImportApi.apply({ task_id: taskId, project_id: projectId });
      if (result.status === 'applied') {
        setApplied({ outlines: result.outlines_created || 0, characters: result.characters_created || 0 });
        setStep(3);
        message.success(`导入完成：${result.outlines_created} 章，${result.characters_created} 个角色`);
      }
    } catch { /* handled */ }
    finally { setUploading(false); }
  };

  return (
    <div>
      <Title level={4}><FileTextOutlined style={{ marginRight: 8 }} />拆书导入</Title>

      <Steps current={step} style={{ marginBottom: 24 }} items={[
        { title: '上传文件' }, { title: '解析预览' }, { title: '确认导入' }, { title: '完成' },
      ]} />

      <Spin spinning={uploading} tip="处理中...">

        {step === 0 && (
          <Card title="上传 TXT/EPUB 文件">
            <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
              支持 .txt 和 .epub 格式，最大 50MB。AI 将自动识别章节边界并提取角色。
            </Text>
            <Dragger {...uploadProps}>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            </Dragger>
          </Card>
        )}

        {step === 2 && preview && (
          <Card title="解析预览" extra={
            <Button type="primary" onClick={handleApply}>确认导入到项目</Button>
          }>
            <Text>检测到 {preview.chapters?.length || 0} 个章节</Text>
            <List
              size="small"
              dataSource={preview.chapters || []}
              renderItem={(ch: any) => (
                <List.Item><Tag>{ch.title}</Tag></List.Item>
              )}
              style={{ marginTop: 8, maxHeight: 400, overflow: 'auto' }}
            />
          </Card>
        )}

        {step === 3 && applied && (
          <Card>
            <div style={{ textAlign: 'center', padding: 40 }}>
              <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />
              <Title level={3} style={{ marginTop: 16 }}>导入完成</Title>
              <Space size="large">
                <Text>章节：{applied.outlines} 章</Text>
                <Text>角色：{applied.characters} 个</Text>
              </Space>
            </div>
          </Card>
        )}
      </Spin>
    </div>
  );
}
