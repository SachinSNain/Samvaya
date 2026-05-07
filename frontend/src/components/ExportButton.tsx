import React, { useState } from 'react';
import { Dropdown, MenuProps, Button, notification } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { ubidApi } from '../api';
import { handleApiError } from '../utils/errorHandling';

interface ExportButtonProps {
  ubid: string;
}

const ExportButton: React.FC<ExportButtonProps> = ({ ubid }) => {
  const [exporting, setExporting] = useState(false);

  const handleExport = async (format: 'json' | 'csv') => {
    setExporting(true);
    try {
      const response = await ubidApi.export(ubid, format);
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${ubid}_export.${format}`);
      document.body.appendChild(link);
      link.click();
      
      // Clean up
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      notification.success({
        message: 'Export Successful',
        description: `Successfully exported UBID details as ${format.toUpperCase()}`,
        placement: 'bottomRight',
      });
    } catch (error) {
      handleApiError(error, 'Failed to export details');
    } finally {
      setExporting(false);
    }
  };

  const items: MenuProps['items'] = [
    {
      key: 'csv',
      label: 'Export as CSV',
      onClick: () => handleExport('csv'),
    },
    {
      key: 'json',
      label: 'Export as JSON',
      onClick: () => handleExport('json'),
    },
  ];

  return (
    <Dropdown menu={{ items }} disabled={exporting} placement="bottomRight">
      <Button icon={<DownloadOutlined />} loading={exporting} aria-label="Export Data">
        Export
      </Button>
    </Dropdown>
  );
};

export default ExportButton;
