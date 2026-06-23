/** LangGraph execution flow visualization using @xyflow/react. */
import { useEffect, useState } from 'react';
import { Card, Typography, Spin, Empty, theme } from 'antd';
import { ReactFlow, Background, Controls, type Node, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { graphStatusApi } from '../../services/api';

const { Title } = Typography;

interface GraphViewerProps {
  projectId: string;
}

export default function GraphViewer({ projectId }: GraphViewerProps) {
  const { token } = theme.useToken();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    graphStatusApi.getVisualization(projectId)
      .then((data: any) => {
        const flowNodes: Node[] = (data.nodes || []).map((n: any, i: number) => ({
          id: n.id,
          data: { label: n.label },
          position: { x: i * 200, y: (i % 2) * 150 },
          style: {
            background: n.status === 'active' ? token.colorPrimary :
                        n.status === 'completed' ? '#52c41a' :
                        token.colorFillSecondary,
            color: n.status === 'active' ? '#fff' : token.colorText,
            border: `2px solid ${n.status === 'active' ? token.colorPrimary : token.colorBorder}`,
            borderRadius: 8,
            padding: '10px 20px',
          },
        }));
        const flowEdges: Edge[] = (data.edges || []).map((e: any, i: number) => ({
          id: `e-${i}`,
          source: e.source,
          target: e.target,
          label: e.label,
          animated: true,
          style: { stroke: token.colorPrimary },
        }));
        setNodes(flowNodes);
        setEdges(flowEdges);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId, token]);

  if (loading) return <Spin />;
  if (nodes.length === 0) return <Empty description="暂无图执行数据" />;

  return (
    <Card title="LangGraph 执行流程" style={{ height: 400 }}>
      <ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable={false}>
        <Background />
        <Controls />
      </ReactFlow>
    </Card>
  );
}
