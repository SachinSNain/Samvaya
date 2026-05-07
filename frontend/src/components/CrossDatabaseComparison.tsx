import React, { useMemo } from 'react';
import { Card, Row, Col, Typography, Tag, Divider } from 'antd';
import { SourceRecordDetail } from '../api/types';

const { Text } = Typography;

const COMPARISON_FIELDS = [
  { key: 'business_name', label: 'Business Name' },
  { key: 'address', label: 'Address' },
  { key: 'PAN', label: 'PAN' },
  { key: 'GSTIN', label: 'GSTIN' },
  { key: 'phone', label: 'Phone' },
  { key: 'pin_code', label: 'Pin Code' },
  { key: 'owner_name', label: 'Owner Name' },
  { key: 'registration_date', label: 'Registration Date' },
];

const DEPT_COLORS: Record<string, string> = {
  shop_establishment: '#1677ff',
  factories: '#FF6B2C',
  labour: '#722ed1',
  kspcb: '#52c41a',
};

interface CrossDatabaseComparisonProps {
  sourceRecords: SourceRecordDetail[];
}

const CrossDatabaseComparison: React.FC<CrossDatabaseComparisonProps> = ({ sourceRecords }) => {
  const comparisonData = useMemo(() => {
    if (!sourceRecords || sourceRecords.length === 0) return [];

    return COMPARISON_FIELDS.map(field => {
      const values = sourceRecords.map(r => ({
        system: r.source_system,
        id: r.source_record_id,
        value: r.record_details?.[field.key] || '—'
      }));

      // Check if there's any mismatch among non-empty values
      const nonEmptyValues = values.filter(v => v.value !== '—').map(v => String(v.value).toLowerCase().trim());
      const allMatch = nonEmptyValues.length <= 1 || nonEmptyValues.every(v => v === nonEmptyValues[0]);

      return {
        ...field,
        values,
        hasMismatch: !allMatch && nonEmptyValues.length > 1
      };
    });
  }, [sourceRecords]);

  if (!sourceRecords || sourceRecords.length === 0) {
    return <Text type="secondary">No records available for comparison.</Text>;
  }

  return (
    <Card title="Cross-Database Comparison" size="small" style={{ borderRadius: 8 }}>
      <Row gutter={[16, 16]} style={{ marginBottom: 12, fontWeight: 'bold' }}>
        <Col span={4}><Text type="secondary">Field</Text></Col>
        {sourceRecords.map((rec, i) => (
          <Col span={Math.floor(20 / sourceRecords.length)} key={i}>
            <Tag 
              color={DEPT_COLORS[rec.source_system] || 'default'}
              style={{ fontSize: 11, textTransform: 'uppercase' }}
            >
              {rec.source_system.replace('_', ' ')}
            </Tag>
          </Col>
        ))}
      </Row>
      <Divider style={{ margin: '8px 0' }} />
      
      {comparisonData.map((row, index) => (
        <React.Fragment key={row.key}>
          <Row 
            gutter={[16, 16]} 
            style={{ 
              padding: '8px 0',
              background: row.hasMismatch ? '#fff1f0' : 'transparent',
              borderRadius: 4
            }}
          >
            <Col span={4}>
              <Text strong style={{ fontSize: 13 }}>{row.label}</Text>
            </Col>
            {row.values.map((v, i) => (
              <Col span={Math.floor(20 / sourceRecords.length)} key={i}>
                <Text 
                  type={v.value === '—' ? 'secondary' : undefined} 
                  style={{ fontSize: 13, wordBreak: 'break-word' }}
                >
                  {v.value}
                </Text>
              </Col>
            ))}
          </Row>
          {index < comparisonData.length - 1 && <Divider style={{ margin: '4px 0' }} />}
        </React.Fragment>
      ))}
    </Card>
  );
};

export default React.memo(CrossDatabaseComparison);
