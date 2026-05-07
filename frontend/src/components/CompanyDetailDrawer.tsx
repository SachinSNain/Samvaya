import React, { useState, useEffect } from 'react';
import { Drawer, Typography, Space, Tag, Alert, Spin, Descriptions, Divider, Progress, Tabs, Modal, Button, notification, Card } from 'antd';
import { RobotOutlined, WarningOutlined } from '@ant-design/icons';
import { Database, ShieldCheck, ShieldAlert, ShieldOff, HelpCircle } from 'lucide-react';
import { ubidApi } from '../api';
import { CompanyFullDetail } from '../api/types';
import SHAPVisualizations from './SHAPVisualizations';
import FeatureMatrix from './FeatureMatrix';
import CrossDatabaseComparison from './CrossDatabaseComparison';
import ExportButton from './ExportButton';
// ActivityView is a full dashboard page — timeline is rendered inline via renderTimeline() below
import { handleApiError } from '../utils/errorHandling';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip as ReTooltip,
  ResponsiveContainer, CartesianGrid
} from 'recharts';

const { Text } = Typography;
const ORANGE = '#FF6B2C';

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: '#52c41a', DORMANT: '#faad14',
  CLOSED_SUSPECTED: '#f5222d', CLOSED_CONFIRMED: '#820014', UNKNOWN: '#8c8c8c',
};

const STATUS_ICON: Record<string, React.ReactNode> = {
  ACTIVE:           <ShieldCheck size={13} color="#52c41a" />,
  DORMANT:          <ShieldAlert size={13} color="#faad14" />,
  CLOSED_SUSPECTED: <ShieldOff size={13} color="#f5222d" />,
  CLOSED_CONFIRMED: <ShieldOff size={13} color="#820014" />,
  UNKNOWN:          <HelpCircle size={13} color="#8c8c8c" />,
};

const DEPT_COLORS: Record<string, string> = {
  shop_establishment: '#1677ff',
  factories:          ORANGE,
  labour:             '#722ed1',
  kspcb:              '#52c41a',
};

interface CompanyDetailDrawerProps {
  ubid: string;
  open: boolean;
  onClose: () => void;
  timelineData: any; // We receive timeline data from parent or fetch it here
  timelineLoading: boolean;
}

