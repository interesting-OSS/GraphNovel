import { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, Empty, Spin, Tag, Space, Statistic, List, Button, Tabs } from 'antd';
import { NodeIndexOutlined, ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { ReactFlow, Background, Controls, MiniMap, useNodesState, useEdgesState } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { useStore } from '../store';
import { graphStatusApi } from '../services/api';

const { Title, Text } = Typography;

const STATUS_COLORS: Record<string, string> = {
  completed: '#52c41a', active: '#1890ff', pending: '#d9d9d9', standby: '#faad14',
};

export default function GraphMonitor() {
  const { currentProject } = useStore();
  const [visualization, setVisualization] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const projectId = currentProject?.id || '';

  const load = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const [viz, met]: any[] = await Promise.all([
        graphStatusApi.getVisualization(projectId),
        graphStatusApi.getMetrics(projectId),
      ]);
      setVisualization(viz);
      setMetrics(met);
    } catch { /* handled */ }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [projectId]);

  // Layout visualization nodes
  useEffect(() => {
    if (!visualization?.nodes) return;

    const nodeList = visualization.nodes.map((n: any) => ({
      id: n.id,
      data: {
        label: (
          <div style={{ padding: '6px 12px', textAlign: 'center', fontSize: 12 }}>
            <div style={{ fontWeight: 600 }}>{n.label}</div>
            <Tag color={STATUS_COLORS[n.status] || 'default'} style={{ fontSize: 10, marginTop: 2 }}>
              {n.status}
            </Tag>
          </div>
        ),
      },
      position: { x: 0, y: 0 },
      style: {
        background: '#fff',
        border: `2px solid ${STATUS_COLORS[n.status] || '#d9d9d9'}`,
        borderRadius: 8,
        width: 140,
      },
    }));

    const edgeList = (visualization.edges || []).map((e: any) => ({
      id: `${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      label: e.label || '',
      style: { stroke: '#999' },
    }));

    // dagre layout
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 80 });
    nodeList.forEach((n: any) => g.setNode(n.id, { width: 140, height: 60 }));
    edgeList.forEach((e: any) => g.setEdge(e.source, e.target));
    dagre.layout(g);
    nodeList.forEach((n: any) => {
      const pos = g.node(n.id);
      if (pos) n.position = { x: pos.x - 70, y: pos.y - 30 };
    });

    setNodes(nodeList);
    setEdges(edgeList);
  }, [visualization]);

  return (
    <div>
      <Title level={4}><NodeIndexOutlined style={{ marginRight: 8 }} />图流程监控</Title>

      <Spin spinning={loading}>
        <Tabs items={[
          {
            key: 'graph',
            label: '流程图',
            children: (
              <Card style={{ height: 600 }}>
                {!visualization?.nodes ? (
                  <Empty description="暂无数据，开始创作后自动展示流程状态" style={{ paddingTop: 200 }} />
                ) : (
                  <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange} fitView>
                    <Background />
                    <Controls />
                    <MiniMap nodeColor="#1890ff" />
                  </ReactFlow>
                )}
              </Card>
            ),
          },
          {
            key: 'metrics',
            label: '节点耗时',
            children: (
              <div>
                {metrics?.summary && (
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    {[
                      { title: '总调用次数', value: metrics.summary.total_node_calls, color: '#1890ff' },
                      { title: '总耗时(ms)', value: metrics.summary.total_time_ms, color: '#52c41a' },
                      { title: '失败率', value: `${metrics.summary.failure_rate_pct}%`, color: '#fa8c16' },
                      { title: '使用节点', value: metrics.summary.unique_nodes, color: '#722ed1' },
                    ].map((s) => (
                      <Col xs={12} sm={6} key={s.title}>
                        <Card size="small"><Statistic title={s.title} value={s.value} valueStyle={{ color: s.color }} /></Card>
                      </Col>
                    ))}
                  </Row>
                )}

                {metrics?.metrics?.length > 0 ? (
                  <List dataSource={metrics.metrics} renderItem={(m: any) => (
                    <Card size="small" style={{ marginBottom: 8 }}>
                      <Space>
                        <Tag color="blue">{m.node}</Tag>
                        <Text>调用 {m.count} 次</Text>
                        <Text type="secondary">平均 {m.avg_duration_ms}ms</Text>
                        <Text type="secondary">最长 {m.max_duration_ms}ms</Text>
                        <Tag color="green"><CheckCircleOutlined /> {m.success_count}</Tag>
                        {m.failure_count > 0 && <Tag color="red"><CloseCircleOutlined /> {m.failure_count}</Tag>}
                      </Space>
                    </Card>
                  )} />
                ) : (
                  <Empty description="暂无节点耗时数据，执行图流程后自动收集" />
                )}
              </div>
            ),
          },
        ]} />
      </Spin>
    </div>
  );
}
