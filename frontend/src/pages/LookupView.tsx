import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Table, Input, Button, Card, Tag, Typography, Space } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { ubidApi } from '../api';
import FilterPanel from '../components/FilterPanel';
import { FilterState, FilterOptions } from '../api/types';

const { Title, Text } = Typography;
const ORANGE = '#FF6B2C';

const STATUS_COLOR: Record<string, string> = {
  ACTIVE: '#52c41a', DORMANT: '#faad14',
  CLOSED_SUSPECTED: '#f5222d', CLOSED_CONFIRMED: '#820014', UNKNOWN: '#8c8c8c',
};

const LookupView: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchName, setSearchName] = useState('');
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [totalRecords, setTotalRecords] = useState(0);

  // Filter states
  const [filters, setFilters] = useState<FilterState>({
    activity_status: [],
    departments: [],
    pincode: '',
  });
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);
  const [filtersLoading, setFiltersLoading] = useState(false);

  const fetchFilters = async () => {
    setFiltersLoading(true);
    try {
      const res = await ubidApi.getFilters();
      setFilterOptions(res.data);
    } catch {
      // silent fail or handle
    } finally {
      setFiltersLoading(false);
    }
  };

  const fetchData = useCallback(async (
    name = searchName, 
    currentFilters = filters,
    page = currentPage,
    size = pageSize
  ) => {
    setLoading(true);
    try {
      const res = await ubidApi.list(page, size, name, currentFilters);
      setData(res.data?.results || []);
      setTotalRecords(res.data?.total || 0);
    } catch { /* silent */ }
    setLoading(false);
  }, [searchName, filters, currentPage, pageSize]);

  useEffect(() => {
    fetchFilters();
    fetchData(searchName, filters, 1, pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounced search effect when filters or search change
  useEffect(() => {
    const timer = setTimeout(() => {
      setCurrentPage(1);
      fetchData(searchName, filters, 1, pageSize);
    }, 300);
    return () => clearTimeout(timer);
  }, [filters, searchName]);

  const handleTableChange = (pagination: any) => {
    setCurrentPage(pagination.current);
    setPageSize(pagination.pageSize);
    fetchData(searchName, filters, pagination.current, pagination.pageSize);
  };

  const columns = [
    {
      title: 'UBID',
      dataIndex: 'ubid',
      key: 'ubid',
      width: 160,
      sorter: (a: any, b: any) => a.ubid.localeCompare(b.ubid),
      render: (ubid: string) => (
        <Text code style={{ fontSize: 11, color: ORANGE }}>{ubid}</Text>
      ),
    },
    {
      title: 'Business Name',
      dataIndex: 'display_name',
      key: 'display_name',
      sorter: (a: any, b: any) => (a.display_name || '').localeCompare(b.display_name || ''),
      render: (name: string) => name
        ? <Text strong style={{ fontSize: 13 }}>{name}</Text>
        : <Text type="secondary">—</Text>,
    },
    {
      title: 'Activity',
      dataIndex: 'activity_status',
      key: 'activity_status',
      width: 130,
      sorter: (a: any, b: any) => (a.activity_status || '').localeCompare(b.activity_status || ''),
      render: (status: string) => (
        <Tag
          style={{
            background: `${STATUS_COLOR[status] ?? '#8c8c8c'}18`,
            color: STATUS_COLOR[status] ?? '#8c8c8c',
            border: `1px solid ${STATUS_COLOR[status] ?? '#8c8c8c'}44`,
            fontWeight: 600, fontSize: 11,
          }}
        >
          {status || 'UNKNOWN'}
        </Tag>
      ),
    },
    {
      title: '',
      key: 'action',
      width: 110,
      render: (_: any, record: any) => (
        <Button
          type="link"
          size="small"
          onClick={(e) => { e.stopPropagation(); navigate(`/dashboard/lookup/${record.ubid}`); }}
          style={{ color: ORANGE, padding: 0, fontSize: 12, fontWeight: 500 }}
          aria-label={`View details for ${record.ubid}`}
        >
          View Details
        </Button>
      ),
    },
  ];

  return (
    <div style={{ backgroundColor: '#fcfcfc', minHeight: '100vh', padding: '24px', margin: '-24px' }}>
      <div style={{ marginBottom: 24, paddingLeft: 8 }}>
        <Title level={2} style={{ margin: 0, fontWeight: 700, letterSpacing: '-0.5px' }}>UBID Directory</Title>
        <Text type="secondary" style={{ fontSize: 14 }}>
          Unified Business Identifier registry — search across all linked department records
        </Text>
      </div>

      <Card 
        style={{ 
          marginBottom: 16, 
          borderRadius: 12, 
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
          border: '1px solid #f0f0f0' 
        }} 
        bodyStyle={{ padding: '20px 24px' }}
      >
        <Space size="large">
          <Input
            placeholder="Search by company name…"
            prefix={<SearchOutlined style={{ color: '#bfbfbf', fontSize: 16, marginRight: 6 }} />}
            style={{ width: 360, borderRadius: 8, height: 44, fontSize: 15 }}
            value={searchName}
            onChange={e => setSearchName(e.target.value)}
            allowClear
            aria-label="Search by company name"
          />
          <Text type="secondary" style={{ fontSize: 12, marginLeft: 16 }}>
            {totalRecords} result{totalRecords !== 1 ? 's' : ''}
          </Text>
        </Space>
      </Card>

      <FilterPanel
        filters={filters}
        options={filterOptions}
        onChange={setFilters}
        loading={filtersLoading}
      />

      <Card 
        style={{ 
          borderRadius: 12, 
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
          border: '1px solid #f0f0f0',
          overflow: 'hidden'
        }} 
        bodyStyle={{ padding: 0 }}
      >
        <Table
          columns={columns}
          dataSource={data}
          rowKey="ubid"
          loading={loading}
          size="middle"
          pagination={{ 
            current: currentPage,
            pageSize: pageSize,
            total: totalRecords,
            position: ['bottomRight'],
            showSizeChanger: true,
          }}
          onChange={handleTableChange}
          onRow={record => ({ onClick: () => navigate(`/dashboard/lookup/${record.ubid}`), style: { cursor: 'pointer' } })}
          rowClassName={() => 'hover-row'}
          locale={{
            emptyText: loading ? 'Loading...' : 'No results found. Try clearing your filters or search.'
          }}
        />
      </Card>
    </div>
  );
};

export default LookupView;
