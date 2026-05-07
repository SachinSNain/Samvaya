import React, { useState, useMemo } from 'react';
import { Radio, Empty, Space, Typography, Tooltip as AntTooltip } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
  CartesianGrid,
  ReferenceLine
} from 'recharts';

const { Text } = Typography;

const FEATURE_LABELS: Record<string, string> = {
  F01: 'Name Jaro-Winkler',
  F02: 'Name Token Ratio',
  F03: 'Name Abbreviation',
  F04: 'PAN Match',
  F05: 'GSTIN Match',
  F06: 'Pin Code Match',
  F07: 'Geo Distance',
  F08: 'Address Match',
  F09: 'Phone Match',
  F10: 'NIC Match',
  F11: 'Owner Name Match',
  F12: 'Source System Weight',
  F13: 'Registration Date Delta',
};

interface SHAPVisualizationsProps {
  shapValues: Record<string, number> | undefined;
}

const SHAPVisualizations: React.FC<SHAPVisualizationsProps> = ({ shapValues }) => {
  const [viewType, setViewType] = useState<'bar' | 'waterfall'>('bar');

  const { barData, waterfallData } = useMemo(() => {
    if (!shapValues || Object.keys(shapValues).length === 0) {
      return { barData: [], waterfallData: [] };
    }

    const rawEntries = Object.entries(shapValues).map(([key, value]) => ({
      key,
      name: FEATURE_LABELS[key] || key,
      value,
      abs: Math.abs(value),
    }));

    // Bar chart data (sorted by absolute value, descending)
    const bar = [...rawEntries].sort((a, b) => b.abs - a.abs);

    // Waterfall chart data
    // We sort by original order or key, but for waterfall, starting with base value is standard.
    // Here we'll just show cumulative sums.
    let cumulative = 0;
    const waterfall = rawEntries.map(entry => {
      const start = cumulative;
      const end = cumulative + entry.value;
      cumulative = end;
      return {
        ...entry,
        start,
        end,
        range: [start, end]
      };
    });

    return { barData: bar, waterfallData: waterfall };
  }, [shapValues]);

  if (!shapValues || Object.keys(shapValues).length === 0) {
    return <Empty description="No SHAP explanation data available for this record." />;
  }

  const renderBarChart = () => (
    <div style={{ height: 350, width: '100%' }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          layout="vertical"
          data={barData}
          margin={{ top: 20, right: 30, left: 100, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tickFormatter={(v) => v.toFixed(2)} />
          <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 11 }} />
          <RechartsTooltip formatter={(value: number) => value.toFixed(4)} />
          <ReferenceLine x={0} stroke="#000" />
          <Bar dataKey="value" barSize={15}>
            {barData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.value >= 0 ? '#52c41a' : '#f5222d'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  const renderWaterfallChart = () => (
    <div style={{ height: 350, width: '100%' }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          layout="vertical"
          data={waterfallData}
          margin={{ top: 20, right: 30, left: 100, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tickFormatter={(v) => v.toFixed(2)} />
          <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 11 }} />
          <RechartsTooltip 
            formatter={(value: [number, number], name: string, props: any) => {
               // `value` here will be the `range` array [start, end]
               const diff = value[1] - value[0];
               return [diff.toFixed(4), "Contribution"];
            }} 
          />
          <ReferenceLine x={0} stroke="#000" />
          <Bar dataKey="range" barSize={15}>
            {waterfallData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.value >= 0 ? '#52c41a' : '#f5222d'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  return (
    <div role="region" aria-label="SHAP Analysis Visualizations">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Space>
          <Text strong>Feature Contributions (SHAP)</Text>
          <AntTooltip title="SHAP values show how much each feature contributed to the final match confidence. Green bars increase confidence, red bars decrease it.">
            <InfoCircleOutlined style={{ color: '#1890ff' }} />
          </AntTooltip>
        </Space>
        <Radio.Group 
          value={viewType} 
          onChange={(e) => setViewType(e.target.value)}
          size="small"
        >
          <Radio.Button value="bar">Bar Chart</Radio.Button>
          <Radio.Button value="waterfall">Waterfall</Radio.Button>
        </Radio.Group>
      </div>

      {viewType === 'bar' ? renderBarChart() : renderWaterfallChart()}
    </div>
  );
};

export default React.memo(SHAPVisualizations);