const CompanyDetailDrawer: React.FC<CompanyDetailDrawerProps> = ({ ubid, open, onClose, timelineData, timelineLoading }) => {
  const [detail, setDetail] = useState<CompanyFullDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  
  // Revert state
  const [revertDialogOpen, setRevertDialogOpen] = useState(false);
  const [revertLoading, setRevertLoading] = useState(false);
  const [selectedLinkId, setSelectedLinkId] = useState<string | null>(null);

  const fetchDetail = async () => {
    if (!ubid) return;
    setLoading(true);
    try {
      // In a real scenario we use getFullDetail, assuming backend supports it
      const res = await ubidApi.getFullDetail(ubid);
      setDetail(res.data);
    } catch (error) {
      handleApiError(error, 'Failed to load UBID details');
      setDetail(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open && ubid) {
      fetchDetail();
      setActiveTab('overview');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, ubid]);

  const handleRevertClick = (linkId: string) => {
    setSelectedLinkId(linkId);
    setRevertDialogOpen(true);
  };

  const confirmRevert = async () => {
    if (!selectedLinkId) return;
    setRevertLoading(true);
    try {
      const response = await ubidApi.revertLink({ link_id: selectedLinkId });
      notification.success({
        message: 'Link Reverted',
        description: response.data.message || 'The link has been successfully reverted.',
      });
      setRevertDialogOpen(false);
      fetchDetail(); // Refresh data
    } catch (error) {
      handleApiError(error, 'Failed to revert link');
    } finally {
      setRevertLoading(false);
    }
  };

  /* Build a mini timeline chart from events */
  const buildTimelineChart = (events: any[]) => {
    if (!events?.length) return [];
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

  const renderOverview = () => {
    if (!detail) return null;
    return (
      <div>
        {/* Status banner */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 12,
          padding: '14px 18px', borderRadius: 8, marginBottom: 16,
          background: `${STATUS_COLOR[detail.activity_status] ?? '#8c8c8c'}14`,
          border: `1px solid ${STATUS_COLOR[detail.activity_status] ?? '#8c8c8c'}30`,
        }}>
          {STATUS_ICON[detail.activity_status]}
          <div>
            <Text strong style={{ fontSize: 15 }}>{detail.display_name || ubid}</Text>
            <div style={{ marginTop: 2 }}>
              <Tag style={{
                background: `${STATUS_COLOR[detail.activity_status] ?? '#8c8c8c'}20`,
                color: STATUS_COLOR[detail.activity_status] ?? '#8c8c8c',
                border: 'none', fontWeight: 700, fontSize: 11,
              }}>
                {detail.activity_status || 'UNKNOWN'}
              </Tag>
              {detail.activity_score != null && (
                <Text type="secondary" style={{ fontSize: 11, marginLeft: 6 }}>
                  Score: {detail.activity_score.toFixed(3)}
                </Text>
              )}
            </div>
          </div>
          <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
            <Text type="secondary" style={{ fontSize: 11, display: 'block' }}>Dept Records</Text>
            <Text strong style={{ fontSize: 20, color: ORANGE }}>{detail.source_record_count}</Text>
          </div>
        </div>

        {/* AI explanation */}
        {detail.ai_explanation && (
          <Alert
            message={<><RobotOutlined /> AI Analysis</>}
            description={detail.ai_explanation}
            type="info" showIcon
            style={{ marginBottom: 14, borderRadius: 8 }}
          />
        )}

        {/* Identity card */}
        {(() => {
          // Extract the most complete consolidated information from the linked source records
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
            <Card size="small" style={{ marginBottom: 14, borderRadius: 8 }} title="Company Identity & Details">
              <Descriptions size="small" column={2} labelStyle={{ color: '#999', fontSize: 12 }}>
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

        {/* Linked source records */}
        <Divider orientation="left" style={{ fontSize: 13 }}>
          Linked Department Records ({detail.source_record_count})
        </Divider>

        {detail.source_records?.map((rec: any, i: number) => {
          // Support both full-details flat fields and legacy evidence.record_details shape
          const businessName = rec.record_details?.business_name ?? rec.business_name;
          const address = rec.record_details?.address ?? rec.address;
          // Use link_id for revert (full-details) or fall back to source_record_id
          const linkId = rec.link_id ?? rec.source_record_id;
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
                  <Button 
                    type="text" 
                    danger 
                    size="small"
                    onClick={() => handleRevertClick(linkId)} 
                    aria-label={`Revert link for ${rec.source_record_id}`}
                  >
                    Revert
                  </Button>
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
    );
  };

  const renderSHAPAnalysis = () => {
    if (!detail?.source_records || detail.source_records.length === 0) return <Text type="secondary">No records available.</Text>;
    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {detail.source_records.map((rec: any, i: number) => {
          // full-details returns shap_values at top level; fallback to nested evidence.shap_values
          const shapValues = rec.shap_values ?? rec.evidence?.shap_values;
          return (
            <Card key={i} title={`SHAP Analysis: ${rec.source_system?.toUpperCase()} - ${rec.source_record_id}`} size="small">
              <SHAPVisualizations shapValues={shapValues} />
            </Card>
          );
        })}
      </Space>
    );
  };

  const renderComparison = () => {
    if (!detail?.source_records || detail.source_records.length === 0) return <Text type="secondary">No records available.</Text>;
    // Normalize source records: full-details has flat fields; wrap them in evidence/record_details shape
    const normalizedRecords = detail.source_records.map((rec: any) => ({
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
      },
      evidence: rec.evidence ?? {
        shap_values: rec.shap_values,
        feature_vector: rec.feature_vector,
      },
    }));
    return (
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <CrossDatabaseComparison sourceRecords={normalizedRecords} />
        <Card title="Feature Vector Agreement" size="small">
          <FeatureMatrix sourceRecords={normalizedRecords} />
        </Card>
      </Space>
    );
  };

  const renderTimeline = () => {
    if (timelineLoading) return <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>;
    if (!timelineData?.events?.length) return <Text type="secondary">No activity events found.</Text>;
    return (
      <div>
        <Card size="small" style={{ marginBottom: 14, borderRadius: 8 }} title="Activity Timeline — Events per Month">
          <div style={{ height: 180 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={buildTimelineChart(timelineData.events)} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="actGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={ORANGE} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={ORANGE} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <ReTooltip />
                <Area dataKey="count" stroke={ORANGE} fill="url(#actGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          {timelineData.activity_narrative && (
            <Text type="secondary" style={{ fontSize: 11, display: 'block', marginTop: 8 }}>
              {timelineData.activity_narrative}
            </Text>
          )}
        </Card>
      </div>
    );
  };

  return (
    <Drawer
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
          <Space>
            <Database size={16} color={ORANGE} />
            <Text style={{ fontFamily: 'monospace', fontSize: 13, color: ORANGE }}>{ubid}</Text>
          </Space>
          <ExportButton ubid={ubid} />
        </div>
      }
      placement="right"
      width={800}
      onClose={onClose}
      open={open}
      bodyStyle={{ padding: '0px', background: '#fafafa' }}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
      ) : detail ? (
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab} 
          style={{ padding: '0 24px' }}
          items={[
            { key: 'overview', label: 'Overview', children: renderOverview() },
            { key: 'shap', label: 'SHAP Analysis', children: renderSHAPAnalysis() },
            { key: 'comparison', label: 'Comparison', children: renderComparison() },
            { key: 'timeline', label: 'Timeline', children: renderTimeline() },
          ]}
        />
      ) : (
        <div style={{ padding: 24 }}>
          <Text type="secondary">Failed to load UBID details.</Text>
        </div>
      )}

      {/* Revert Confirmation Modal */}
      <Modal
        title={
          <Space>
            <WarningOutlined style={{ color: '#faad14' }} />
            <Text>Confirm Link Revert</Text>
          </Space>
        }
        open={revertDialogOpen}
        onOk={confirmRevert}
        onCancel={() => setRevertDialogOpen(false)}
        confirmLoading={revertLoading}
        okText="Revert Link"
        okButtonProps={{ danger: true }}
      >
        <p>Are you sure you want to revert the link for source record <b>{selectedLinkId}</b>?</p>
        <p>This action will unlink the record from this UBID. If this record has no other active links, a new UBID will be created for it. This action cannot be undone and will be audited.</p>
      </Modal>
    </Drawer>
  );
};

export default React.memo(CompanyDetailDrawer);
