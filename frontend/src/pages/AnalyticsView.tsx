import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Typography, Alert } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import { TrendingUp, Link2, Users, CheckSquare, Activity, Cpu } from 'lucide-react';
import { reviewApi, adminApi } from '../api';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Legend, RadialBarChart, RadialBar,
} from 'recharts';

const { Title, Text } = Typography;

const ORANGE  = '#FF6B2C';
const STATUS_COLORS: Record<string, string> = {
  Active:  '#52c41a',
  Dormant: '#faad14',
  Closed:  '#f5222d',
  Unknown: '#8c8c8c',
};

const KpiCard: React.FC<{
  icon: React.ReactNode; label: string; value: string | number;
  sub?: string; color?: string;
}> = ({ icon, label, value, sub, color = ORANGE }) => (
  <Card style={{ borderRadius: 8, height: '100%' }} styles={{ body: { padding: '18px 20px' } }}>
    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
      <div>
        <Text style={{ fontSize: 12, color: '#999', display: 'block', marginBottom: 6 }}>{label}</Text>
        <div style={{ fontSize: 28, fontWeight: 800, color, fontFamily: 'monospace', lineHeight: 1 }}>{value}</div>
        {sub && <Text style={{ fontSize: 11, color: '#bbb', marginTop: 4, display: 'block' }}>{sub}</Text>}
      </div>
      <div style={{ color, opacity: 0.8 }}>{icon}</div>
    </div>
  </Card>
);

