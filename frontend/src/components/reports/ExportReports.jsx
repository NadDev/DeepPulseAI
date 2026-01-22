import React, { useState } from 'react';
import axios from 'axios';
import './ExportReports.css';

/**
 * ExportReports Component
 * Export trade history, strategies, and metrics to PDF or CSV
 */
const ExportReports = ({ userId, days = 30 }) => {
  const [exportFormat, setExportFormat] = useState('csv');
  const [exportType, setExportType] = useState('trades');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleExport = async () => {
    setLoading(true);
    setMessage('');
    try {
      const token = localStorage.getItem('supabaseAuthToken');
      
      // Fetch data based on export type
      let data;
      let filename;
      
      if (exportType === 'trades') {
        const res = await axios.get('/api/reports/trades', {
          params: { days },
          headers: { Authorization: `Bearer ${token}` }
        });
        data = res.data.trades;
        filename = `trades_${new Date().toISOString().split('T')[0]}`;
      } else if (exportType === 'strategies') {
        const res = await axios.get('/api/reports/strategies', {
          params: { days },
          headers: { Authorization: `Bearer ${token}` }
        });
        data = res.data.strategies;
        filename = `strategies_${new Date().toISOString().split('T')[0]}`;
      } else if (exportType === 'performance') {
        const res = await axios.get('/api/reports/performance', {
          headers: { Authorization: `Bearer ${token}` }
        });
        data = [res.data];
        filename = `performance_${new Date().toISOString().split('T')[0]}`;
      }

      if (exportFormat === 'csv') {
        exportToCSV(data, filename);
      } else if (exportFormat === 'pdf') {
        exportToPDF(data, filename, exportType);
      }

      setMessage(`✅ ${exportType.toUpperCase()} exported as ${exportFormat.toUpperCase()} successfully!`);
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Export error:', error);
      setMessage('❌ Failed to export. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const exportToCSV = (data, filename) => {
    if (!data || data.length === 0) {
      alert('No data to export');
      return;
    }

    // Get all unique keys
    const allKeys = new Set();
    data.forEach(item => {
      Object.keys(item).forEach(key => allKeys.add(key));
    });
    const headers = Array.from(allKeys);

    // Create CSV content
    let csv = headers.join(',') + '\n';
    data.forEach(item => {
      const row = headers.map(header => {
        const value = item[header];
        // Handle nested objects and arrays
        if (typeof value === 'object') {
          return `"${JSON.stringify(value).replace(/"/g, '""')}"`;
        }
        // Escape quotes in strings
        const stringValue = String(value || '');
        return stringValue.includes(',') || stringValue.includes('"') 
          ? `"${stringValue.replace(/"/g, '""')}"` 
          : stringValue;
      });
      csv += row.join(',') + '\n';
    });

    // Create blob and download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportToPDF = async (data, filename, exportType) => {
    try {
      // Dynamic import for jsPDF
      const { jsPDF } = await import('jspdf');
      const doc = new jsPDF();
      
      // Add title
      doc.setFontSize(16);
      doc.text(`${exportType.toUpperCase()} Report`, 14, 15);
      
      // Add date
      doc.setFontSize(10);
      doc.text(`Generated: ${new Date().toLocaleDateString()}`, 14, 25);
      
      // Add data table
      const headers = Object.keys(data[0] || {});
      const rows = data.map(item =>
        headers.map(header => {
          const value = item[header];
          if (typeof value === 'object') {
            return JSON.stringify(value).substring(0, 20);
          }
          return String(value).substring(0, 30);
        })
      );

      // Simple table rendering (jsPDF doesn't have built-in table support in all versions)
      let yPos = 35;
      const pageHeight = doc.internal.pageSize.getHeight();
      const lineHeight = 7;
      const headerColor = [59, 130, 246]; // Blue
      const rowColor = [226, 232, 240]; // Light gray

      // Header row
      doc.setFillColor(...headerColor);
      doc.setTextColor(255, 255, 255);
      let xPos = 14;
      headers.forEach(header => {
        doc.text(header.substring(0, 12), xPos, yPos);
        xPos += 30;
      });
      yPos += lineHeight;

      // Data rows
      doc.setTextColor(0, 0, 0);
      rows.forEach((row, rowIdx) => {
        if (yPos + lineHeight > pageHeight - 10) {
          doc.addPage();
          yPos = 15;
        }
        if (rowIdx % 2 === 0) {
          doc.setFillColor(...rowColor);
          doc.rect(14, yPos - 3, 180, lineHeight, 'F');
        }
        xPos = 14;
        row.forEach(cell => {
          doc.text(String(cell), xPos, yPos);
          xPos += 30;
        });
        yPos += lineHeight;
      });

      // Save PDF
      doc.save(`${filename}.pdf`);
    } catch (error) {
      console.error('PDF generation error:', error);
      alert('PDF export requires jsPDF library. Please install: npm install jspdf');
    }
  };

  return (
    <div className="export-reports-container">
      <div className="export-section">
        <h3>📥 Export Reports</h3>
        <p>Download your trading reports in CSV or PDF format</p>

        <div className="export-controls">
          <div className="control-group">
            <label htmlFor="export-type">Export Type:</label>
            <select
              id="export-type"
              value={exportType}
              onChange={(e) => setExportType(e.target.value)}
              disabled={loading}
            >
              <option value="trades">Trade History</option>
              <option value="strategies">Strategy Performance</option>
              <option value="performance">Overall Performance</option>
            </select>
          </div>

          <div className="control-group">
            <label htmlFor="export-format">Format:</label>
            <select
              id="export-format"
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
              disabled={loading}
            >
              <option value="csv">CSV (Excel)</option>
              <option value="pdf">PDF</option>
            </select>
          </div>

          <button
            className="export-button"
            onClick={handleExport}
            disabled={loading}
          >
            {loading ? '⏳ Exporting...' : '📥 Export Now'}
          </button>
        </div>

        {message && (
          <div className={`export-message ${message.startsWith('✅') ? 'success' : 'error'}`}>
            {message}
          </div>
        )}

        <div className="export-info">
          <h4>📋 Export Details</h4>
          <ul>
            <li><strong>Trade History:</strong> All trades with entry/exit prices, P&L, and market context</li>
            <li><strong>Strategy Performance:</strong> Win rates, profit factors, and context breakdowns for each strategy</li>
            <li><strong>Overall Performance:</strong> Summary metrics including Sharpe ratio, max drawdown, and total P&L</li>
            <li><strong>CSV Format:</strong> Compatible with Excel, Google Sheets, and data analysis tools</li>
            <li><strong>PDF Format:</strong> Professional report format with formatting and headers</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ExportReports;
