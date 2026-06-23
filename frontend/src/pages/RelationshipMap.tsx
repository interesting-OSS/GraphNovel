import { useState, useEffect, useMemo } from 'react';
import { Card, Typography, Empty, Tag, Space, Spin } from 'antd';
import { NodeIndexOutlined } from '@ant-design/icons';
import { ReactFlow, Background, Controls, MiniMap, useNodesState, useEdgesState, type Node, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useStore } from '../store';
import { characterApi, relationshipApi } from '../services/api';
import type { Character, CharacterRelationship } from '../types';
import dagre from 'dagre';

const { Title } = Typography;

const COLORS = ['#1890ff', '#52c41a', '#fa8c16', '#eb2f96', '#722ed1', '#13c2c2', '#f5222d', '#faad14'];

export default function RelationshipMap() {
  const { currentProject, characters, setCharacters } = useStore();
  const [relationships, setRelationships] = useState<CharacterRelationship[]>([]);
  const [loading, setLoading] = useState(false);
  const projectId = currentProject?.id || '';

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const load = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const [charData, relData]: any[] = await Promise.all([
        characterApi.list(projectId),
        relationshipApi.list(projectId),
      ]);
      setCharacters(charData.items || []);
      setRelationships(relData.items || []);
    } catch { /* handled */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [projectId]);

  const colorMap = useMemo(() => {
    const map: Record<string, string> = {};
    characters.forEach((c, i) => { map[c.id] = COLORS[i % COLORS.length]; });
    return map;
  }, [characters]);

  useEffect(() => {
    if (characters.length === 0) {
      setNodes([]);
      setEdges([]);
      return;
    }

    const nodeList = characters.map((char: Character) => ({
      id: char.id,
      data: {
        label: (
          <div style={{ padding: '4px 8px', textAlign: 'center' }}>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{char.name}</div>
            <Tag color={colorMap[char.id]} style={{ fontSize: 10, marginTop: 2 }}>
              {char.role_type === 'protagonist' ? '主角' : char.role_type === 'antagonist' ? '反派' : '配角'}
            </Tag>
          </div>
        ),
      },
      position: { x: 0, y: 0 },
      style: {
        background: '#fff',
        border: `2px solid ${colorMap[char.id] || '#1890ff'}`,
        borderRadius: 8,
        padding: 0,
        width: 120,
      },
    }));

    const edgeList = relationships.map((rel: CharacterRelationship) => ({
      id: rel.id,
      source: rel.char_a_id,
      target: rel.char_b_id,
      label: rel.relation_type,
      style: { stroke: '#999' },
    }));

    // Layout with dagre
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 100 });
    nodeList.forEach((n) => g.setNode(n.id, { width: 120, height: 60 }));
    edgeList.forEach((e) => g.setEdge(e.source, e.target));
    dagre.layout(g);
    nodeList.forEach((n) => {
      const pos = g.node(n.id);
      n.position = { x: pos.x - 60, y: pos.y - 30 };
    });

    setNodes(nodeList);
    setEdges(edgeList);
  }, [characters, relationships, colorMap]);

  return (
    <div>
      <Title level={4}><NodeIndexOutlined style={{ marginRight: 8 }} />角色关系图谱</Title>

      {loading && <Spin style={{ display: 'block', margin: '40px auto' }} />}

      <Card style={{ height: 600 }}>
        {!loading && characters.length === 0 ? (
          <Empty description="暂无角色，请先在角色工坊中创建角色" style={{ paddingTop: 200 }} />
        ) : (
          <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} fitView>
            <Background />
            <Controls />
            <MiniMap nodeColor="#1890ff" />
          </ReactFlow>
        )}
      </Card>
    </div>
  );
}
