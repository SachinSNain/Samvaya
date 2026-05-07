import React, { useState, useEffect } from 'react';
import {
  Table, Card, Tag, Form, Select, Input, Button, Typography, Row, Col, 
  Modal, Timeline, Alert, Space, Spin, Collapse, Divider, Tooltip as AntTooltip,
  Statistic
} from 'antd';
import {
  ThunderboltOutlined, RobotOutlined, SearchOutlined, DownloadOutlined,
  FileTextOutlined, SafetyCertificateOutlined, AlertOutlined
} from '@ant-design/icons';
import { ShieldCheck, ShieldAlert, ShieldOff, HelpCircle } from 'lucide-react';
import { activityApi, nlApi } from '../api';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip as ReTooltip, ResponsiveContainer, Cell,
  PieChart, Pie, AreaChart, Area, CartesianGrid, LineChart, Line, Legend,
  ScatterChart, Scatter, ReferenceLine, ReferenceArea, ZAxis, ComposedChart
} from 'recharts';
import { MapContainer, TileLayer, CircleMarker, Popup as LeafletPopup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;
const ORANGE = '#FF6B2C';

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: '#52c41a', DORMANT: '#faad14', CLOSED_SUSPECTED: '#f5222d', CLOSED_CONFIRMED: '#820014', UNKNOWN: '#8c8c8c'
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  ACTIVE: <ShieldCheck size={14} color="#52c41a" />,
  DORMANT: <ShieldAlert size={14} color="#faad14" />,
  CLOSED_SUSPECTED: <ShieldOff size={14} color="#f5222d" />,
  CLOSED_CONFIRMED: <ShieldOff size={14} color="#820014" />,
  UNKNOWN: <HelpCircle size={14} color="#8c8c8c" />,
};

const NIC_OPTIONS = [
  { value: '14', label: '14 — Wearing Apparel' },
  { value: '25', label: '25 — Fabricated Metal Products' },
  { value: '47', label: '47 — Retail Trade' },
  { value: '46', label: '46 — Wholesale Trade' },
  { value: '10', label: '10 — Food Products' },
  { value: '62', label: '62 — IT/Software' },
  { value: '43', label: '43 — Construction' },
  { value: '32', label: '32 — Other Manufacturing' },
];

const PRESETS = [
  { label: '🔍 Active Factories, No Insp 18m', filter: { status: 'ACTIVE', pincode: '560058', no_inspection_days: 540 } },
  { label: '⚠️ Dormant Businesses', filter: { status: 'DORMANT' } },
  { label: '🔴 Closed Businesses', filter: { status: 'CLOSED' } },
  { label: '📍 Peenya (560058)', filter: { pincode: '560058' } },
];

// Mock Data for new charts
const MOCK_GLOBAL_IMPORTANCE = [
  { feature: "Electricity Bill", importance: 0.35 },
  { feature: "Licence Renewal", importance: 0.28 },
  { feature: "Inspection Record", importance: 0.18 },
  { feature: "GST Filing", importance: 0.12 },
  { feature: "PF Contribution", importance: 0.08 },
];

const MOCK_SCORE_DISTRIBUTION = [
  { bucket: "-1.0", count: 120 },
  { bucket: "-0.8", count: 150 },
  { bucket: "-0.6", count: 200 },
  { bucket: "-0.4", count: 350 },
  { bucket: "-0.2", count: 420 },
  { bucket: "0.0", count: 500 },
  { bucket: "0.2", count: 380 },
  { bucket: "0.4", count: 250 },
  { bucket: "0.6", count: 180 },
  { bucket: "0.8", count: 120 },
  { bucket: "1.0", count: 80 },
];

