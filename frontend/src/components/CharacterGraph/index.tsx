/** Character relationship graph visualization using @xyflow/react. */
import { Card, Empty, theme } from 'antd';
import { ReactFlow, Background, Controls, MiniMap, type Node, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

interface CharacterGraphProps {
  characters: Array<{ id: string; name: string; ui_color?: string }>;
  relationships: Array<{ char_a_id: string; char_b_id: string; relation_type: string }>;
}

export default function CharacterGraph({ characters, relationships }: CharacterGraphProps) {
  const { token } = theme.useToken();

  if (characters.length === 0) {
    return <Empty description="暂无角色数据" />;
  }

  const nodes: Node[] = characters.map((char, i) => ({
    id: char.id,
    data: { label: char.name },
    position: {
      x: Math.cos((2 * Math.PI * i) / characters.length) * 200 + 300,
      y: Math.sin((2 * Math.PI * i) / characters.length) * 200 + 250,
    },
    style: {
      background: char.ui_color || token.colorPrimary,
      color: '#fff',
      borderRadius: '50%',
      width: 80,
      height: 80,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      border: `3px solid ${token.colorBorder}`,
      fontSize: 14,
      fontWeight: 'bold',
    },
  }));

  const edges: Edge[] = relationships.map((rel, i) => ({
    id: `rel-${i}`,
    source: rel.char_a_id,
    target: rel.char_b_id,
    label: rel.relation_type,
    style: { stroke: token.colorPrimary, strokeWidth: 2 },
  }));

  return (
    <Card style={{ height: 600 }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background />
        <Controls />
        <MiniMap nodeColor={token.colorPrimary} />
      </ReactFlow>
    </Card>
  );
}
