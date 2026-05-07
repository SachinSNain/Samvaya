import React from 'react';
import { Card, Checkbox, Input, Button, Space, Typography, Badge, Row, Col, Popover } from 'antd';
import { DownOutlined, EnvironmentOutlined } from '@ant-design/icons';
import { FilterState, FilterOptions } from '../api/types';

const { Text } = Typography;

// Department system keys → human-readable labels
const DEPT_LABEL_MAP: Record<string, string> = {
  shop_establishment: 'Shop & Establishment',
  factories: 'Factories',
  labour: 'Labour',
  kspcb: 'KSPCB',
};

// Fixed activity status options — not fetched from API
const ACTIVITY_OPTIONS = [
  { label: 'Active',   value: 'ACTIVE' },
  { label: 'Dormant',  value: 'DORMANT' },
  { label: 'Inactive', value: 'INACTIVE' },
];

interface FilterPanelProps {
  filters: FilterState;
  options: FilterOptions | null;
  onChange: (newFilters: FilterState) => void;
  loading?: boolean;
}

const FilterPanel: React.FC<FilterPanelProps> = ({ filters, options, onChange, loading = false }) => {
  const getActiveFilterCount = () => {
    let count = 0;
    count += filters.activity_status.length;
    count += filters.departments.length;
    if (filters.pincode && filters.pincode.trim()) count += 1;
    return count;
  };

  const handleClearAll = () => {
    onChange({ activity_status: [], departments: [], pincode: '' });
  };

  const activeCount = getActiveFilterCount();

  // Resolve department options: prefer API counts, fallback to fixed list
  const deptOptions = options?.departments && options.departments.length > 0
    ? options.departments.map(opt => ({
        label: `${DEPT_LABEL_MAP[opt.value] ?? opt.label} (${opt.count})`,
        value: opt.value,
      }))
    : Object.entries(DEPT_LABEL_MAP).map(([value, label]) => ({ label, value }));

  const popoverButtonProps = {
    style: {
      width: '100%',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      borderRadius: '8px',
      height: '40px',
      backgroundColor: '#f8f9fa',
      border: '1px solid #d9d9d9',
      boxShadow: '0 2px 4px rgba(0,0,0,0.02)',
    }
  };

  return (
    <Card
      size="small"
      title={
        <Space>
          <Text strong style={{ fontSize: '15px' }}>Filters</Text>
          {activeCount > 0 && <Badge count={activeCount} color="#FF6B2C" />}
        </Space>
      }
      extra={
        <Button
          type="link"
          size="small"
          onClick={handleClearAll}
          disabled={activeCount === 0 || loading}
          style={{ fontWeight: 600, color: '#FF6B2C' }}
        >
          Clear All
        </Button>
      }
      style={{
        marginBottom: 20,
        borderRadius: 12,
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
        border: '1px solid #f0f0f0'
      }}
      bodyStyle={{ padding: '20px 24px' }}
    >
      <Row gutter={[24, 24]} align="middle" style={{ width: '100%', margin: 0 }}>
        {/* Activity Status Dropdown */}
        <Col span={8}>
          <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 13, color: '#555' }}>
            Activity Status
          </Text>
          <Popover
            content={
              <div style={{ padding: '8px 4px', minWidth: 200 }}>
                <Checkbox.Group
                  options={ACTIVITY_OPTIONS}
                  value={filters.activity_status}
                  onChange={vals => onChange({ ...filters, activity_status: vals as string[] })}
                  style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
                  disabled={loading}
                />
              </div>
            }
            trigger="click"
            placement="bottomLeft"
          >
            <Button {...popoverButtonProps}>
              <Text>
                {filters.activity_status.length > 0
                  ? `${filters.activity_status.length} selected`
                  : 'Select Status'}
              </Text>
              <DownOutlined style={{ fontSize: 10, color: '#888' }} />
            </Button>
          </Popover>
        </Col>

        {/* Departments Dropdown */}
        <Col span={8}>
          <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 13, color: '#555' }}>
            Departments
          </Text>
          <Popover
            content={
              <div style={{ padding: '8px 4px', minWidth: 240 }}>
                <Checkbox.Group
                  options={deptOptions}
                  value={filters.departments}
                  onChange={vals => onChange({ ...filters, departments: vals as string[] })}
                  style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
                  disabled={loading}
                />
              </div>
            }
            trigger="click"
            placement="bottomLeft"
          >
            <Button {...popoverButtonProps}>
              <Text>
                {filters.departments.length > 0
                  ? `${filters.departments.length} selected`
                  : 'Select Departments'}
              </Text>
              <DownOutlined style={{ fontSize: 10, color: '#888' }} />
            </Button>
          </Popover>
        </Col>

        {/* Pincode */}
        <Col span={8}>
          <Text strong style={{ display: 'block', marginBottom: 8, fontSize: 13, color: '#555' }}>
            Pincode
          </Text>
          <Input
            placeholder="Search by pincode (e.g. 560001)"
            value={filters.pincode}
            onChange={e => onChange({ ...filters, pincode: e.target.value })}
            allowClear
            maxLength={6}
            prefix={<EnvironmentOutlined style={{ color: '#bfbfbf', marginRight: 4 }} />}
            style={{ 
              width: '100%', 
              height: '40px',
              borderRadius: '8px',
              backgroundColor: '#f8f9fa',
              boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.02)'
            }}
            disabled={loading}
          />
        </Col>
      </Row>
    </Card>
  );
};

export default React.memo(FilterPanel);