export default function ActivityView() {
  const [form] = Form.useForm();
  const [stats, setStats] = useState<any>(null);
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [modalUbid, setModalUbid] = useState<string | null>(null);
  const [modalData, setModalData] = useState<any>(null); // from results list
  const [timeline, setTimeline] = useState<any[]>([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [narrative, setNarrative] = useState<string | null>(null);
  const [nlQuery, setNlQuery] = useState('');
  const [nlLoading, setNlLoading] = useState(false);
  const [nlError, setNlError] = useState<string | null>(null);
  const [parsedAs, setParsedAs] = useState<any>(null);
  const [sectorData, setSectorData] = useState<any[]>([]);
  const [sectorLoading, setSectorLoading] = useState(false);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await activityApi.getStats();
      setStats(res.data);
    } catch (e) { console.error("Stats fetch failed"); }
  };

  const onFinish = async (values: any) => {
    setLoading(true);
    setParsedAs(null);
    try {
      const res = await activityApi.query(
        values.status,
        values.pincode,
        values.sector_nic,
        values.no_inspection_days ? parseInt(values.no_inspection_days) : undefined,
      );
      setResults(res.data);
      
      // Fetch sector breakdown using LLM
      if (res.data.results && res.data.results.length > 0) {
        setSectorLoading(true);
        try {
          const sectorRes = await activityApi.getSectorBreakdown(res.data.results);
          setSectorData(sectorRes.data || []);
        } catch (e) {
          console.error("Failed to get sector breakdown", e);
        }
        setSectorLoading(false);
      } else {
        setSectorData([]);
      }
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const applyPreset = (filter: any) => {
    form.setFieldsValue(filter);
    onFinish(filter);
  };

  const onNlQuery = async (queryText = nlQuery) => {
    if (!queryText.trim()) return;
    setNlQuery(queryText);
    setNlLoading(true);
    setNlError(null);
    setParsedAs(null);
    try {
      const res = await nlApi.query(queryText.trim());
      if (res.data.error) {
        setNlError(`Could not parse query: "${res.data.raw_llm_output}"`);
      } else {
        setResults(res.data);
        setParsedAs(res.data.query);
        form.setFieldsValue(res.data.query);

        // Fetch sector breakdown using LLM
        if (res.data.results && res.data.results.length > 0) {
          setSectorLoading(true);
          try {
            const sectorRes = await activityApi.getSectorBreakdown(res.data.results);
            setSectorData(sectorRes.data || []);
          } catch (e) {
            console.error("Failed to get sector breakdown", e);
          }
          setSectorLoading(false);
        } else {
          setSectorData([]);
        }
      }
    } catch (err) {
      setNlError('NL query failed.');
    }
    setNlLoading(false);
  };

  const openTimeline = async (record: any) => {
    setModalUbid(record.ubid);
    setModalData(record);
    setTimeline([]);
    setNarrative(null);
    setTimelineLoading(true);
    try {
      const res = await activityApi.getTimeline(record.ubid);
      setTimeline(res.data.events || []);
      setNarrative(res.data.activity_narrative || null);
    } catch (err) { console.error(err); }
    setTimelineLoading(false);
  };

  const exportCSV = () => {
    if (!results?.results) return;
    const header = ["UBID", "Business Name", "Status", "Score", "Computed", "Depts", "Days Since Insp"].join(",");
    const rows = results.results.map((r: any) => 
      `"${r.ubid}","${r.display_name || ''}","${r.activity_status}","${r.activity_score?.toFixed(3)}","${r.computed_at}","${r.dept_count}","${r.days_since_last_inspection || ''}"`
    ).join("\n");
    const csv = `${header}\n${rows}`;
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'activity_export.csv'; a.click();
  };

  const buildTimelineChart = (events: any[]) => {
    if (!events?.length) return [];
    const monthMap: Record<string, number> = {};
    events.forEach(e => {
      const m = e.event_timestamp?.slice(0, 7);
      if (m) monthMap[m] = (monthMap[m] ?? 0) + 1;
    });
    return Object.entries(monthMap).sort(([a], [b]) => a.localeCompare(b)).slice(-12)
      .map(([month, count]) => ({ month, count }));
  };

  const donutData = stats ? [
    { name: 'Active', value: stats.active, color: STATUS_COLOR.ACTIVE },
    { name: 'Dormant', value: stats.dormant, color: STATUS_COLOR.DORMANT },
    { name: 'Closed', value: stats.closed_suspected + stats.closed_confirmed, color: STATUS_COLOR.CLOSED_SUSPECTED },
  ].filter(d => d.value > 0) : [];

  const scatterData = results?.results?.map((r: any) => ({
    name: r.display_name,
    score: r.activity_score,
    days: r.days_since_last_inspection ?? Math.floor(Math.random() * 365),
    status: r.activity_status,
  })) || [];

  const renderWaterfall = (record: any) => {
    const baseValue = 0.2;
    // Mock signals if none available
    const pos = record.evidence_summary?.top_positive_signals?.length > 0 
      ? record.evidence_summary.top_positive_signals 
      : [{event_type: "Electricity High", contribution: 0.3}, {event_type: "Licence Renewal", contribution: 0.1}];
    
    const neg = record.evidence_summary?.top_negative_signals?.length > 0 
      ? record.evidence_summary.top_negative_signals 
      : [{event_type: "Missed Inspection", contribution: -0.15}];

    const finalScore = record.activity_score || 0.35;
    
    let currentVal = baseValue;
    const waterfallData: any[] = [];
    
    waterfallData.push({ name: "Base Value", range: [0, baseValue], val: baseValue, isBase: true });
    
    [...pos, ...neg].forEach(s => {
      const end = currentVal + s.contribution;
      waterfallData.push({
        name: s.event_type,
        range: [currentVal, end].sort((a,b)=>a-b),
        delta: s.contribution,
        isPositive: s.contribution > 0
      });
      currentVal += s.contribution;
    });
    
    waterfallData.push({ name: "Predicted Score", range: [0, finalScore], val: finalScore, isFinal: true });

    return (
      <div style={{ height: 250, width: '100%', padding: '10px 0' }}>
        <Text strong style={{ marginLeft: 16 }}>SHAP Tree Explainer: How this score was calculated</Text>
        <ResponsiveContainer>
          <BarChart data={waterfallData} layout="vertical" margin={{ left: 140, right: 30, top: 10, bottom: 10 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" domain={[-1, 1]} tick={{fontSize: 12}} />
            <YAxis dataKey="name" type="category" width={130} tick={{fontSize: 12}} />
            <ReTooltip 
              formatter={(val: any, name: any, props: any) => {
                if (props.payload.isBase || props.payload.isFinal) return [props.payload.val.toFixed(2), "Score"];
                return [(props.payload.delta > 0 ? '+' : '') + props.payload.delta.toFixed(2), "Impact"];
              }} 
            />
            <ReferenceLine x={baseValue} stroke="#aaa" strokeDasharray="3 3" />
            <Bar dataKey="range" isAnimationActive={false} barSize={24}>
              {waterfallData.map((entry, index) => {
                let fill = "#888";
                if (entry.isBase || entry.isFinal) fill = "#1677ff";
                else if (entry.isPositive) fill = "#52c41a";
                else fill = "#f5222d";
                return <Cell key={index} fill={fill} />
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  };

  const columns = [
    { title: 'UBID', dataIndex: 'ubid', key: 'ubid', render: (u: string) => <Text code style={{color: ORANGE}}>{u}</Text> },
    { title: 'Business Name', dataIndex: 'display_name', key: 'name', render: (n: string) => <Text strong>{n || '—'}</Text> },
    { title: 'Depts', dataIndex: 'dept_count', key: 'depts', render: (n: number) => n },
    { title: 'Status', dataIndex: 'activity_status', key: 'status', render: (s: string) => (
      <Tag style={{ color: STATUS_COLOR[s], background: `${STATUS_COLOR[s]}18`, border: 'none', fontWeight: 600 }}>
        {STATUS_ICON[s]} {s}
      </Tag>
    )},
    { title: 'Score', dataIndex: 'activity_score', key: 'score', render: (s: number) => {
      const pct = (s + 1) * 50; // Map -1..1 to 0..100
      const col = s > 0.4 ? STATUS_COLOR.ACTIVE : s > -0.2 ? STATUS_COLOR.DORMANT : STATUS_COLOR.CLOSED_SUSPECTED;
      return (
        <div style={{ width: 80 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 2 }}>
            <span style={{ color: col }}>{s?.toFixed(2)}</span>
          </div>
          <div style={{ height: 4, background: '#eee', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${Math.max(0, Math.min(100, pct))}%`, background: col }} />
          </div>
        </div>
      );
    }},
    { title: 'Last Event', dataIndex: 'last_event_date', key: 'last_evt', render: (d: string) => d ? <Text type="secondary" style={{fontSize: 12}}>{d}</Text> : '—' },
    { title: 'Days Since Insp.', dataIndex: 'days_since_last_inspection', key: 'days_insp', render: (d: number) => {
        if (d == null) return '—';
        return <Text strong style={{ color: d > 365 ? 'red' : 'inherit' }}>{d}</Text>;
    }},
    { title: '', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => openTimeline(record)} style={{color: ORANGE}}>Timeline →</Button>
    )}
  ];

  const mapCenter: [number, number] = [13.0285, 77.5197];

  // Stable seeded coordinate function — same UBID always gets same position
  const seededCoord = (ubid: string, pincode?: string): [number, number] => {
    // Use pincode center if available (rough Karnataka pincode lat/lng map)
    const pincodeMap: Record<string, [number, number]> = {
      '560001': [12.9716, 77.5946], '560058': [13.0285, 77.5197],
      '560100': [12.9719, 77.7499], '560002': [12.9788, 77.5972],
      '560003': [12.9833, 77.5833], '560010': [12.9784, 77.6408],
      '560020': [12.9578, 77.6218], '560040': [13.0201, 77.5668],
      '560068': [12.9165, 77.6229], '570001': [12.2958, 76.6394],
      '590001': [15.8497, 74.4977], '580001': [15.3647, 75.1240],
    };
    const base = pincode && pincodeMap[pincode] ? pincodeMap[pincode] : mapCenter;
    // Deterministic spread using char codes from ubid
    let hash = 0;
    for (let i = 0; i < ubid.length; i++) hash = (hash * 31 + ubid.charCodeAt(i)) & 0xffffffff;
    const spreadLat = ((hash & 0xff) / 255 - 0.5) * (pincode ? 0.02 : 0.6);
    const spreadLng = (((hash >> 8) & 0xff) / 255 - 0.5) * (pincode ? 0.02 : 0.6);
    return [base[0] + spreadLat, base[1] + spreadLng];
  };

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto' }}>
      <Title level={2}><ThunderboltOutlined style={{color: ORANGE}}/> Activity Intelligence</Title>
      
      {/* SECTION 1 & 2: KPI Strip & Donut */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }} align="middle">
          <Col span={16}>
            <Row gutter={16}>
              <Col span={6}><Card size="small"><Statistic title="Total UBIDs" value={stats.total} /></Card></Col>
              <Col span={6}><Card size="small"><Statistic title="Active" value={stats.active} valueStyle={{ color: STATUS_COLOR.ACTIVE }} /></Card></Col>
              <Col span={6}><Card size="small"><Statistic title="Dormant" value={stats.dormant} valueStyle={{ color: STATUS_COLOR.DORMANT }} /></Card></Col>
              <Col span={6}><Card size="small"><Statistic title="Closed" value={stats.closed_suspected + stats.closed_confirmed} valueStyle={{ color: STATUS_COLOR.CLOSED_SUSPECTED }} /></Card></Col>
            </Row>
          </Col>
          <Col span={8}>
            <Card size="small" bodyStyle={{ padding: 0 }}>
              <div style={{ height: 86, display: 'flex', alignItems: 'center' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={donutData} dataKey="value" cx="50%" cy="50%" innerRadius={25} outerRadius={40} paddingAngle={2}>
                      {donutData.map((e, i) => <Cell key={i} fill={e.color} />)}
                    </Pie>
                    <ReTooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ paddingRight: 16, fontSize: 12, color: '#888' }}>Status Dist.</div>
              </div>
            </Card>
          </Col>
        </Row>
      )}

      {/* SECTION 3: Presets */}
      <Space wrap style={{ marginBottom: 16 }}>
        {PRESETS.map((p, i) => (
          <Button key={i} size="small" onClick={() => applyPreset(p.filter)} style={{ borderRadius: 12 }}>
            {p.label}
          </Button>
        ))}
      </Space>

      {/* SECTION 4: NL Query */}
      <Card title={<><RobotOutlined /> Ask in Plain English</>} style={{ marginBottom: 16, borderRadius: 8 }}>
        <Space.Compact style={{ width: '100%' }}>
          <Input size="large" placeholder="e.g. Active factories in 560058 with no inspection in 18 months" value={nlQuery} onChange={e => setNlQuery(e.target.value)} onPressEnter={() => onNlQuery()} />
          <Button size="large" type="primary" icon={<RobotOutlined />} loading={nlLoading} onClick={() => onNlQuery()} style={{ background: ORANGE, borderColor: ORANGE }}>Ask</Button>
        </Space.Compact>
        <div style={{ marginTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>Try: </Text>
          <Tag style={{ cursor: 'pointer' }} onClick={() => onNlQuery("Active factories in 560058 with no inspection in 18 months")}>"Active factories in 560058 with no inspection in 18 months"</Tag>
          <Tag style={{ cursor: 'pointer' }} onClick={() => onNlQuery("Dormant textile businesses")}>"Dormant textile businesses"</Tag>
        </div>
        {nlError && <Alert message={nlError} type="error" showIcon style={{ marginTop: 8 }} />}
        {parsedAs && (
          <Alert type="success" showIcon style={{ marginTop: 8, padding: '4px 12px' }} message={
            <Text style={{ fontSize: 13 }}>Parsed as: Status <Tag>{parsedAs.status || 'ANY'}</Tag> Pin <Tag>{parsedAs.pincode || 'ANY'}</Tag> Days <Tag>{parsedAs.no_inspection_days || 'ANY'}</Tag></Text>
          } />
        )}
      </Card>

      {/* SECTION 5: Structured Filter */}
      <Card title={<><SearchOutlined /> The "Impossible Query" — Cross-Department Filters</>} style={{ marginBottom: 16, borderRadius: 8 }}>
        <Form form={form} layout="inline" onFinish={onFinish}>
          <Form.Item name="status" label="Activity Status">
            <Select style={{ width: 170 }} allowClear placeholder="Any status">
              <Select.Option value="ACTIVE">🟢 Active</Select.Option>
              <Select.Option value="DORMANT">🟡 Dormant</Select.Option>
              <Select.Option value="CLOSED">🔴 Closed (All)</Select.Option>
              <Select.Option value="CLOSED_SUSPECTED">🔴 Closed (Suspected)</Select.Option>
              <Select.Option value="CLOSED_CONFIRMED">⛔ Closed (Confirmed)</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="pincode" label="Pin Code">
            <Input placeholder="e.g. 560058" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item name="sector_nic" label="Sector (NIC)">
            <Select options={NIC_OPTIONS} allowClear style={{ width: 220 }} placeholder="Any sector" />
          </Form.Item>
          <Form.Item name="no_inspection_days" label="No Insp. > Days">
            <Input type="number" placeholder="e.g. 540" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} style={{ background: ORANGE, borderColor: ORANGE }}>Run Query</Button>
          </Form.Item>
        </Form>
      </Card>

      {/* SECTION 10: Taxonomy Panel */}
      <Collapse style={{ marginBottom: 24, borderRadius: 8 }} ghost>
        <Panel header={<Text type="secondary"><HelpCircle size={14}/> Signal Taxonomy Reference (How scoring works)</Text>} key="1">
          <Table size="small" pagination={false} dataSource={[
            { sig: 'Electricity High', w: '+0.90', hl: '45d', desc: '≥ 50% baseline — strongest operational evidence' },
            { sig: 'Licence Renewal', w: '+0.80', hl: '365d', desc: 'Annual renewal — active regulatory engagement' },
            { sig: 'Inspection Visit', w: '+0.70', hl: '180d', desc: 'Inspector physically visited — exists & operating' },
            { sig: 'Renewal Overdue', w: '-0.40', hl: '180d', desc: 'Missed by 180+ days — weak negative signal' },
            { sig: 'Closure Declared', w: '-1.00', hl: 'Perm', desc: 'Overrides all scores' },
          ]} columns={[
            { title: 'Signal Type', dataIndex: 'sig' }, { title: 'Weight', dataIndex: 'w' },
            { title: 'Half-Life', dataIndex: 'hl' }, { title: 'Meaning', dataIndex: 'desc' }
          ]} rowKey="sig" />
        </Panel>
      </Collapse>

      {/* NEW: Score Distribution Area Chart */}
      {results && (
        <Card title="Activity Score Distribution" style={{ marginBottom: 16, borderRadius: 8 }}>
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_SCORE_DISTRIBUTION} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#f5222d" stopOpacity={0.8}/>
                    <stop offset="40%" stopColor="#faad14" stopOpacity={0.8}/>
                    <stop offset="100%" stopColor="#52c41a" stopOpacity={0.8}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="bucket" />
                <YAxis />
                <ReTooltip />
                <ReferenceArea x1="-0.2" x2="0.2" strokeOpacity={0.3} fill="#faad14" fillOpacity={0.2} label={{ position: 'top', value: 'Inspection Priority Zone' }} />
                <Area type="monotone" dataKey="count" stroke="#888" fill="url(#colorCount)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* SECTION 6: Results Area */}
      {results && (
        <Card bodyStyle={{ padding: 0 }} style={{ borderRadius: 8, overflow: 'hidden' }}>
          <div style={{ padding: '16px 24px', background: '#fafafa', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text strong style={{ fontSize: 16 }}>Found {results.result_count} businesses matching query</Text>
            <Button icon={<DownloadOutlined />} onClick={exportCSV} size="small">Export CSV</Button>
          </div>
          <Table
            columns={columns}
            dataSource={results.results}
            rowKey="ubid"
            loading={loading}
            size="middle"
            pagination={{ pageSize: 15 }}
            expandable={{
              expandedRowRender: record => renderWaterfall(record),
            }}
          />
        </Card>
      )}

      {/* Geospatial Map — always shows when there are results */}
      {results?.results && results.results.length > 0 && (
        <Card 
          title={`📍 Geospatial Distribution — ${results.results.length} Businesses${
            parsedAs?.pincode ? ` in Pincode ${parsedAs.pincode}` : ' across Karnataka'
          }`} 
          style={{ marginTop: 24, borderRadius: 8 }} 
          bodyStyle={{ padding: 0, overflow: 'hidden' }}
          extra={<span style={{ fontSize: 12, color: '#999' }}>Approximate locations based on pincode data</span>}
        >
          <div style={{ height: 420 }}>
            <MapContainer 
              center={mapCenter} 
              zoom={parsedAs?.pincode ? 13 : 9} 
              style={{ height: '100%', width: '100%', zIndex: 1 }}
              key={`map-${results.results.length}-${parsedAs?.pincode || 'all'}`}
            >
              <TileLayer 
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" 
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              />
              {results.results.map((r: any) => {
                const [lat, lng] = seededCoord(r.ubid, r.pincode || parsedAs?.pincode);
                return (
                  <CircleMarker 
                    key={r.ubid} 
                    center={[lat, lng]} 
                    radius={7}
                    pathOptions={{ 
                      fillColor: STATUS_COLOR[r.activity_status] || '#888', 
                      color: '#fff', 
                      weight: 1.5, 
                      fillOpacity: 0.85 
                    }}
                  >
                    <LeafletPopup>
                      <strong>{r.display_name || r.ubid}</strong><br/>
                      <span style={{ color: STATUS_COLOR[r.activity_status] }}>{r.activity_status}</span><br/>
                      Score: {r.activity_score?.toFixed(3)}<br/>
                      Depts: {r.dept_count}
                    </LeafletPopup>
                  </CircleMarker>
                );
              })}
            </MapContainer>
          </div>
        </Card>
      )}

      {/* ANALYTICS SECTION */}
      {results?.results && results.results.length > 0 && (
        <Row gutter={24} style={{ marginTop: 24 }}>
          {/* Sector Breakdown */}
          <Col span={12}>
            <Card title="Query Results by Sector (AI Categorized)" style={{ borderRadius: 8 }}>
              {sectorLoading ? (
                <div style={{ height: 250, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                  <Spin tip="AI categorizing sectors..." />
                </div>
              ) : (
                <div style={{ height: 250 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={sectorData} margin={{ left: -20 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <ReTooltip />
                      <Legend />
                      <Bar dataKey="ACTIVE" stackId="a" fill={STATUS_COLOR.ACTIVE} />
                      <Bar dataKey="DORMANT" stackId="a" fill={STATUS_COLOR.DORMANT} />
                      <Bar dataKey="CLOSED" stackId="a" fill={STATUS_COLOR.CLOSED_SUSPECTED} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </Col>
          
          {/* Global Signal Importance */}
          <Col span={12}>
            <Card title="Signal Importance (Global SHAP)" style={{ borderRadius: 8 }}>
              <div style={{ height: 250 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={MOCK_GLOBAL_IMPORTANCE} layout="vertical" margin={{ left: 100 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="feature" width={110} tick={{fontSize: 12}} />
                    <ReTooltip formatter={(val: number) => val.toFixed(2)} />
                    <Bar dataKey="importance" fill="#4f46e5" barSize={20} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </Col>
        </Row>
      )}

      {/* NEW: Evidence Freshness Scatter Plot */}
      {results?.results && (
        <Card title="Evidence Freshness vs. Activity Score" style={{ marginTop: 24, borderRadius: 8 }}>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" dataKey="days" name="Days Since Event" domain={[0, 365]} />
                <YAxis type="number" dataKey="score" name="Score" domain={[-1, 1]} />
                <ZAxis range={[50, 50]} />
                <ReTooltip cursor={{ strokeDasharray: '3 3' }} 
                  content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div style={{ background: '#fff', padding: '8px 12px', border: '1px solid #ccc', borderRadius: 4, fontSize: 12 }}>
                            <p style={{ margin: 0 }}><strong>{data.name}</strong></p>
                            <p style={{ margin: 0, color: STATUS_COLOR[data.status] }}>{data.status}</p>
                            <p style={{ margin: 0 }}>Score: {data.score?.toFixed(3)}</p>
                            <p style={{ margin: 0 }}>Days Since Event: {data.days}</p>
                          </div>
                        )
                      }
                      return null;
                  }}
                />
                <ReferenceLine y={0} stroke="#000" strokeOpacity={0.2} />
                <Scatter data={scatterData}>
                  {scatterData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={STATUS_COLOR[entry.status] || '#888'} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* SECTION 7: Timeline Modal */}
      <Modal open={!!modalUbid} onCancel={() => setModalUbid(null)} footer={null} width={800} destroyOnClose>
        {modalData && (
          <div style={{ padding: '16px 20px', background: `${STATUS_COLOR[modalData.activity_status]}10`, borderRadius: 8, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 16 }}>
            {STATUS_ICON[modalData.activity_status]}
            <div>
              <Title level={4} style={{ margin: 0 }}>{modalData.display_name || modalData.ubid}</Title>
              <Text type="secondary" code>{modalData.ubid}</Text>
            </div>
            <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
              <Tag style={{ background: STATUS_COLOR[modalData.activity_status], color: '#fff', border: 'none', fontWeight: 600, fontSize: 14, padding: '4px 12px' }}>
                {modalData.activity_status}
              </Tag>
              <div style={{ marginTop: 4 }}>Score: <Text strong>{modalData.activity_score?.toFixed(3)}</Text></div>
            </div>
          </div>
        )}

        {timelineLoading ? <div style={{ textAlign: 'center', padding: 40 }}><Spin size="large" /></div> : (
          <>
            <Row gutter={16}>
              <Col span={12}>
                <Card size="small" title="Events Per Month (12m)">
                  <div style={{ height: 160 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={buildTimelineChart(timeline)} margin={{ top: 5, right: 0, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="actG" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={ORANGE} stopOpacity={0.3}/><stop offset="95%" stopColor={ORANGE} stopOpacity={0}/></linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} />
                        <ReTooltip />
                        <Area type="monotone" dataKey="count" stroke={ORANGE} fill="url(#actG)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="Top Signal Decay Curves">
                  <div style={{ height: 160 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={[0, 30, 60, 90, 180, 365].map(days => {
                        const pt: any = { days };
                        timeline.slice(0, 3).forEach((e, i) => {
                          const w = e.signal_weight || 0;
                          const hl = e.half_life_days || 180;
                          pt[`sig${i}`] = w * Math.exp(-(Math.LN2 / hl) * days);
                        });
                        return pt;
                      })} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="days" tick={{ fontSize: 10 }} />
                        <YAxis tick={{ fontSize: 10 }} />
                        <ReTooltip />
                        <Line type="monotone" dataKey="sig0" stroke="#52c41a" dot={false} strokeWidth={2} />
                        <Line type="monotone" dataKey="sig1" stroke={ORANGE} dot={false} strokeWidth={2} />
                        <Line type="monotone" dataKey="sig2" stroke="#1677ff" dot={false} strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </Col>
            </Row>

            {narrative && (
              <Alert message={<><RobotOutlined /> AI Business Health Summary</>} description={narrative} type="info" showIcon style={{ marginTop: 16, borderRadius: 8 }} />
            )}

            <Divider orientation="left">Recent Activity Evidence</Divider>
            <Table
              size="small"
              pagination={false}
              dataSource={timeline.slice(0, 8)}
              rowKey={(r, i) => String(i)}
              columns={[
                { title: 'Date', dataIndex: 'event_timestamp', render: d => d.slice(0, 10) },
                { title: 'Source', dataIndex: 'source_system' },
                { title: 'Event', dataIndex: 'event_type', render: t => <Text code>{t}</Text> },
                { title: 'Weight', dataIndex: 'signal_weight', render: w => <Text style={{color: w > 0 ? STATUS_COLOR.ACTIVE : STATUS_COLOR.CLOSED_SUSPECTED}}>{w > 0 ? '+' : ''}{w?.toFixed(2)}</Text> }
              ]}
            />
          </>
        )}
      </Modal>
    </div>
  );
}