const AnalyticsView: React.FC = () => {
  const [stats, setStats]           = useState<any>({});
  const [modelStats, setModelStats] = useState<any>({});

  useEffect(() => {
    reviewApi.getStats().then(res => setStats(res.data)).catch(console.error);
    adminApi.getModelStats().then(res => setModelStats(res.data)).catch(console.error);
  }, []);

  const pieData = [
    { name: 'Active',  value: stats.active_count  ?? 0 },
    { name: 'Dormant', value: stats.dormant_count  ?? 0 },
    { name: 'Closed',  value: stats.closed_count   ?? 0 },
    { name: 'Unknown', value: stats.unknown_count  ?? 0 },
  ].filter(d => d.value > 0);

  const linkBarData = [
    { name: 'Auto-Links',   value: stats.auto_link_count   ?? 0, fill: '#52c41a' },
    { name: 'Manual Links', value: stats.manual_link_count ?? 0, fill: ORANGE },
    { name: 'Pending',      value: stats.queue_depth       ?? 0, fill: '#faad14' },
    { name: 'Decided',      value: stats.decided           ?? 0, fill: '#1677ff' },
  ];

  const aucPct = Math.round((modelStats.val_auc ?? 0) * 100);
  const radialData = [{ name: 'AUC', value: aucPct, fill: ORANGE }];

  const formatDate = (iso?: string) => {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
    catch { return iso; }
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0, fontFamily: 'monospace' }}>Analytics & Operations</Title>
        <Text type="secondary" style={{ fontSize: 13 }}>Live platform metrics · Entity resolution health · Activity intelligence</Text>
      </div>

      {stats.ai_insights && (
        <Alert
          message={<><RobotOutlined /> AI Insight</>}
          description={stats.ai_insights}
          type="info" showIcon
          style={{ marginBottom: 20, borderRadius: 8 }}
        />
      )}

      {/* KPI row */}
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={12} sm={8} lg={4}>
          <KpiCard icon={<CheckSquare size={22} />} label="Review Queue" value={stats.queue_depth ?? 0} sub="pending tasks" color="#cf1322" />
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <KpiCard icon={<TrendingUp size={22} />} label="Auto-Link Rate" value={`${stats.auto_link_rate_pct ?? 0}%`} sub="of all pairs" color="#52c41a" />
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <KpiCard icon={<Link2 size={22} />} label="Auto-Links" value={stats.auto_link_count ?? 0} sub="total linked" color={ORANGE} />
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <KpiCard icon={<Users size={22} />} label="Manual Links" value={stats.manual_link_count ?? 0} sub="reviewer decided" color="#722ed1" />
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <KpiCard icon={<CheckSquare size={22} />} label="Decided" value={stats.decided ?? 0} sub="total reviewed" color="#1677ff" />
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <KpiCard icon={<Cpu size={22} />} label="Model AUC" value={modelStats.val_auc != null ? modelStats.val_auc.toFixed(4) : '—'} sub="validation score" color={ORANGE} />
        </Col>
      </Row>

      <Row gutter={[20, 20]} style={{ marginBottom: 20 }}>
        {/* Activity status pie */}
        <Col xs={24} lg={10}>
          <Card title="Activity Status Distribution" style={{ borderRadius: 8, height: '100%' }}>
            <Row gutter={8} style={{ marginBottom: 12 }}>
              {pieData.map(d => (
                <Col key={d.name} span={12}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: STATUS_COLORS[d.name] ?? '#888' }} />
                    <Text style={{ fontSize: 12 }}>{d.name}</Text>
                    <Text strong style={{ marginLeft: 'auto', fontSize: 13, color: STATUS_COLORS[d.name] ?? '#888' }}>{d.value}</Text>
                  </div>
                </Col>
              ))}
            </Row>
            <div style={{ height: 240 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%" cy="50%"
                    innerRadius={55} outerRadius={95}
                    dataKey="value"
                    paddingAngle={3}
                    label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {pieData.map((d, i) => (
                      <Cell key={i} fill={STATUS_COLORS[d.name] ?? '#888'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => [v, 'UBIDs']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>

        {/* Link statistics bar */}
        <Col xs={24} lg={14}>
          <Card title="Entity Resolution — Link Statistics" style={{ borderRadius: 8, height: '100%' }}>
            <div style={{ height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={linkBarData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[5, 5, 0, 0]}>
                    {linkBarData.map((d, i) => (
                      <Cell key={i} fill={d.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>
      </Row>

      {/* Model Health + AUC gauge */}
      <Row gutter={[20, 20]}>
        <Col xs={24} lg={8}>
          <Card title="Model Validation AUC" style={{ borderRadius: 8, textAlign: 'center' }}>
            <div style={{ height: 180 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart
                  cx="50%" cy="80%"
                  innerRadius="60%" outerRadius="100%"
                  startAngle={180} endAngle={0}
                  data={radialData}
                >
                  <RadialBar background dataKey="value" cornerRadius={6} fill={ORANGE} />
                  <Tooltip formatter={(v: number) => [`${v}%`, 'AUC']} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <div style={{ marginTop: -30 }}>
              <div style={{ fontSize: 32, fontWeight: 800, color: ORANGE, fontFamily: 'monospace' }}>
                {modelStats.val_auc != null ? modelStats.val_auc.toFixed(4) : '—'}
              </div>
              <Text type="secondary" style={{ fontSize: 12 }}>Validation AUC</Text>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          <Card title="Entity Resolution — Model Health" style={{ borderRadius: 8 }}>
            <Row gutter={[16, 16]}>
              {[
                { label: 'Model Version',        value: modelStats.model_version ?? '—' },
                { label: 'Last Retrained',        value: formatDate(modelStats.last_retrain) },
                { label: 'Validation F1',         value: modelStats.val_f1 != null ? modelStats.val_f1.toFixed(4) : '—' },
                { label: 'Auto-Link Threshold',   value: modelStats.auto_link_threshold?.toFixed(2) ?? '—' },
                { label: 'Review Threshold',      value: modelStats.review_threshold?.toFixed(2)    ?? '—' },
                { label: 'Train Size',            value: modelStats.train_size ?? '—' },
              ].map(s => (
                <Col span={8} key={s.label}>
                  <div style={{ background: '#fafafa', borderRadius: 6, padding: '10px 14px' }}>
                    <Text style={{ fontSize: 11, color: '#999', display: 'block', marginBottom: 3 }}>{s.label}</Text>
                    <Text strong style={{ fontSize: 16, fontFamily: 'monospace', color: '#222' }}>{s.value}</Text>
                  </div>
                </Col>
              ))}
            </Row>
            <div style={{ marginTop: 16, padding: '10px 14px', background: `${ORANGE}10`, borderRadius: 6, borderLeft: `3px solid ${ORANGE}` }}>
              <Text style={{ fontSize: 12 }}>
                <strong>Routing: </strong>
                Score ≥ {modelStats.auto_link_threshold ?? 0.95} → Auto-link ·
                {' '}{modelStats.review_threshold ?? 0.75}–{modelStats.auto_link_threshold ?? 0.95} → Review queue ·
                {' '}Below {modelStats.review_threshold ?? 0.75} → Keep separate ·
                {' '}PAN/GSTIN mismatch → Force separate (hard veto)
              </Text>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AnalyticsView;
