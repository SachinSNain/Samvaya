import React, { useState, useEffect } from 'react';
import {
  Tag, Typography, Descriptions,
  Alert, Spin, Row, Col, Progress, Tabs, Card, Divider,
} from 'antd';
import {
  ShieldCheck, ShieldAlert, ShieldOff, HelpCircle, Database,
  Link2, Phone, MapPin, User, Calendar, Sparkles,
  Zap, Activity, BarChart2, FileText, Eye,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip as ReTooltip,
  ResponsiveContainer, Cell, AreaChart, Area, CartesianGrid, ReferenceLine,
  PieChart, Pie,
} from 'recharts';
import { useParams, Link } from 'react-router-dom';
import SHAPVisualizations from '../components/SHAPVisualizations';
import FeatureMatrix from '../components/FeatureMatrix';
import CrossDatabaseComparison from '../components/CrossDatabaseComparison';
import { ubidApi, activityApi } from '../api';

const { Title, Text } = Typography;

const ORANGE      = '#FF6B2C';
const SIDEBAR_BG  = '#0f0f0f';
const SIDEBAR_BORDER = '#1f1f1f';
const CARD_SHADOW = '0 1px 4px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.06)';

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: '#52c41a', DORMANT: '#faad14',
  CLOSED_SUSPECTED: '#f5222d', CLOSED_CONFIRMED: '#820014', UNKNOWN: '#8c8c8c',
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  ACTIVE:           <ShieldCheck size={15} color="#52c41a" />,
  DORMANT:          <ShieldAlert size={15} color="#faad14" />,
  CLOSED_SUSPECTED: <ShieldOff  size={15} color="#f5222d" />,
  CLOSED_CONFIRMED: <ShieldOff  size={15} color="#820014" />,
  UNKNOWN:          <HelpCircle size={15} color="#8c8c8c" />,
};

const DEPT_COLORS: Record<string, string> = {
  shop_establishment: '#1677ff',
  factories:          ORANGE,
  labour:             '#722ed1',
  kspcb:              '#52c41a',
};

const FEATURE_LABELS: Record<string, string> = {
  F01: 'Name Jaro-Winkler', F02: 'Token Set Ratio',  F03: 'Abbreviation Match',
  F04: 'PAN Match',          F05: 'GSTIN Match',       F06: 'Pin Code Match',
  F07: 'Geo Distance (m)',   F08: 'Address Overlap',   F09: 'Phone Match',
  F10: 'NIC Industry',       F11: 'Owner Name',        F12: 'Same Source',
  F13: 'Reg Date Gap',
};

const FIELD_LABELS: Record<string, string> = {
  se_reg_no: 'SE Reg No', factory_licence_no: 'Licence No', employer_code: 'Employer Code',
  consent_order_no: 'Consent Order No', business_name: 'Business Name', factory_name: 'Factory Name',
  employer_name: 'Employer Name', unit_name: 'Unit Name', owner_name: 'Owner Name', address: 'Address',
  pin_code: 'Pin Code', pan: 'PAN', gstin: 'GSTIN', phone: 'Phone', trade_category: 'Trade Category',
  product_description: 'Product / Description', industry_type: 'Industry Type', consent_type: 'Consent Type',
  nic_code: 'NIC Code', num_workers: 'Workers', num_employees: 'Employees', status: 'Status',
  registration_date: 'Registration Date', licence_valid_until: 'Licence Valid Until',
  consent_valid_until: 'Consent Valid Until',
};

const SKIP_FIELDS = new Set(['id', 'ubid', 'source_system', 'source_record_id', 'created_at', 'updated_at']);

/* Pick a lucide icon for each event type keyword */
const eventIcon = (eventType: string): React.ReactNode => {
  const t = eventType?.toLowerCase() ?? '';
  if (t.includes('electric') || t.includes('power'))    return <Zap     size={13} color={ORANGE} />;
  if (t.includes('inspect') || t.includes('visit'))     return <Eye     size={13} color="#1677ff" />;
  if (t.includes('filing') || t.includes('compliance')) return <FileText size={13} color="#722ed1" />;
  if (t.includes('activity') || t.includes('event'))    return <Activity size={13} color="#52c41a" />;
  return <BarChart2 size={13} color="#8c8c8c" />;
};

