import { useState, useEffect } from 'react';
import { Card, Button, Row, Col, Tag, Space, Typography, Modal, Input, Select, InputNumber, ColorPicker, theme } from 'antd';
import { PlusOutlined, ThunderboltOutlined, EditOutlined, DeleteOutlined, TeamOutlined } from '@ant-design/icons';
import { useCharacterSync } from '../store/hooks';
import { useStore } from '../store';
import type { Character } from '../types';

const { Title, Text, Paragraph } = Typography;

const ROLE_TYPES = [
  { value: 'protagonist', label: '主角', color: 'gold' },
  { value: 'antagonist', label: '反派', color: 'red' },
  { value: 'supporting', label: '配角', color: 'blue' },
];

export default function CharacterWorkshop() {
  const { token } = theme.useToken();
  const { characters, currentProject } = useStore();
  const { refreshCharacters, createCharacter, updateCharacter, deleteCharacter } = useCharacterSync();
  const [editOpen, setEditOpen] = useState(false);
  const [editingChar, setEditingChar] = useState<Partial<Character> | null>(null);

  const projectId = currentProject?.id || '';

  useEffect(() => {
    if (projectId) refreshCharacters(projectId);
  }, [projectId, refreshCharacters]);

  const getRoleColor = (roleType: string) => {
    return ROLE_TYPES.find((r) => r.value === roleType)?.color || 'default';
  };

  const handleSave = async () => {
    if (!editingChar) return;
    const data = { ...editingChar, project_id: projectId };
    if (editingChar.id) {
      await updateCharacter(editingChar.id, data);
    } else {
      await createCharacter(data);
    }
    setEditOpen(false);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>
          <TeamOutlined style={{ marginRight: 8 }} />角色工坊
        </Title>
        <Space>
          <Button icon={<PlusOutlined />}
            onClick={() => { setEditingChar({ role_type: 'supporting' }); setEditOpen(true); }}>
            添加角色
          </Button>
          <Button type="primary" icon={<ThunderboltOutlined />}>
            AI 批量生成
          </Button>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        {characters.map((char: Character) => (
          <Col xs={24} sm={12} lg={8} key={char.id}>
            <Card
              hoverable
              style={{ borderLeft: `4px solid ${char.ui_color || token.colorPrimary}` }}
              actions={[
                <EditOutlined key="edit" onClick={() => { setEditingChar(char); setEditOpen(true); }} />,
                <DeleteOutlined key="delete" onClick={() => deleteCharacter(char.id, projectId)} />,
              ]}
            >
              <Card.Meta
                title={
                  <Space>
                    <Text strong style={{ fontSize: 16 }}>{char.name}</Text>
                    <Tag color={getRoleColor(char.role_type)}>
                      {ROLE_TYPES.find((r) => r.value === char.role_type)?.label}
                    </Tag>
                  </Space>
                }
                description={
                  <>
                    <Space size={4} wrap style={{ marginBottom: 8 }}>
                      <Tag>{char.gender}</Tag>
                      {char.age && <Tag>年龄: {char.age}</Tag>}
                      {char.power_level && <Tag color="purple">{char.power_level}</Tag>}
                    </Space>
                    {char.personality && (
                      <Paragraph ellipsis={{ rows: 2 }} type="secondary">
                        性格: {char.personality}
                      </Paragraph>
                    )}
                    {char.mental_state && (
                      <Text type="secondary">心理状态: {char.mental_state}</Text>
                    )}
                  </>
                }
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Modal
        title={editingChar?.id ? '编辑角色' : '新建角色'}
        open={editOpen}
        onCancel={() => setEditOpen(false)}
        onOk={handleSave}
        width={700}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Space>
            <Input placeholder="角色名" value={editingChar?.name || ''}
              onChange={(e) => setEditingChar((p) => ({ ...p, name: e.target.value }))} />
            <Select placeholder="角色类型" value={editingChar?.role_type || 'supporting'}
              onChange={(v) => setEditingChar((p) => ({ ...p, role_type: v }))}
              options={ROLE_TYPES} style={{ width: 120 }} />
            <Select placeholder="性别" value={editingChar?.gender || '男'}
              onChange={(v) => setEditingChar((p) => ({ ...p, gender: v }))}
              options={[{ value: '男', label: '男' }, { value: '女', label: '女' }]} style={{ width: 80 }} />
            <InputNumber placeholder="年龄" value={editingChar?.age || undefined}
              onChange={(v) => setEditingChar((p) => ({ ...p, age: v || undefined }))} min={1} max={10000}
              style={{ width: 100 }} />
          </Space>
          <Input.TextArea placeholder="外貌描述" value={editingChar?.appearance || ''}
            onChange={(e) => setEditingChar((p) => ({ ...p, appearance: e.target.value }))} rows={2} />
          <Input.TextArea placeholder="性格特征" value={editingChar?.personality || ''}
            onChange={(e) => setEditingChar((p) => ({ ...p, personality: e.target.value }))} rows={2} />
          <Input.TextArea placeholder="背景故事" value={editingChar?.background || ''}
            onChange={(e) => setEditingChar((p) => ({ ...p, background: e.target.value }))} rows={3} />
          <Input.TextArea placeholder="角色目标" value={editingChar?.goals || ''}
            onChange={(e) => setEditingChar((p) => ({ ...p, goals: e.target.value }))} rows={2} />
          <Input.TextArea placeholder="角色秘密" value={editingChar?.secrets || ''}
            onChange={(e) => setEditingChar((p) => ({ ...p, secrets: e.target.value }))} rows={2} />
          <Input placeholder="心理状态" value={editingChar?.mental_state || ''}
            onChange={(e) => setEditingChar((p) => ({ ...p, mental_state: e.target.value }))} />
          <Input placeholder="战力等级" value={editingChar?.power_level || ''}
            onChange={(e) => setEditingChar((p) => ({ ...p, power_level: e.target.value }))} />
          <Input placeholder="个人信条" value={editingChar?.motto || ''}
            onChange={(e) => setEditingChar((p) => ({ ...p, motto: e.target.value }))} />
          <Space>
            <Text>UI 标识色：</Text>
            <ColorPicker value={editingChar?.ui_color || '#4D8088'}
              onChange={(_, hex) => setEditingChar((p) => ({ ...p, ui_color: hex }))} />
          </Space>
        </Space>
      </Modal>
    </div>
  );
}
