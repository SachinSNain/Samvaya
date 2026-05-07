import React, { useMemo } from 'react';
import { Table, Typography, Tag, Space, Tooltip } from 'antd';
import { SourceRecordDetail } from '../api/types';

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

const AGREEMENT_COLORS = {
  match: '#f6ffed',    // light green
  partial: '#fffbe6',  // light yellow
  mismatch: '#fff1f0', // light red
  missing: '#f5f5f5',  // light grey
};

interface FeatureMatrixProps {
  sourceRecords: SourceRecordDetail[];
}

const FeatureMatrix: React.FC<FeatureMatrixProps> = ({ sourceRecords }) => {
  const tableData = useMemo(() => {
    if (!sourceRecords || sourceRecords.length === 0) return [];

    const features = Object.keys(FEATURE_LABELS);
    
    return features.map(featureKey => {
      const row: any = {
        key: featureKey,
        featureName: FEATURE_LABELS[featureKey],
      };

      // Calculate values and agreement for this feature across all records
      let matchCount = 0;
      let totalCount = 0;
      let sumShap = 0;

      sourceRecords.forEach((record: any, index) => {
        const featureValue = record.feature_vector?.[featureKey] ?? record.evidence?.feature_vector?.[featureKey];
        const shapValue = record.shap_values?.[featureKey] ?? record.evidence?.shap_values?.[featureKey];
        
        row[`record_${index}`] = {
          value: featureValue,
          shap: shapValue,
        };

        if (featureValue !== undefined && featureValue !== null) {
          totalCount++;
          // Assuming higher feature value (closer to 1) means better match
          // You might need to adjust logic depending on feature definitions
          if (featureValue > 0.8) matchCount++;
        }
        
        if (shapValue) sumShap += shapValue;
      });

      // Simple agreement logic based on how many have high feature values
      if (totalCount === 0) {
        row.agreement = 'missing';
      } else if (matchCount === totalCount) {
        row.agreement = 'match';
      } else if (matchCount > 0) {
        row.agreement = 'partial';
      } else {
        row.agreement = 'mismatch';
      }

      row.averageShap = sourceRecords.length > 0 ? sumShap / sourceRecords.length : 0;

      return row;
    });
  }, [sourceRecords]);

  if (!sourceRecords || sourceRecords.length === 0) {
    return <Text type="secondary">No records to compare.</Text>;
  }

  const columns: any[] = [
    {
      title: 'Feature',
      dataIndex: 'featureName',
      key: 'featureName',
      fixed: 'left',
      width: 200,
      sorter: (a: any, b: any) => a.featureName.localeCompare(b.featureName),
      render: (text: string, record: any) => (
        <Space>
          <Text strong style={{ fontSize: 13 }}>{text}</Text>
          <Tag 
            color={
              record.agreement === 'match' ? 'success' : 
              record.agreement === 'partial' ? 'warning' : 
              record.agreement === 'mismatch' ? 'error' : 'default'
            }
            style={{ fontSize: 10, marginLeft: 8 }}
          >
            {record.agreement}
          </Tag>
        </Space>
      ),
    },
    ...sourceRecords.map((record, index) => ({
      title: (
        <div style={{ textAlign: 'center' }}>
          <Tag style={{ fontSize: 10 }}>{record.source_system.toUpperCase()}</Tag>
          <br />
          <Text code style={{ fontSize: 10 }}>{record.source_record_id}</Text>
        </div>
      ),
      dataIndex: `record_${index}`,
      key: `record_${index}`,
      align: 'center',
      render: (cellData: any, record: any) => {
        if (!cellData || cellData.value === undefined || cellData.value === null) return <Text type="secondary">—</Text>;
        
        const hasHighShap = cellData.shap && Math.abs(cellData.shap) > 0.1;
        const borderThickness = hasHighShap ? Math.min(Math.abs(cellData.shap) * 5, 4) : 0;
        const borderColor = cellData.shap > 0 ? '#52c41a' : '#f5222d';

        return (
          <Tooltip title={`SHAP: ${cellData.shap?.toFixed(4) || 'N/A'}`}>
            <div 
              style={{
                padding: '6px 12px',
                background: AGREEMENT_COLORS[record.agreement as keyof typeof AGREEMENT_COLORS],
                border: hasHighShap ? `${borderThickness}px solid ${borderColor}` : '1px solid transparent',
                borderRadius: 4,
                display: 'inline-block',
                minWidth: 60,
              }}
            >
              <Text style={{ fontSize: 13 }}>{typeof cellData.value === 'number' ? cellData.value.toFixed(3) : String(cellData.value)}</Text>
            </div>
          </Tooltip>
        );
      }
    })),
  ];

  return (
    <Table
      columns={columns}
      dataSource={tableData}
      pagination={false}
      size="small"
      scroll={{ x: 'max-content' }}
      bordered
    />
  );
};

export default React.memo(FeatureMatrix);