const buildTimelineChart = (events: any[]) => {
  const monthMap: Record<string, number> = {};
  events.forEach(e => {
    const m = e.event_timestamp?.slice(0, 7);
    if (m) monthMap[m] = (monthMap[m] ?? 0) + 1;
  });
  return Object.entries(monthMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .slice(-12)
    .map(([month, count]) => ({ month, count }));
};

const buildWaterfall = (shapValues: Record<string, number>, baseScore: number) => {
  const sorted = Object.entries(shapValues)
    .map(([k, v]) => ({ name: FEATURE_LABELS[k] || k, value: v }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  const items: { name: string; base: number; value: number; fill: string }[] = [];
  let running = baseScore;
  sorted.forEach(({ name, value }) => {
    items.push({
      name,
      base:  value >= 0 ? running : running + value,
      value: Math.abs(value),
      fill:  value >= 0 ? '#52c41a' : '#f5222d',
    });
    running += value;
  });
  return { items, finalScore: running };
};

const aggregateDetails = (sourceRecords: any[]) => {
  const d: Record<string, string> = {};
  sourceRecords.forEach(rec => {
    const f = rec.fields ?? {};
    if (!d.owner_name      && (f.owner_name      || rec.owner_name))      d.owner_name      = f.owner_name      || rec.owner_name;
    if (!d.address         && (f.address         || rec.address))         d.address         = f.address         || rec.address;
    if (!d.phone           && (f.phone           || rec.phone))           d.phone           = f.phone           || rec.phone;
    if (!d.pin_code        && (f.pin_code        || rec.pin_code))        d.pin_code        = f.pin_code        || rec.pin_code;
    if (!d.gstin           && (f.gstin           || rec.gstin))           d.gstin           = f.gstin           || rec.gstin;
    if (!d.nic_code        && (f.nic_code        || rec.nic_code))        d.nic_code        = f.nic_code        || rec.nic_code;
    if (!d.trade_category  && (f.trade_category  || rec.trade_category))  d.trade_category  = f.trade_category  || rec.trade_category;
    if (!d.reg_date        && (f.registration_date || rec.registration_date)) d.reg_date = f.registration_date || rec.registration_date;
  });
  return d;
};

/* Thin section-title used throughout */
const SectionTitle: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div style={{
    fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
    color: '#999', marginBottom: 10, ...style,
  }}>
    {children}
  </div>
);

const UbidDetailView: React.FC = () => {
  const { ubid } = useParams<{ ubid: string }>();
  const [detail,   setDetail]   = useState<any>(null);
  const [timeline, setTimeline] = useState<any>(null);
  const [intel,    setIntel]    = useState<any>(null);
  const [loading,  setLoading]  = useState(true);
  const [shapView, setShapView] = useState<Record<number, 'simple' | 'technical'>>({});

  useEffect(() => {
    if (!ubid) return;
    Promise.all([
      ubidApi.getFullDetail(ubid),
      activityApi.getTimeline(ubid),
      ubidApi.getIntelligence(ubid),
    ]).then(([d, t, i]) => {
      setDetail(d.data);
      setTimeline(t.data);
      setIntel(i.data);
    }).catch(() => {}).finally(() => setLoading(false));
  }, [ubid]);

  const status      = detail?.activity_status ?? 'UNKNOWN';
  const statusColor = STATUS_COLOR[status] ?? '#8c8c8c';

  const toggleShapView = (i: number) =>
    setShapView(prev => ({ ...prev, [i]: prev[i] === 'technical' ? 'simple' : 'technical' }));

  return (
    <div style={{ background: '#f5f5f5', minHeight: '100%' }}>

      {/* ── Breadcrumb bar ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        marginBottom: 20, flexWrap: 'wrap',
      }}>
        <Link to="/dashboard/lookup" style={{
          color: ORANGE, fontSize: 13, fontWeight: 500, textDecoration: 'none',
          display: 'flex', alignItems: 'center', gap: 4,
        }}>
          ← UBID Directory
        </Link>
        <span style={{ color: '#bbb', fontSize: 13 }}>/</span>
        <span style={{
          fontFamily: 'monospace', fontSize: 12, color: '#555',
          background: `${ORANGE}10`, border: `1px solid ${ORANGE}30`,
          padding: '2px 10px', borderRadius: 4,
        }}>
          {ubid}
        </span>
        {detail && (
          <span style={{ fontSize: 14, fontWeight: 600, color: '#222', marginLeft: 4 }}>
            {detail.display_name}
          </span>
        )}
      </div>

      {/* ── Page body ── */}
      <div style={{ maxWidth: 1120, width: '100%' }}>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 140 }}><Spin size="large" /></div>
        ) : !detail ? (
          <Alert type="error" message="Failed to load UBID details." showIcon style={{ borderRadius: 8 }} />
        ) : (
          <>

          <Tabs 
            defaultActiveKey="overview" 
            size="large"
            items={[
              {
                key: 'overview',
                label: 'Overview',
                children: (
                  <div style={{ paddingTop: 8, paddingBottom: 40 }}>
                    {/* ══ KPI METRICS STRIP ══ */}
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: 12, marginBottom: 20
            }}>
              <div style={{ background: '#fff', borderRadius: 8, padding: '12px 16px', boxShadow: CARD_SHADOW }}>
                <Text style={{ fontSize: 11, color: '#888', display: 'block', marginBottom: 4 }}>Activity Score</Text>
                <div style={{ fontSize: 24, fontWeight: 600, color: '#1D9E75', lineHeight: 1 }}>
                  {intel?.kpi?.activity_score?.toFixed(3) ?? 'N/A'}
                </div>
                {intel?.peer_benchmark && (
                  <Text style={{ fontSize: 10, color: '#aaa', marginTop: 4, display: 'block' }}>
                    Top {100 - intel.peer_benchmark.score_percentile}% in sector
                  </Text>
                )}
              </div>
              
              <div style={{ background: '#fff', borderRadius: 8, padding: '12px 16px', boxShadow: CARD_SHADOW }}>
                <Text style={{ fontSize: 11, color: '#888', display: 'block', marginBottom: 4 }}>ER Confidence</Text>
                <div style={{ fontSize: 24, fontWeight: 600, color: '#185FA5', lineHeight: 1 }}>
                  {intel?.kpi?.er_confidence?.toFixed(3) ?? 'N/A'}
                </div>
                <Text style={{ fontSize: 10, color: '#aaa', marginTop: 4, display: 'block' }}>
                  {intel?.kpi?.er_confidence >= 0.95 ? 'AUTO_LINK' : 'REVIEW'}
                </Text>
              </div>

              <div style={{ background: '#fff', borderRadius: 8, padding: '12px 16px', boxShadow: CARD_SHADOW }}>
                <Text style={{ fontSize: 11, color: '#888', display: 'block', marginBottom: 4 }}>Linked Depts</Text>
                <div style={{ fontSize: 24, fontWeight: 600, color: '#222', lineHeight: 1 }}>
                  {intel?.kpi?.dept_count ?? 0}
                </div>
                <Text style={{ fontSize: 10, color: '#aaa', marginTop: 4, display: 'block' }}>
                  Anchor: {detail?.anchor_status}
                </Text>
              </div>

              <div style={{ background: '#fff', borderRadius: 8, padding: '12px 16px', boxShadow: CARD_SHADOW }}>
                <Text style={{ fontSize: 11, color: '#888', display: 'block', marginBottom: 4 }}>Dormancy ETA</Text>
                <div style={{ fontSize: 24, fontWeight: 600, color: '#BA7517', lineHeight: 1 }}>
                  {intel?.kpi?.dormancy_eta_days ? `${intel.kpi.dormancy_eta_days}d` : 'Stable'}
                </div>
                <Text style={{ fontSize: 10, color: '#aaa', marginTop: 4, display: 'block' }}>
                  if no new signals
                </Text>
              </div>

              <div style={{ background: '#fff', borderRadius: 8, padding: '12px 16px', boxShadow: CARD_SHADOW }}>
                <Text style={{ fontSize: 11, color: '#888', display: 'block', marginBottom: 4 }}>Anomalies</Text>
                <div style={{ fontSize: 24, fontWeight: 600, color: intel?.kpi?.anomaly_count > 0 ? '#D85A30' : '#1D9E75', lineHeight: 1 }}>
                  {intel?.kpi?.anomaly_count ?? 0}
                </div>
                <Text style={{ fontSize: 10, color: '#aaa', marginTop: 4, display: 'block' }}>
                  {intel?.anomalies?.filter((a: any) => a.severity === 'CRITICAL').length || 0} critical
                </Text>
              </div>
            </div>

            {/* ══ AI COMPLIANCE NARRATIVE ══ */}
            {intel?.llm_narrative && (
              <div style={{
                background: '#fff',
                border: `1px solid #e8e8e8`,
                borderRadius: 10,
                padding: '16px 20px',
                marginBottom: 20,
                boxShadow: CARD_SHADOW,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 12 }}>
                  <Sparkles size={16} color={ORANGE} />
                  <Text style={{ fontWeight: 600, fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.04em', color: '#555' }}>
                    LLM Compliance Narrative
                  </Text>
                  <span style={{ fontSize: 10, background: '#E1F5EE', color: '#085041', padding: '2px 8px', borderRadius: 10, marginLeft: 6 }}>
                    Gemini 2.5
                  </span>
                </div>
                <div style={{
                  background: '#fafafa',
                  borderLeft: `3px solid #1D9E75`,
                  borderRadius: '0 8px 8px 0',
                  padding: '12px 16px',
                  fontSize: 13,
                  lineHeight: 1.6,
                  color: '#333'
                }}>
                  {intel.llm_narrative}
                </div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
                  <button style={{ fontSize: 11, padding: '4px 12px', borderRadius: 20, border: '1px solid #ddd', cursor: 'pointer', background: 'transparent' }}>
                    Explain conflict ↗
                  </button>
                  <button style={{ fontSize: 11, padding: '4px 12px', borderRadius: 20, border: '1px solid #ddd', cursor: 'pointer', background: 'transparent' }}>
                    Enforcement actions ↗
                  </button>
                  <button style={{ fontSize: 11, padding: '4px 12px', borderRadius: 20, border: '1px solid #ddd', cursor: 'pointer', background: 'transparent' }}>
                    Similar cases ↗
                  </button>
                </div>
              </div>
            )}


            {/* ══ COMPANY IDENTITY & DETAILS ══ */}
            {(() => {
              const consolidated: any = {};
              detail.source_records?.forEach((rec: any) => {
                const r = rec.record_details || rec;
                if (!consolidated.business_name && r.business_name) consolidated.business_name = r.business_name;
                if (!consolidated.owner_name && r.owner_name) consolidated.owner_name = r.owner_name;
                if (!consolidated.address && r.address) consolidated.address = r.address;
                if (!consolidated.phone && r.phone) consolidated.phone = r.phone;
                if (!consolidated.pin_code && r.pin_code) consolidated.pin_code = r.pin_code;
                if (!consolidated.pan && (r.PAN || r.pan)) consolidated.pan = r.PAN || r.pan;
                if (!consolidated.gstin && (r.GSTIN || r.gstin)) consolidated.gstin = r.GSTIN || r.gstin;
              });

              return (
                <Card size="small" style={{ marginBottom: 18, borderRadius: 8, boxShadow: CARD_SHADOW }} title="Company Identity & Details">
                  <Descriptions size="small" column={{ xxl: 2, xl: 2, lg: 2, md: 1, sm: 1, xs: 1 }} labelStyle={{ color: '#999', fontSize: 12 }}>
                    <Descriptions.Item label="UBID">
                      <span style={{ fontSize: 12, fontFamily: 'monospace', color: ORANGE, fontWeight: 600 }}>{detail.ubid}</span>
                    </Descriptions.Item>
                    <Descriptions.Item label="Anchor Status">
                      <Tag color={detail.anchor_status === 'ANCHORED' ? 'blue' : 'default'} style={{ margin: 0 }}>
                        {detail.anchor_status}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="Company Name" span={2}>
                      <strong>{consolidated.business_name || detail.display_name || '—'}</strong>
                    </Descriptions.Item>
                    <Descriptions.Item label="Owner Name" span={2}>
                      {consolidated.owner_name ? <span>{consolidated.owner_name}</span> : <span style={{ color: '#aaa' }}>—</span>}
                    </Descriptions.Item>
                    <Descriptions.Item label="Address" span={2}>
                      {consolidated.address 
                        ? <span>{consolidated.address} {consolidated.pin_code && !consolidated.address.includes(consolidated.pin_code) ? `- ${consolidated.pin_code}` : ''}</span> 
                        : <span style={{ color: '#aaa' }}>—</span>}
                    </Descriptions.Item>
                    <Descriptions.Item label="Phone">
                      {consolidated.phone ? <span>{consolidated.phone}</span> : <span style={{ color: '#aaa' }}>—</span>}
                    </Descriptions.Item>
                    <Descriptions.Item label="PAN No.">
                      {detail.pan_anchor || consolidated.pan
                        ? <span>{detail.pan_anchor || consolidated.pan}</span>
                        : <span style={{ color: '#aaa' }}>—</span>}
                    </Descriptions.Item>
                    <Descriptions.Item label="GSTIN No." span={2}>
                      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4 }}>
                        {detail.gstin_anchors && detail.gstin_anchors.length > 0 ? (
                          detail.gstin_anchors.map((g: string, i: number) => (
                            <Tag key={i} style={{ fontFamily: 'monospace', margin: 0 }}>{g}</Tag>
                          ))
                        ) : consolidated.gstin ? (
                          <span>{consolidated.gstin}</span>
                        ) : <span style={{ color: '#aaa' }}>—</span>}
                      </div>
                    </Descriptions.Item>
                  </Descriptions>
                </Card>
              );
            })()}

            {/* ══ SIGNAL ANOMALY DETECTOR ══ */}
            {intel?.anomalies?.length > 0 && (
              <div style={{
                background: '#fff', borderRadius: 10, boxShadow: CARD_SHADOW,
                padding: '16px 20px', marginBottom: 18,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }}>
                  <ShieldAlert size={15} color="#555" />
                  <SectionTitle style={{ marginBottom: 0 }}>Signal Anomaly Detector</SectionTitle>
                </div>
                {intel.anomalies.map((anom: any, idx: number) => {
                  const isCrit = anom.severity === 'CRITICAL';
                  const isWarn = anom.severity === 'WARNING';
                  const isOk   = anom.severity === 'OK';
                  const color  = isCrit ? '#A32D2D' : isWarn ? '#854F0B' : '#3B6D11';
                  const bg     = isCrit ? '#FCEBEB' : isWarn ? '#FAEEDA' : '#EAF3DE';
                  
                  return (
                    <div key={idx} style={{
                      display: 'flex', alignItems: 'flex-start', gap: 10, padding: '10px 0',
                      borderBottom: idx === intel.anomalies.length - 1 ? 'none' : '1px solid #f0f0f0'
                    }}>
                      <div style={{
                        width: 28, height: 28, borderRadius: '50%', background: bg, color: color,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
                      }}>
                        {isCrit ? <ShieldOff size={14} /> : isWarn ? <Zap size={14} /> : <ShieldCheck size={14} />}
                      </div>
                      <div>
                        <Text style={{ fontWeight: 600, fontSize: 13, color: '#222', display: 'block' }}>{anom.title}</Text>
                        <Text style={{ color: '#666', fontSize: 13, display: 'block', lineHeight: 1.4, marginTop: 2 }}>{anom.description}</Text>
                        <Text style={{ fontSize: 11, color: '#999', marginTop: 4, display: 'block' }}>{anom.date} · {anom.severity}</Text>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            
            {/* Linked source records */}
            <Divider orientation="left" style={{ fontSize: 13, marginTop: 32 }}>
              Linked Department Records ({detail.source_record_count})
            </Divider>

            {detail.source_records?.map((rec: any, i: number) => {
              const businessName = rec.record_details?.business_name ?? rec.business_name;
              const address = rec.record_details?.address ?? rec.address;
              return (
                <Card
                  key={i}
                  size="small"
                  style={{ marginBottom: 10, borderRadius: 8 }}
                  bodyStyle={{ padding: '12px 16px' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Tag
                      style={{
                        background: `${DEPT_COLORS[rec.source_system] ?? '#888'}20`,
                        color: DEPT_COLORS[rec.source_system] ?? '#888',
                        border: `1px solid ${DEPT_COLORS[rec.source_system] ?? '#888'}44`,
                        fontWeight: 700, fontSize: 11, textTransform: 'uppercase',
                      }}
                    >
                      {rec.source_system?.replace(/_/g, ' ')}
                    </Tag>
                    <Text code style={{ fontSize: 11 }}>{rec.source_record_id}</Text>
                    
                    <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <Tag color={rec.link_type === 'auto' ? 'green' : 'gold'} style={{ fontSize: 10 }}>
                        {rec.link_type}
                      </Tag>
                      <Progress
                        percent={Math.round((rec.confidence ?? 0) * 100)}
                        size="small"
                        strokeColor={rec.confidence >= 0.95 ? '#52c41a' : rec.confidence >= 0.75 ? ORANGE : '#faad14'}
                        style={{ width: 80, marginRight: 8 }}
                        format={p => <span style={{ fontSize: 10 }}>{p}%</span>}
                      />
                    </div>
                  </div>
                  {(businessName || address) && (
                    <div style={{ marginTop: 8 }}>
                       <Text type="secondary" style={{ fontSize: 11 }}>Business Name: </Text>
                       <Text style={{ fontSize: 11, marginRight: 16 }}>{businessName || '—'}</Text>
                       <Text type="secondary" style={{ fontSize: 11 }}>Address: </Text>
                       <Text style={{ fontSize: 11 }}>{address || '—'}</Text>
                    </div>
                  )}
                </Card>
              );
            })}

                  </div>
                )
              },
              {
                key: 'shap',
                label: 'SHAP Analysis',
                children: (
                  <div style={{ paddingTop: 8, paddingBottom: 40 }}>
                    
            <Row gutter={16} style={{ marginBottom: 16 }}>
              {/* Dept Identity Graph */}
              <Col xs={24} lg={24}>
                <div style={{
                  background: '#fff', borderRadius: 10, boxShadow: CARD_SHADOW,
                  padding: '16px 20px', height: '100%',
                }}>
                  <SectionTitle>Dept Identity Graph</SectionTitle>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {detail?.source_records?.map((rec: any, idx: number) => {
                      const conf = rec.confidence ?? 0;
                      const hasCrit = intel?.anomalies?.some((a: any) => a.severity === 'CRITICAL' && a.title.toLowerCase().includes(rec.source_system.split('_')[0]));
                      return (
                        <div key={idx} style={{
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                          paddingBottom: 8, borderBottom: idx === detail.source_records.length - 1 ? 'none' : '1px solid #f0f0f0'
                        }}>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: 13, color: '#333' }}>{rec.source_system.replace(/_/g, ' ')}</div>
                            <div style={{ fontSize: 11, color: '#888', display: 'flex', alignItems: 'center', gap: 6 }}>
                              Conf: {conf.toFixed(2)}
                              <div style={{ width: 40, height: 4, background: '#eee', borderRadius: 2 }}>
                                <div style={{ height: '100%', width: `${conf * 100}%`, background: '#1D9E75', borderRadius: 2 }} />
                              </div>
                            </div>
                          </div>
                          <span style={{
                            fontSize: 10, padding: '2px 8px', borderRadius: 10,
                            background: hasCrit ? '#FCEBEB' : (conf >= 0.95 ? '#EAF3DE' : '#f5f5f5'),
                            color: hasCrit ? '#A32D2D' : (conf >= 0.95 ? '#3B6D11' : '#666')
                          }}>
                            {hasCrit ? '⚠ Conflict' : (conf >= 0.95 ? 'Anchor' : 'Match')}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </Col>

              
            </Row>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {detail.source_records?.map((rec: any, i: number) => {
                const shapValues = rec.shap_values ?? rec.evidence?.shap_values;
                if (!shapValues) return null;
                return (
                  <Card key={i} title={`SHAP Analysis: ${rec.source_system?.toUpperCase()} - ${rec.source_record_id}`} size="small">
                    <SHAPVisualizations shapValues={shapValues} />
                  </Card>
                );
              })}
            </div>

                  </div>
                )
              },
              {
                key: 'comparison',
                label: 'Comparison',
                children: (
                  <div style={{ paddingTop: 8, paddingBottom: 40 }}>
                    
            <Row gutter={16} style={{ marginBottom: 18 }}>

              <Col xs={24} lg={24}>
                <div style={{
                  background: '#fff', borderRadius: 10, boxShadow: CARD_SHADOW,
                  padding: '16px 20px', height: '100%',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                    <SectionTitle style={{ marginBottom: 0 }}>Sector Peer Benchmark</SectionTitle>
                    {intel?.peer_benchmark?.nic_code && (
                      <span style={{ fontSize: 10, color: '#888' }}>
                        NIC {intel.peer_benchmark.nic_code} · {intel.peer_benchmark.pincode}
                      </span>
                    )}
                  </div>
                  
                  {intel?.peer_benchmark ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      <div style={{ display: 'flex', fontSize: 11, color: '#888', gap: 12, marginBottom: 4 }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <div style={{ width: 10, height: 3, background: '#D85A30', borderRadius: 2 }} /> This entity
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <div style={{ width: 10, height: 10, background: '#B5D4F4', borderRadius: 2 }} /> Sector average
                        </span>
                      </div>

                      {/* Score */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 100, fontSize: 11, color: '#666' }}>Activity Score</div>
                        <div style={{ flex: 1, height: 10, background: '#f5f5f5', borderRadius: 5, position: 'relative' }}>
                          <div style={{ height: '100%', width: `${Math.max(0, intel.peer_benchmark.peer_avg_score * 50 + 50)}%`, background: '#B5D4F4', borderRadius: 5 }} />
                          <div style={{ position: 'absolute', top: -3, width: 3, height: 16, background: '#D85A30', borderRadius: 2, left: `${Math.max(0, intel.peer_benchmark.this_score * 50 + 50)}%` }} />
                        </div>
                        <div style={{ width: 36, textAlign: 'right', fontSize: 12, fontWeight: 600 }}>{intel.peer_benchmark.this_score.toFixed(2)}</div>
                      </div>

                      {/* Insp Age */}
                      {intel.peer_benchmark.inspection_age_days !== null && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ width: 100, fontSize: 11, color: '#666' }}>Insp. Age (days)</div>
                          <div style={{ flex: 1, height: 10, background: '#f5f5f5', borderRadius: 5, position: 'relative' }}>
                            <div style={{ height: '100%', width: `50%`, background: '#F7C1C1', borderRadius: 5 }} />
                            <div style={{ position: 'absolute', top: -3, width: 3, height: 16, background: '#D85A30', borderRadius: 2, left: `${Math.min(100, intel.peer_benchmark.inspection_age_days / 730 * 100)}%` }} />
                          </div>
                          <div style={{ width: 36, textAlign: 'right', fontSize: 12, fontWeight: 600, color: intel.peer_benchmark.inspection_age_days > 365 ? '#E24B4A' : '#333' }}>
                            {intel.peer_benchmark.inspection_age_days}d
                          </div>
                        </div>
                      )}

                      {/* Dept Coverage */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 100, fontSize: 11, color: '#666' }}>Dept Coverage</div>
                        <div style={{ flex: 1, height: 10, background: '#f5f5f5', borderRadius: 5, position: 'relative' }}>
                          <div style={{ height: '100%', width: `${(intel.peer_benchmark.dept_coverage / intel.peer_benchmark.max_dept_coverage) * 100}%`, background: '#B5D4F4', borderRadius: 5 }} />
                          <div style={{ position: 'absolute', top: -3, width: 3, height: 16, background: '#D85A30', borderRadius: 2, left: `${(intel.peer_benchmark.dept_coverage / intel.peer_benchmark.max_dept_coverage) * 100}%` }} />
                        </div>
                        <div style={{ width: 36, textAlign: 'right', fontSize: 12, fontWeight: 600 }}>{intel.peer_benchmark.dept_coverage}/{intel.peer_benchmark.max_dept_coverage}</div>
                      </div>

                      <div style={{ fontSize: 10, color: '#aaa', marginTop: 6 }}>
                        Compared against {intel.peer_benchmark.peer_count} businesses in region.
                      </div>
                    </div>
                  ) : (
                    <Text type="secondary" style={{ fontSize: 12 }}>Not enough peer data available.</Text>
                  )}
                </div>
              </Col>
            </Row>

            {(() => {
              const normalizedRecords = detail.source_records?.map((rec: any) => ({
                ...rec,
                record_details: rec.record_details ?? {
                  business_name: rec.business_name,
                  address: rec.address,
                  PAN: rec.pan,
                  GSTIN: rec.gstin,
                  phone: rec.phone,
                  pin_code: rec.pin_code,
                  owner_name: rec.owner_name,
                  registration_date: rec.registration_date,
                }
              })) || [];
              if (normalizedRecords.length === 0) return <Text type="secondary">No records available.</Text>;
              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                  <CrossDatabaseComparison sourceRecords={normalizedRecords} />
                  {normalizedRecords.length > 1 && (
                    <Card title="Feature Vector Agreement" size="small" style={{ borderRadius: 8, boxShadow: CARD_SHADOW }}>
                      <FeatureMatrix sourceRecords={normalizedRecords} />
                    </Card>
                  )}
                </div>
              );
            })()}

                  </div>
                )
              },
              {
                key: 'timeline',
                label: 'Timeline',
                children: (
                  <div style={{ paddingTop: 8, paddingBottom: 40 }}>
                    
            <Row gutter={16} style={{ marginBottom: 18 }}>

              <Col xs={24} lg={24}>
                <div style={{
                  background: '#fff', borderRadius: 10, boxShadow: CARD_SHADOW,
                  padding: '16px 20px', height: '100%',
                }}>
                  <SectionTitle>Activity Pulse — Score Timeline</SectionTitle>
                  <div style={{ height: 180, marginTop: 10 }}>
                    {intel?.score_history?.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={[...intel.score_history].reverse()} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                          <defs>
                            <linearGradient id="scoreGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%"  stopColor={ORANGE} stopOpacity={0.25} />
                              <stop offset="95%" stopColor={ORANGE} stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                          <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#888' }} axisLine={false} tickLine={false} />
                          <YAxis tick={{ fontSize: 10, fill: '#888' }} domain={[-1, 1]} axisLine={false} tickLine={false} />
                          <ReTooltip formatter={(v: number) => [v.toFixed(2), 'Score']} />
                          <ReferenceLine y={0} stroke="#ddd" strokeDasharray="3 3" />
                          <Area type="monotone" dataKey="score" stroke={ORANGE} fill="url(#scoreGrad)" strokeWidth={2} dot={{ r: 3, fill: ORANGE }} />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
                        <Text type="secondary">No history available</Text>
                      </div>
                    )}
                  </div>
                </div>
              </Col>

              
</Row>
            <Row gutter={16} style={{ marginBottom: 18 }}>

              <Col xs={24} lg={12}>
                <div style={{
                  background: '#fff', borderRadius: 10, boxShadow: CARD_SHADOW,
                  padding: '16px 20px', height: '100%',
                }}>
                  <SectionTitle>Active Signal Weights</SectionTitle>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {intel?.active_signals?.slice(0, 4).map((sig: any, idx: number) => {
                      const pos = sig.effective_weight > 0;
                      return (
                        <div key={idx} style={{
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                          paddingBottom: 8, borderBottom: idx === Math.min(3, intel.active_signals.length - 1) ? 'none' : '1px solid #f0f0f0'
                        }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <div style={{ width: 8, height: 8, borderRadius: '50%', background: pos ? '#1D9E75' : (sig.effective_weight < 0 ? '#E24B4A' : '#888') }} />
                            <div>
                              <div style={{ fontWeight: 500, fontSize: 13, color: '#333' }}>{sig.event_type.replace(/_/g, ' ')}</div>
                              <div style={{ fontSize: 10, color: '#888' }}>
                                {sig.days_since}d · {sig.half_life_days ? `${sig.half_life_days}d HL` : 'No decay'}
                              </div>
                            </div>
                          </div>
                          <div style={{ fontWeight: 600, fontSize: 13, color: pos ? '#1D9E75' : (sig.effective_weight < 0 ? '#E24B4A' : '#888') }}>
                            {sig.effective_weight > 0 ? '+' : ''}{sig.effective_weight.toFixed(2)}
                          </div>
                        </div>
                      );
                    })}
                    {(!intel?.active_signals || intel.active_signals.length === 0) && (
                      <Text type="secondary" style={{ fontSize: 12 }}>No active signals.</Text>
                    )}
                  </div>
                </div>
              </Col>

              

              <Col xs={24} lg={12}>
                <div style={{
                  background: '#fff', borderRadius: 10, boxShadow: CARD_SHADOW,
                  padding: '16px 20px', height: '100%',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'
                }}>
                  <SectionTitle style={{ alignSelf: 'flex-start' }}>Dormancy Risk</SectionTitle>
                  <div style={{ position: 'relative', width: 140, height: 100 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={[
                            { value: intel?.kpi?.dormancy_eta_days ? Math.min(1, intel.kpi.dormancy_eta_days / 365) : 1 },
                            { value: intel?.kpi?.dormancy_eta_days ? Math.max(0, 1 - intel.kpi.dormancy_eta_days / 365) : 0 }
                          ]}
                          cx="50%" cy="100%"
                          startAngle={180} endAngle={0}
                          innerRadius={60} outerRadius={70}
                          paddingAngle={0}
                          dataKey="value"
                          stroke="none"
                        >
                          <Cell fill="#BA7517" />
                          <Cell fill="#f0f0f0" />
                        </Pie>
                      </PieChart>
                    </ResponsiveContainer>
                    <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, textAlign: 'center' }}>
                      <div style={{ fontSize: 28, fontWeight: 600, color: '#333', lineHeight: 1 }}>
                        {intel?.kpi?.dormancy_eta_days ?? '∞'}
                      </div>
                      <div style={{ fontSize: 10, color: '#888' }}>days to DORMANT</div>
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: '#666', textAlign: 'center', marginTop: 12, background: '#fafafa', padding: 8, borderRadius: 6 }}>
                    {intel?.kpi?.dormancy_eta_days 
                      ? "Score will drop below threshold at current decay rate." 
                      : "Entity is currently stable or permanently closed."}
                  </div>
                </div>
              </Col>
            </Row>

            {/* ══ RECENT ACTIVITY EVENTS ══ */}
            {timeline?.events?.length > 0 && (
              <>
                <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 12 }}>Recent Activity Events</div>
                <div style={{
                  background: '#fff', borderRadius: 10, boxShadow: CARD_SHADOW,
                  padding: '18px 20px', marginBottom: 28,
                }}>
                  {/* Vertical connected timeline */}
                  <div style={{ position: 'relative' }}>
                    {/* Connecting line */}
                    <div style={{
                      position: 'absolute', left: 14, top: 14,
                      bottom: 14, width: 1,
                      background: 'linear-gradient(to bottom, #e0e0e0, #f5f5f5)',
                    }} />

                    {timeline.events.slice(0, 10).map((e: any, idx: number) => {
                      const positive = e.signal_weight > 0;
                      const neutral  = e.signal_weight === 0 || e.signal_weight == null;
                      const dotColor = neutral ? '#d9d9d9' : positive ? '#52c41a' : '#f5222d';

                      return (
                        <div key={idx} style={{ display: 'flex', gap: 14, marginBottom: 16, position: 'relative' }}>
                          {/* Dot */}
                          <div style={{
                            width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                            background: neutral ? '#f5f5f5' : positive ? '#f6ffed' : '#fff1f0',
                            border: `2px solid ${dotColor}`,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            zIndex: 1,
                          }}>
                            {eventIcon(e.event_type)}
                          </div>

                          {/* Content */}
                          <div style={{ flex: 1, paddingTop: 3 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                              <Text style={{ fontSize: 13, fontWeight: 600, color: '#222' }}>
                                {e.event_type?.replace(/_/g, ' ')}
                              </Text>
                              {e.signal_weight != null && (
                                <span style={{
                                  fontSize: 11, fontWeight: 700, padding: '1px 10px',
                                  borderRadius: 20,
                                  background: positive ? '#f6ffed' : neutral ? '#fafafa' : '#fff1f0',
                                  color:      positive ? '#389e0d' : neutral ? '#999'    : '#cf1322',
                                  border: `1px solid ${positive ? '#b7eb8f' : neutral ? '#e0e0e0' : '#ffa39e'}`,
                                }}>
                                  {positive ? '+' : ''}{e.signal_weight.toFixed(2)}
                                </span>
                              )}
                            </div>
                            <Text style={{ fontSize: 11, color: '#aaa', marginTop: 2, display: 'block' }}>
                              {e.source_system} · {e.event_timestamp?.slice(0, 10)}
                            </Text>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            )}



                  </div>
                )
              }
            ]}
          />
          </>
        )}
      </div>
    </div>
  );
};

export default UbidDetailView;
