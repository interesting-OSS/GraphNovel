import { useState, useEffect } from 'react';
import { Card, Button, Tag, Space, Typography, Modal, Input, InputNumber, Select, message, theme, Empty } from 'antd';
import { PlusOutlined, ThunderboltOutlined, EditOutlined, DeleteOutlined, OrderedListOutlined, HolderOutlined } from '@ant-design/icons';
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useOutlineSync } from '../store/hooks';
import { useStore } from '../store';
import { outlineApi } from '../services/api';
import type { Outline } from '../types';

const { Title, Text, Paragraph } = Typography;

function SortableOutlineCard({ outline, onEdit, onDelete }: {
  outline: Outline; onEdit: () => void; onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: outline.id });
  const style = { transform: CSS.Transform.toString(transform), transition, marginBottom: 8 };

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <Card size="small"
        title={
          <Space>
            <span {...listeners} style={{ cursor: 'grab' }}><HolderOutlined /></span>
            <Tag color="blue">第{outline.volume}卷</Tag>
            <Tag>第{outline.chapter_num}章</Tag>
            <Text strong>{outline.title}</Text>
            <Tag color={outline.mode === 'one-to-many' ? 'purple' : 'default'}>
              {outline.mode === 'one-to-many' ? '1对N' : '1对1'}
            </Tag>
          </Space>
        }
        extra={
          <Space>
            <Button size="small" icon={<EditOutlined />} onClick={onEdit} />
            <Button size="small" danger icon={<DeleteOutlined />} onClick={onDelete} />
          </Space>
        }>
        {outline.summary && <Paragraph ellipsis={{ rows: 2 }} type="secondary">{outline.summary}</Paragraph>}
        {outline.key_points && (
          <Space wrap>{(() => {
            try {
              const pts = JSON.parse(outline.key_points);
              return (Array.isArray(pts) ? pts : []).map((p: string, i: number) => <Tag key={i}>{p}</Tag>);
            } catch { return null; }
          })()}</Space>
        )}
      </Card>
    </div>
  );
}

export default function OutlineEditor() {
  const { token } = theme.useToken();
  const { outlines, currentProject } = useStore();
  const { refreshOutlines, createOutline, updateOutline, deleteOutline } = useOutlineSync();
  const [editOpen, setEditOpen] = useState(false);
  const [editingOutline, setEditingOutline] = useState<Partial<Outline> | null>(null);
  const [generating, setGenerating] = useState(false);
  const projectId = currentProject?.id || '';

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));

  useEffect(() => {
    if (projectId) refreshOutlines(projectId);
  }, [projectId, refreshOutlines]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await outlineApi.generate({ project_id: projectId });
      message.success('大纲生成任务已创建');
    } catch { message.error('生成失败'); }
    finally { setGenerating(false); }
  };

  const handleSave = async () => {
    if (!editingOutline) return;
    const data = { ...editingOutline, project_id: projectId };
    if (editingOutline.id) await updateOutline(editingOutline.id, data);
    else await createOutline(data);
    setEditOpen(false);
  };

  const handleDragEnd = async (event: any) => {
    const { active, over } = event;
    if (active.id !== over?.id) {
      const oldIdx = outlines.findIndex((o) => o.id === active.id);
      const newIdx = outlines.findIndex((o) => o.id === over?.id);
      if (oldIdx !== -1 && newIdx !== -1) {
        try {
          await outlineApi.reorder({ project_id: projectId, from_index: oldIdx, to_index: newIdx });
          message.success('排序已更新');
          refreshOutlines(projectId);
        } catch { message.error('排序失败'); }
      }
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}><OrderedListOutlined style={{ marginRight: 8 }} />大纲规划</Title>
        <Space>
          <Button icon={<PlusOutlined />}
            onClick={() => { setEditingOutline({ volume: 1, chapter_num: outlines.length + 1, mode: 'one-to-one', expansion_strategy: 'balanced' }); setEditOpen(true); }}>
            添加节点
          </Button>
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerate} loading={generating}>
            AI 生成大纲
          </Button>
        </Space>
      </div>

      {outlines.length === 0 ? (
        <Empty description="暂无大纲，点击 AI 生成或手动添加" />
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={outlines.map((o) => o.id)} strategy={verticalListSortingStrategy}>
            {outlines.map((outline: Outline) => (
              <SortableOutlineCard key={outline.id} outline={outline}
                onEdit={() => { setEditingOutline(outline); setEditOpen(true); }}
                onDelete={() => deleteOutline(outline.id, projectId)} />
            ))}
          </SortableContext>
        </DndContext>
      )}

      <Modal title={editingOutline?.id ? '编辑大纲' : '新建大纲节点'} open={editOpen}
        onCancel={() => setEditOpen(false)} onOk={handleSave} width={600}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input placeholder="章节标题" value={editingOutline?.title || ''}
            onChange={(e) => setEditingOutline((prev) => ({ ...prev, title: e.target.value }))} />
          <Space>
            <InputNumber placeholder="卷号" min={1} value={editingOutline?.volume || 1}
              onChange={(v) => setEditingOutline((prev) => ({ ...prev, volume: v || 1 }))} />
            <InputNumber placeholder="章号" min={1} value={editingOutline?.chapter_num || 1}
              onChange={(v) => setEditingOutline((prev) => ({ ...prev, chapter_num: v || 1 }))} />
          </Space>
          <Input.TextArea placeholder="章节摘要" rows={4} value={editingOutline?.summary || ''}
            onChange={(e) => setEditingOutline((prev) => ({ ...prev, summary: e.target.value }))} />
          <Input.TextArea placeholder="关键要点 JSON" rows={2} value={editingOutline?.key_points || ''}
            onChange={(e) => setEditingOutline((prev) => ({ ...prev, key_points: e.target.value }))} />
          <Space>
            <Select value={editingOutline?.mode || 'one-to-one'} style={{ width: 120 }}
              onChange={(v) => setEditingOutline((prev) => ({ ...prev, mode: v }))}
              options={[{ value: 'one-to-one', label: '1对1' }, { value: 'one-to-many', label: '1对N' }]} />
            <Select value={editingOutline?.expansion_strategy || 'balanced'} style={{ width: 140 }}
              onChange={(v) => setEditingOutline((prev) => ({ ...prev, expansion_strategy: v }))}
              options={[
                { value: 'balanced', label: '均衡' },
                { value: 'climax', label: '高潮优先' },
                { value: 'detail', label: '细节优先' },
              ]} />
          </Space>
        </Space>
      </Modal>
    </div>
  );
}
