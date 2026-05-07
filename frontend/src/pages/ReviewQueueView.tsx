import React, { useState, useEffect } from 'react';
import {
  Card, List, Typography, Tag, Button, Row, Col,
  Descriptions, notification, Alert, Space, Divider, Spin, Tabs, Badge, Tooltip
} from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, RobotOutlined, CheckOutlined
} from '@ant-design/icons';
import { BarChart, Bar, XAxis, YAxis, Tooltip as ReTooltip, ResponsiveContainer, Cell } from 'recharts';
import { reviewApi } from '../api';

const { Title, Text } = Typography;
const ORANGE = '#FF6B2C';

const FEATURE_LABELS: Record<string, string> = {
  F01: 'Name Jaro-Winkler', F02: 'Token Set Ratio',   F03: 'Abbreviation Match',
  F04: 'PAN Match',          F05: 'GSTIN Match',        F06: 'Pin Code Match',
  F07: 'Geo Distance (m)',   F08: 'Address Overlap',    F09: 'Phone Match',
  F10: 'NIC Industry',       F11: 'Owner Name',         F12: 'Same Source',
  F13: 'Reg Date Gap',
};

/* Risk thresholds — GREEN ≥ 0.7 · YELLOW 0.4–0.69 · RED < 0.4 */
const featureRisk = (val: number): { color: string; bg: string; label: string } => {
  if (val >= 0.7) return { color: '#52c41a', bg: '#f6ffed', label: 'High match' };
  if (val >= 0.4) return { color: '#faad14', bg: '#fffbe6', label: 'Partial match' };
  return              { color: '#f5222d', bg: '#fff1f0', label: 'Low / mismatch' };
};

const DECISION_COLORS: Record<string, string> = {
  CONFIRM_MATCH:     '#52c41a',
  CONFIRM_NON_MATCH: '#f5222d',
  CONFIRM_PARTIAL:   '#faad14',
};
const DECISION_LABELS: Record<string, string> = {
  CONFIRM_MATCH:     'Match',
  CONFIRM_NON_MATCH: 'Non-Match',
  CONFIRM_PARTIAL:   'Partial',
};

