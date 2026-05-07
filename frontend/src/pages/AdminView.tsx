import React, { useState, useEffect, useRef } from 'react';
import {
  Card, Button, Slider, Table, Tag, Typography, Row, Col,
  Progress, Alert, Divider, Space, notification, Tooltip, Badge
} from 'antd';
import {
  Play, RefreshCw, Activity, Shield, Clock, CheckCircle, XCircle, AlertTriangle
} from 'lucide-react';
import { adminApi } from '../api';

const { Title, Text } = Typography;
const ORANGE = '#FF6B2C';

const SectionTitle: React.FC<{ icon: React.ReactNode; text: string }> = ({ icon, text }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
    <span style={{ color: ORANGE }}>{icon}</span>
    <Title level={5} style={{ margin: 0 }}>{text}</Title>
  </div>
);

const AdminView: React.FC = () => {
  const [modelStats, setModelStats]       = useState<any>(null);
  const [auditLog, setAuditLog]           = useState<any[]>([]);
  const [pipelineState, setPipelineState] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [pipelineProgress, setPipelineProgress] = useState(0);
  const [pipelineMsg, setPipelineMsg]     = useState('');
  const [taskId, setTaskId]               = useState<string | null>(null);
  const [autoThresh, setAutoThresh]       = useState(0.95);
  const [reviewThresh, setReviewThresh]   = useState(0.75);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchModelStats();
    fetchAuditLog();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const fetchModelStats = async () => {
    try {
      const res = await adminApi.getModelStats();
      const d = res.data;
      setModelStats(d);
      setAutoThresh(d.auto_link_threshold ?? 0.95);
      setReviewThresh(d.review_threshold ?? 0.75);
    } catch { /* silent */ }
  };

  const fetchAuditLog = async () => {
    try {
      const res = await adminApi.getAuditLog();
      setAuditLog(res.data.logs || []);
    } catch { /* silent */ }
  };

  const triggerPipeline = async () => {
    setPipelineState('running');
    setPipelineProgress(5);
    setPipelineMsg('Queuing pipeline job…');
    try {
      const res = await adminApi.triggerPipeline();
      const id = res.data.task_id;
      setTaskId(id);
      pollRef.current = setInterval(async () => {
        try {
          const s = await adminApi.getPipelineStatus(id);
          const { state, step, detail } = s.data;
          if (state === 'PROGRESS') {
            const steps: Record<string, number> = {
              ingest: 15, normalise: 30, block: 45,
              score: 65, cluster: 80, activity: 92, done: 100,
            };
            setPipelineProgress(steps[step] ?? 50);
            setPipelineMsg(detail ?? step);
          } else if (state === 'SUCCESS') {
            setPipelineProgress(100);
            setPipelineMsg('Pipeline complete');
            setPipelineState('done');
            clearInterval(pollRef.current!);
            notification.success({ message: 'Pipeline finished successfully' });
            fetchAuditLog();
          } else if (state === 'FAILURE') {
            setPipelineState('error');
            setPipelineMsg(s.data.error ?? 'Unknown error');
            clearInterval(pollRef.current!);
          }
        } catch { /* keep polling */ }
      }, 2000);
    } catch (e: any) {
      setPipelineState('error');
      setPipelineMsg(e?.response?.data?.detail ?? 'Failed to start pipeline');
    }
  };

  const auditColumns = [
    {
      title: 'Event',
      dataIndex: 'event_type',
      key: 'event_type',
      render: (v: string) => {
        const color = v.includes('decision') ? 'orange' : v.includes('pipeline') ? 'blue' : 'default';
        return <Tag color={color} style={{ fontFamily: 'monospace', fontSize: 11 }}>{v}</Tag>;
      },
    },
    { title: 'Actor', dataIndex: 'actor', key: 'actor', render: (v: string) => <Text code style={{ fontSize: 11 }}>{v}</Text> },
    { title: 'Target', dataIndex: 'target_id', key: 'target_id', render: (v: string) => <Text style={{ fontSize: 11, color: '#888' }}>{v ?? '—'}</Text> },
    {
      title: 'Timestamp', dataIndex: 'timestamp', key: 'timestamp',
      render: (v: string) => <Text style={{ fontSize: 11, color: '#888' }}>{v ? new Date(v).toLocaleString('en-IN') : '—'}</Text>,
    },
  ];

  const formatDate = (iso?: string) => {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
    catch { return iso; }
  };

  return (
    <div>
      {/* Page header */}
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0, fontFamily: 'monospace' }}>Admin Console</Title>
        <Text type="secondary" style={{ fontSize: 13 }}>Pipeline control · Threshold management · Audit log</Text>
      </div>

      <Row gutter={[20, 20]}>
        {/* Left column */}
        <Col xs={24} lg={14}>

          {/* Model Health */}
          <Card style={{ marginBottom: 20, borderRadius: 8 }}>
            <SectionTitle icon={<Activity size={16} />} text="Entity Resolution — Model Health" />
            <Row gutter={[16, 16]}>
              {[
                { label: 'Model Version',      value: modelStats?.model_version ?? '—' },
                { label: 'Last Retrained',      value: formatDate(modelStats?.last_retrain) },
                { label: 'Validation AUC',      value: modelStats?.val_auc != null ? modelStats.val_auc.toFixed(4) : '—' },
                { label: 'Validation F1',       value: modelStats?.val_f1  != null ? modelStats.val_f1.toFixed(4)  : '—' },
                { label: 'Auto-Link Threshold', value: modelStats?.auto_link_threshold?.toFixed(2) ?? '—' },
                { label: 'Review Threshold',    value: modelStats?.review_threshold?.toFixed(2)    ?? '—' },
              ].map(s => (
                <Col span={8} key={s.label}>
                  <div style={{ background: '#fafafa', borderRadius: 6, padding: '10px 14px' }}>
                    <div style={{ fontSize: 11, color: '#999', marginBottom: 3 }}>{s.label}</div>
                    <div style={{ fontWeight: 700, fontSize: 18, color: ORANGE, fontFamily: 'monospace' }}>{s.value}</div>
                  </div>
                </Col>
              ))}
            </Row>
          </Card>

          {/* Threshold sliders */}
          <Card style={{ marginBottom: 20, borderRadius: 8 }}>
            <SectionTitle icon={<Shield size={16} />} text="Threshold Configuration" />
            <div style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <Text style={{ fontSize: 13 }}>Auto-Link Threshold</Text>
                <Text strong style={{ color: ORANGE, fontFamily: 'monospace' }}>{autoThresh.toFixed(2)}</Text>
              </div>
              <Slider
                min={0.5} max={1.0} step={0.01}
                value={autoThresh}
                onChange={setAutoThresh}
                trackStyle={{ background: ORANGE }}
                handleStyle={{ borderColor: ORANGE }}
                tooltip={{ formatter: (v?: number) => v?.toFixed(2) }}
              />
              <Text type="secondary" style={{ fontSize: 11 }}>
                Pairs scoring ≥ {autoThresh.toFixed(2)} are auto-linked without review
              </Text>
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <Text style={{ fontSize: 13 }}>Review Queue Threshold</Text>
                <Text strong style={{ color: '#faad14', fontFamily: 'monospace' }}>{reviewThresh.toFixed(2)}</Text>
              </div>
              <Slider
                min={0.3} max={autoThresh - 0.01} step={0.01}
                value={reviewThresh}
                onChange={setReviewThresh}
                trackStyle={{ background: '#faad14' }}
                handleStyle={{ borderColor: '#faad14' }}
                tooltip={{ formatter: (v?: number) => v?.toFixed(2) }}
              />
              <Text type="secondary" style={{ fontSize: 11 }}>
                Pairs between {reviewThresh.toFixed(2)}–{autoThresh.toFixed(2)} go to human review
              </Text>
            </div>
            <Alert
              type="info"
              showIcon
              message={
                <span style={{ fontSize: 12 }}>
                  Threshold changes require a pipeline re-run to take effect.
                  Pairs below <strong>{reviewThresh.toFixed(2)}</strong> are kept separate automatically.
                </span>
              }
            />
          </Card>

          {/* Audit Log */}
          <Card style={{ borderRadius: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <SectionTitle icon={<Clock size={16} />} text="Audit Log" />
              <Button size="small" icon={<RefreshCw size={13} />} onClick={fetchAuditLog} style={{ fontSize: 12 }}>
                Refresh
              </Button>
            </div>
            <Table
              dataSource={auditLog}
              columns={auditColumns}
              rowKey={(r, i) => String(i)}
              size="small"
              pagination={{ pageSize: 8, size: 'small' }}
              locale={{ emptyText: 'No audit events yet — decisions will appear here' }}
            />
          </Card>
        </Col>

        {/* Right column — Pipeline */}
        <Col xs={24} lg={10}>
          <Card style={{ borderRadius: 8, marginBottom: 20 }}>
            <SectionTitle icon={<Play size={16} />} text="Pipeline Control" />

            <div style={{
              background: '#0f0f0f',
              borderRadius: 8,
              padding: 20,
              marginBottom: 16,
              fontFamily: 'monospace',
              fontSize: 12,
              color: '#888',
              minHeight: 80,
            }}>
              {pipelineState === 'idle' && (
                <span style={{ color: '#444' }}>No pipeline running. Click "Run Pipeline" to start.</span>
              )}
              {pipelineState === 'running' && (
                <div>
                  <span style={{ color: ORANGE }}>● </span>
                  <span style={{ color: '#ccc' }}>RUNNING</span>
                  {pipelineMsg && <div style={{ marginTop: 6, color: '#666' }}>{pipelineMsg}</div>}
                  {taskId && <div style={{ marginTop: 4, color: '#444', fontSize: 10 }}>task: {taskId}</div>}
                </div>
              )}
              {pipelineState === 'done' && (
                <div>
                  <span style={{ color: '#52c41a' }}>✓ </span>
                  <span style={{ color: '#52c41a' }}>COMPLETE</span>
                  <div style={{ marginTop: 6, color: '#666' }}>{pipelineMsg}</div>
                </div>
              )}
              {pipelineState === 'error' && (
                <div>
                  <span style={{ color: '#f5222d' }}>✗ </span>
                  <span style={{ color: '#f5222d' }}>FAILED</span>
                  <div style={{ marginTop: 6, color: '#f5222d', fontSize: 11 }}>{pipelineMsg}</div>
                </div>
              )}
            </div>

            {(pipelineState === 'running' || pipelineState === 'done') && (
              <Progress
                percent={pipelineProgress}
                strokeColor={pipelineState === 'done' ? '#52c41a' : ORANGE}
                style={{ marginBottom: 16 }}
                size="small"
              />
            )}

            <Space direction="vertical" style={{ width: '100%' }} size={8}>
              <Button
                type="primary"
                icon={<Play size={14} />}
                onClick={triggerPipeline}
                loading={pipelineState === 'running'}
                disabled={pipelineState === 'running'}
                block
                style={{ background: ORANGE, borderColor: ORANGE, fontFamily: 'monospace', height: 40 }}
              >
                Run Full Pipeline
              </Button>
              <Button
                icon={<RefreshCw size={14} />}
                onClick={async () => {
                  try {
                    await adminApi.triggerReroute();
                    notification.success({ message: 'Event rerouting queued' });
                    fetchAuditLog();
                  } catch { notification.error({ message: 'Failed to queue reroute' }); }
                }}
                block
                style={{ fontFamily: 'monospace', height: 38 }}
              >
                Reroute Events Only
              </Button>
            </Space>

            <Divider style={{ margin: '16px 0' }} />

            {/* Pipeline stages legend */}
            <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 10 }}>PIPELINE STAGES</Text>
            {[
              { step: 'Ingest & Standardise',  pct: 15 },
              { step: 'Multi-Key Blocking',    pct: 30 },
              { step: 'Feature Extraction',    pct: 45 },
              { step: 'LightGBM Scoring',      pct: 65 },
              { step: 'UBID Clustering',       pct: 80 },
              { step: 'Activity Scoring',      pct: 92 },
              { step: 'Complete',              pct: 100 },
            ].map(s => (
              <div key={s.step} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                  background: pipelineProgress >= s.pct ? '#52c41a' :
                               pipelineState === 'running' && pipelineProgress >= s.pct - 15 ? ORANGE : '#333',
                }} />
                <Text style={{ fontSize: 11, color: pipelineProgress >= s.pct ? '#ccc' : '#555', fontFamily: 'monospace' }}>
                  {s.step}
                </Text>
              </div>
            ))}
          </Card>

          {/* Threshold routing legend */}
          <Card style={{ borderRadius: 8 }}>
            <SectionTitle icon={<AlertTriangle size={16} />} text="Routing Rules" />
            {[
              { color: '#52c41a', label: `Score ≥ ${autoThresh.toFixed(2)}`, action: 'Auto-link → UBID Registry' },
              { color: '#faad14', label: `Score ${reviewThresh.toFixed(2)}–${autoThresh.toFixed(2)}`, action: 'Human review queue + SHAP card' },
              { color: '#f5222d', label: `Score < ${reviewThresh.toFixed(2)}`, action: 'Keep separate' },
              { color: '#722ed1', label: 'PAN / GSTIN mismatch', action: 'Force separate — hard veto' },
            ].map(r => (
              <div key={r.label} style={{ display: 'flex', gap: 10, marginBottom: 10, alignItems: 'flex-start' }}>
                <div style={{ width: 10, height: 10, borderRadius: 2, background: r.color, marginTop: 3, flexShrink: 0 }} />
                <div>
                  <Text style={{ fontSize: 12, fontFamily: 'monospace', fontWeight: 600 }}>{r.label}</Text>
                  <div style={{ fontSize: 11, color: '#888' }}>{r.action}</div>
                </div>
              </div>
            ))}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AdminView;