const ReviewQueueView: React.FC = () => {
  const [activeTab, setActiveTab]             = useState<'pending' | 'reviewed'>('pending');
  const [tasks, setTasks]                     = useState<any[]>([]);
  const [reviewedTasks, setReviewedTasks]     = useState<any[]>([]);
  const [loading, setLoading]                 = useState(false);
  const [reviewedLoading, setReviewedLoading] = useState(false);
  const [selectedTask, setSelectedTask]       = useState<any>(null);
  const [taskLoading, setTaskLoading]         = useState(false);
  const [stats, setStats]                     = useState<any>({});
  const [pendingCount, setPendingCount]       = useState(0);
  const [decidedCount, setDecidedCount]       = useState(0);

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const res = await reviewApi.getQueue('PENDING', 1, 50);
      setTasks(res.data.tasks || []);
      setPendingCount(res.data.total || 0);
    } catch { /* silent */ }
    setLoading(false);
  };

  const fetchReviewed = async () => {
    setReviewedLoading(true);
    try {
      const res = await reviewApi.getQueue('DECIDED', 1, 50);
      setReviewedTasks(res.data.tasks || []);
      setDecidedCount(res.data.total || 0);
    } catch { /* silent */ }
    setReviewedLoading(false);
  };

  const fetchStats = async () => {
    try {
      const res = await reviewApi.getStats();
      setStats(res.data);
      setDecidedCount(res.data.decided ?? 0);
    } catch { /* silent */ }
  };

  useEffect(() => { fetchQueue(); fetchStats(); }, []);
  useEffect(() => {
    if (activeTab === 'reviewed' && reviewedTasks.length === 0) fetchReviewed();
  }, [activeTab]); // eslint-disable-line

  const handleSelect = async (taskId: string) => {
    setTaskLoading(true);
    try {
      const res = await reviewApi.getTask(taskId);
      setSelectedTask(res.data);
    } catch { /* silent */ }
    setTaskLoading(false);
  };

  const submitDecision = async (decision: string) => {
    if (!selectedTask) return;
    try {
      await reviewApi.submitDecision(selectedTask.task_id, decision);
      notification.success({ message: `Decision "${DECISION_LABELS[decision] ?? decision}" submitted.` });
      setSelectedTask(null);
      fetchQueue();
      fetchStats();
    } catch {
      notification.error({ message: 'Failed to submit decision.' });
    }
  };

  const shapData = selectedTask?.shap_values
    ? Object.entries(selectedTask.shap_values as Record<string, number>)
        .map(([feat, val]) => ({ name: FEATURE_LABELS[feat] || feat, value: val }))
        .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
        .slice(0, 10)
    : [];

  const scoreConfColor = (s: number) =>
    s >= 0.90 ? '#f5222d' : s >= 0.80 ? ORANGE : '#faad14';

  const TaskListItem: React.FC<{ task: any; isReviewed?: boolean }> = ({ task, isReviewed }) => (
    <List.Item
      onClick={() => handleSelect(task.task_id)}
      style={{
        cursor: 'pointer',
        background: selectedTask?.task_id === task.task_id
          ? (isReviewed ? '#f6ffed' : '#fff7f3')
          : 'white',
        padding: '10px 12px',
        border: `1px solid ${selectedTask?.task_id === task.task_id ? (isReviewed ? '#b7eb8f' : ORANGE + '44') : '#f0f0f0'}`,
        marginBottom: 6,
        borderRadius: 6,
        transition: 'all 0.15s',
      }}
    >
      <List.Item.Meta
        title={
          <Space size={4}>
            <Text strong style={{ fontSize: 12 }}>#{task.task_id.slice(-6)}</Text>
            {!isReviewed && (
              <Tag
                color={scoreConfColor(task.calibrated_score ?? 0)}
                style={{ fontSize: 10, padding: '0 4px' }}
              >
                {((task.calibrated_score ?? 0) * 100).toFixed(0)}%
              </Tag>
            )}
            {isReviewed && <CheckOutlined style={{ color: '#52c41a', fontSize: 11 }} />}
          </Space>
        }
        description={
          task.ai_teaser
            ? <Text type="secondary" style={{ fontSize: 11 }}>{task.ai_teaser}</Text>
            : <Text type="secondary" style={{ fontSize: 11 }}>
                {task.pair_record_a?.split(':')[0]} ↔ {task.pair_record_b?.split(':')[0]}
              </Text>
        }
      />
    </List.Item>
  );

  return (
    <div>
      {/* Stats bar */}
      <Row gutter={16} style={{ marginBottom: 20 }}>
        {[
          { label: 'Queue Depth',    value: pendingCount ?? '—',                                          color: '#cf1322' },
          { label: 'Auto-Link Rate', value: stats.auto_link_rate_pct != null ? `${stats.auto_link_rate_pct}%` : '—', color: '#52c41a' },
          { label: 'Decided',        value: decidedCount ?? '—',                                          color: '#1677ff' },
          { label: 'Auto-Links',     value: stats.auto_link_count ?? '—',                                 color: '#722ed1' },
        ].map(s => (
          <Col span={6} key={s.label}>
            <Card size="small" style={{ textAlign: 'center', borderRadius: 8 }}>
              <div style={{ fontSize: 26, fontWeight: 800, color: s.color, fontFamily: 'monospace' }}>{s.value}</div>
              <div style={{ color: '#999', fontSize: 11 }}>{s.label}</div>
            </Card>
          </Col>
        ))}
      </Row>

      {stats.ai_insights && (
        <Alert
          message={<><RobotOutlined /> AI Insight</>}
          description={stats.ai_insights}
          type="info" showIcon
          style={{ marginBottom: 16, borderRadius: 8 }}
        />
      )}

      <Row gutter={20}>
        {/* Queue list */}
        <Col span={8}>
          <Tabs
            activeKey={activeTab}
            onChange={k => setActiveTab(k as 'pending' | 'reviewed')}
            size="small"
            items={[
              {
                key: 'pending',
                label: <span>Pending <Badge count={pendingCount} style={{ marginLeft: 4, background: '#cf1322' }} showZero /></span>,
                children: (
                  <List loading={loading} dataSource={tasks}
                    locale={{ emptyText: 'No pending tasks' }}
                    renderItem={task => <TaskListItem task={task} />}
                  />
                ),
              },
              {
                key: 'reviewed',
                label: <span>Reviewed <Badge count={decidedCount} style={{ marginLeft: 4, background: '#52c41a' }} showZero /></span>,
                children: (
                  <List loading={reviewedLoading} dataSource={reviewedTasks}
                    locale={{ emptyText: 'No reviewed tasks yet' }}
                    renderItem={task => <TaskListItem task={task} isReviewed />}
                  />
                ),
              },
            ]}
          />
        </Col>

        {/* Detail panel */}
        <Col span={16}>
          {taskLoading ? (
            <div style={{ textAlign: 'center', marginTop: 80 }}><Spin size="large" /></div>
          ) : selectedTask ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                <Title level={4} style={{ margin: 0 }}>Review Task</Title>
                <Tag color={scoreConfColor(selectedTask.calibrated_score ?? 0)} style={{ fontFamily: 'monospace' }}>
                  {((selectedTask.calibrated_score ?? 0) * 100).toFixed(0)}% confidence
                </Tag>
                {selectedTask.status === 'DECIDED' && selectedTask.decision && (
                  <Tag color={DECISION_COLORS[selectedTask.decision] ?? 'default'}>
                    {DECISION_LABELS[selectedTask.decision] ?? selectedTask.decision}
                  </Tag>
                )}
              </div>

              {/* AI explanation */}
              {selectedTask.ai_explanation && (
                <Alert
                  message={<><RobotOutlined /> AI Analysis</>}
                  description={selectedTask.ai_explanation}
                  type="warning" showIcon
                  style={{ marginBottom: 14, borderRadius: 8 }}
                />
              )}

              {/* Side-by-side records */}
              <Row gutter={12} style={{ marginBottom: 14 }}>
                {(['record_a', 'record_b'] as const).map((key, idx) => (
                  <Col span={12} key={key}>
                    <Card
                      title={idx === 0 ? 'Record A' : 'Record B'}
                      size="small"
                      styles={{ header: {
                        background: idx === 0 ? '#e6f7ff' : '#f6ffed',
                        fontWeight: 700, fontSize: 13,
                      } }}
                      style={{ borderRadius: 8 }}
                    >
                      {selectedTask[key] && typeof selectedTask[key] === 'object'
                        ? Object.entries(selectedTask[key])
                            .filter(([k]) => k !== 'error' && k !== 'note')
                            .map(([k, v]) => (
                              <div key={k} style={{ marginBottom: 3, fontSize: 12 }}>
                                <Text strong style={{ textTransform: 'capitalize', color: '#555' }}>{k}: </Text>
                                <Text>{String(v ?? '—')}</Text>
                              </div>
                            ))
                        : <Text type="secondary">{selectedTask[key === 'record_a' ? 'pair_record_a' : 'pair_record_b']}</Text>
                      }
                    </Card>
                  </Col>
                ))}
              </Row>

              {/* Feature scores with risk indicators */}
              {selectedTask.feature_scores && Object.keys(selectedTask.feature_scores).length > 0 && (
                <Card title="Feature Scores — Risk Indicators" size="small" style={{ marginBottom: 14, borderRadius: 8 }}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {Object.entries(selectedTask.feature_scores as Record<string, number>).map(([k, v]) => {
                      const risk = featureRisk(v);
                      return (
                        <Tooltip
                          key={k}
                          title={`${FEATURE_LABELS[k] || k}: ${v?.toFixed(3)} — ${risk.label}`}
                        >
                          <div style={{
                            display: 'flex', alignItems: 'center', gap: 5,
                            padding: '4px 10px', borderRadius: 20,
                            background: risk.bg,
                            border: `1px solid ${risk.color}44`,
                            cursor: 'default',
                          }}>
                            <div style={{ width: 7, height: 7, borderRadius: '50%', background: risk.color, flexShrink: 0 }} />
                            <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#333' }}>
                              {FEATURE_LABELS[k] || k}
                            </span>
                            <span style={{ fontSize: 11, fontWeight: 700, color: risk.color, fontFamily: 'monospace' }}>
                              {v?.toFixed(2)}
                            </span>
                          </div>
                        </Tooltip>
                      );
                    })}
                  </div>
                  {/* Risk legend */}
                  <div style={{ display: 'flex', gap: 16, marginTop: 10 }}>
                    {[
                      { color: '#52c41a', bg: '#f6ffed', label: 'High match  ≥ 0.70' },
                      { color: '#faad14', bg: '#fffbe6', label: 'Partial  0.40–0.69' },
                      { color: '#f5222d', bg: '#fff1f0', label: 'Low / mismatch  < 0.40' },
                    ].map(r => (
                      <div key={r.label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <div style={{ width: 7, height: 7, borderRadius: '50%', background: r.color }} />
                        <Text style={{ fontSize: 10, color: '#888' }}>{r.label}</Text>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* SHAP waterfall */}
              {shapData.length > 0 && (
                <Card title="Why this score? — SHAP Feature Contributions" size="small" style={{ marginBottom: 14, borderRadius: 8 }}>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={shapData} layout="vertical" margin={{ left: 130, right: 20 }}>
                      <XAxis type="number" domain={[-0.5, 0.5]} tickFormatter={v => v.toFixed(2)} tick={{ fontSize: 10 }} />
                      <YAxis type="category" dataKey="name" width={125} tick={{ fontSize: 10 }} />
                      <ReTooltip formatter={(v: number) => v.toFixed(4)} />
                      <Bar dataKey="value">
                        {shapData.map((entry, i) => (
                          <Cell key={i} fill={entry.value >= 0 ? '#52c41a' : '#f5222d'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              )}

              {/* Decision buttons */}
              {selectedTask.status !== 'DECIDED' && (
                <>
                  <Divider style={{ margin: '12px 0' }} />
                  <Space wrap>
                    <Button
                      type="primary"
                      icon={<CheckCircleOutlined />}
                      onClick={() => submitDecision('CONFIRM_MATCH')}
                      style={{ background: '#52c41a', borderColor: '#52c41a', height: 38 }}
                    >
                      Confirm Match
                    </Button>
                    <Button
                      danger
                      icon={<CloseCircleOutlined />}
                      onClick={() => submitDecision('CONFIRM_NON_MATCH')}
                      style={{ height: 38 }}
                    >
                      Confirm Non-Match
                    </Button>
                    <Button
                      onClick={() => submitDecision('CONFIRM_PARTIAL')}
                      style={{ borderColor: '#faad14', color: '#faad14', height: 38 }}
                    >
                      Partial Match
                    </Button>
                  </Space>
                </>
              )}

              {selectedTask.status === 'DECIDED' && (
                <Alert
                  type="success" showIcon
                  message={`Decision recorded: ${DECISION_LABELS[selectedTask.decision] ?? selectedTask.decision}`}
                  style={{ marginTop: 12, borderRadius: 8 }}
                />
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', height: '60vh', alignItems: 'center', justifyContent: 'center' }}>
              <Text type="secondary" style={{ fontSize: 15 }}>← Select a task from the queue to review</Text>
            </div>
          )}
        </Col>
      </Row>
    </div>
  );
};

export default ReviewQueueView;
