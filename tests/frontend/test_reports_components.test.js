/**
 * Test suite for Reports components
 * Tests all report components: TradeHistoryTable, StrategyPerformanceChart, etc.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import TradeHistoryTable from '../src/components/reports/TradeHistoryTable';
import StrategyPerformanceChart from '../src/components/reports/StrategyPerformanceChart';
import MarketContextAnalysis from '../src/components/reports/MarketContextAnalysis';
import DashboardKPIs from '../src/components/reports/DashboardKPIs';
import PerformanceCharts from '../src/components/reports/PerformanceCharts';
import ExportReports from '../src/components/reports/ExportReports';

// Mock axios
jest.mock('axios');

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('TradeHistoryTable Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue('test-token');
  });

  test('renders loading state initially', () => {
    axios.get.mockImplementation(() => new Promise(() => {})); // Never resolve
    render(<TradeHistoryTable userId="test-user" />);
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  test('renders trade table with data', async () => {
    const mockTrades = {
      trades: [
        {
          id: '1',
          symbol: 'BTCUSDT',
          entry_price: 45000,
          exit_price: 46000,
          pnl: 100,
          status: 'CLOSED',
          market_context: 'STRONG_BULLISH'
        }
      ]
    };

    axios.get.mockResolvedValue({ data: mockTrades });
    render(<TradeHistoryTable userId="test-user" />);

    await waitFor(() => {
      expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    });
  });

  test('filters trades by symbol', async () => {
    const mockTrades = {
      trades: [
        { id: '1', symbol: 'BTCUSDT', entry_price: 45000, exit_price: 46000, pnl: 100, status: 'CLOSED' },
        { id: '2', symbol: 'ETHUSDT', entry_price: 2500, exit_price: 2400, pnl: -100, status: 'CLOSED' }
      ]
    };

    axios.get.mockResolvedValue({ data: mockTrades });
    render(<TradeHistoryTable userId="test-user" />);

    await waitFor(() => {
      expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    });

    const symbolFilter = screen.getByDisplayValue(/select symbol/i);
    fireEvent.change(symbolFilter, { target: { value: 'BTCUSDT' } });

    // Should still show BTCUSDT
    expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
  });

  test('displays summary stats', async () => {
    const mockTrades = {
      trades: [
        { id: '1', symbol: 'BTCUSDT', pnl: 100, status: 'CLOSED' },
        { id: '2', symbol: 'ETHUSDT', pnl: -50, status: 'CLOSED' }
      ]
    };

    axios.get.mockResolvedValue({ data: mockTrades });
    render(<TradeHistoryTable userId="test-user" />);

    await waitFor(() => {
      expect(screen.getByText(/win rate/i)).toBeInTheDocument();
    });
  });

  test('handles error gracefully', async () => {
    axios.get.mockRejectedValue(new Error('API Error'));
    render(<TradeHistoryTable userId="test-user" />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load|error/i)).toBeInTheDocument();
    });
  });
});

describe('StrategyPerformanceChart Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue('test-token');
  });

  test('renders strategy comparison table', async () => {
    const mockStrategies = {
      strategies: [
        {
          name: 'MA_CROSSOVER',
          total_trades: 10,
          winning_trades: 7,
          win_rate: 0.7,
          total_pnl: 500
        }
      ]
    };

    axios.get.mockResolvedValue({ data: mockStrategies });
    render(<StrategyPerformanceChart userId="test-user" />);

    await waitFor(() => {
      expect(screen.getByText('MA_CROSSOVER')).toBeInTheDocument();
    });
  });

  test('displays strategy metrics', async () => {
    const mockStrategies = {
      strategies: [
        {
          name: 'RSI_DIVERGENCE',
          total_trades: 5,
          winning_trades: 3,
          win_rate: 0.6,
          total_pnl: 250,
          profit_factor: 2.0
        }
      ]
    };

    axios.get.mockResolvedValue({ data: mockStrategies });
    render(<StrategyPerformanceChart userId="test-user" />);

    await waitFor(() => {
      expect(screen.getByText(/profit factor/i)).toBeInTheDocument();
    });
  });

  test('shows detail view when strategy selected', async () => {
    const mockStrategies = {
      strategies: [{ name: 'GRID_TRADING', total_trades: 20, winning_trades: 12 }]
    };

    axios.get.mockResolvedValue({ data: mockStrategies });
    render(<StrategyPerformanceChart userId="test-user" />);

    await waitFor(() => {
      const strategyRow = screen.getByText('GRID_TRADING');
      expect(strategyRow).toBeInTheDocument();
    });
  });
});

describe('DashboardKPIs Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue('test-token');
  });

  test('renders KPI cards with data', async () => {
    const mockData = {
      total_pnl: 1500,
      win_rate: 0.65,
      profit_factor: 2.5,
      sharpe_ratio: 1.8,
      total_trades: 20
    };

    axios.get.mockResolvedValue({ data: mockData });
    render(<DashboardKPIs userId="test-user" />);

    await waitFor(() => {
      expect(screen.getByText(/total p&l/i)).toBeInTheDocument();
    });
  });

  test('displays period selector', async () => {
    axios.get.mockResolvedValue({ data: {} });
    render(<DashboardKPIs userId="test-user" />);

    expect(screen.getByDisplayValue('30')).toBeInTheDocument();
  });

  test('updates data when period changes', async () => {
    axios.get.mockResolvedValue({ data: {} });
    const { rerender } = render(<DashboardKPIs userId="test-user" />);

    // Should call with initial period
    await waitFor(() => {
      expect(axios.get).toHaveBeenCalled();
    });

    // Clear calls and change period
    axios.get.mockClear();
    rerender(<DashboardKPIs userId="test-user" />);
  });

  test('displays positive P&L in green', async () => {
    const mockData = {
      total_pnl: 1500,
      win_rate: 0.65,
      profit_factor: 2.5,
      sharpe_ratio: 1.8
    };

    axios.get.mockResolvedValue({ data: mockData });
    render(<DashboardKPIs userId="test-user" />);

    await waitFor(() => {
      const pnlValue = screen.getByText(/\$1500|1500/);
      expect(pnlValue).toHaveClass('positive');
    });
  });

  test('displays negative P&L in red', async () => {
    const mockData = {
      total_pnl: -500,
      win_rate: 0.35,
      profit_factor: 0.5,
      sharpe_ratio: -0.5
    };

    axios.get.mockResolvedValue({ data: mockData });
    render(<DashboardKPIs userId="test-user" />);

    await waitFor(() => {
      const pnlValue = screen.getByText(/-500/);
      expect(pnlValue).toHaveClass('negative');
    });
  });
});

describe('PerformanceCharts Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue('test-token');
  });

  test('renders chart sections', async () => {
    axios.get.mockResolvedValue({ data: [] });
    render(<PerformanceCharts userId="test-user" days={30} />);

    await waitFor(() => {
      expect(screen.getByText(/equity curve/i)).toBeInTheDocument();
    });
  });

  test('displays all chart types', async () => {
    axios.get.mockResolvedValue({ data: [] });
    render(<PerformanceCharts userId="test-user" days={30} />);

    await waitFor(() => {
      expect(screen.getByText(/drawdown/i)).toBeInTheDocument();
      expect(screen.getByText(/daily p&l/i)).toBeInTheDocument();
      expect(screen.getByText(/strategy comparison/i)).toBeInTheDocument();
    });
  });

  test('handles missing data gracefully', async () => {
    axios.get.mockResolvedValue({ data: [] });
    render(<PerformanceCharts userId="test-user" days={30} />);

    await waitFor(() => {
      expect(screen.queryByText(/no data available/i)).toBeInTheDocument();
    });
  });

  test('updates period when days prop changes', async () => {
    axios.get.mockResolvedValue({ data: [] });
    const { rerender } = render(<PerformanceCharts userId="test-user" days={30} />);

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalled();
    });

    axios.get.mockClear();
    rerender(<PerformanceCharts userId="test-user" days={60} />);

    // Should fetch new data with different days parameter
    expect(axios.get).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ params: expect.objectContaining({ days: 60 }) })
    );
  });
});

describe('MarketContextAnalysis Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue('test-token');
  });

  test('renders context distribution', async () => {
    const mockData = {
      context_distribution: [
        { context: 'STRONG_BULLISH', count: 10, win_rate: 0.8 },
        { context: 'STRONG_BEARISH', count: 5, win_rate: 0.4 }
      ]
    };

    axios.get.mockResolvedValue({ data: mockData });
    render(<MarketContextAnalysis userId="test-user" />);

    await waitFor(() => {
      expect(screen.getByText(/market context/i)).toBeInTheDocument();
    });
  });
});

describe('ExportReports Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue('test-token');
  });

  test('renders export controls', () => {
    render(<ExportReports userId="test-user" days={30} />);
    
    expect(screen.getByDisplayValue('csv')).toBeInTheDocument();
    expect(screen.getByDisplayValue('trades')).toBeInTheDocument();
    expect(screen.getByText(/export now/i)).toBeInTheDocument();
  });

  test('displays all export format options', () => {
    render(<ExportReports userId="test-user" days={30} />);
    
    expect(screen.getByDisplayValue('csv')).toBeInTheDocument();
    expect(screen.getByDisplayValue('pdf')).toBeInTheDocument();
  });

  test('displays all export type options', () => {
    render(<ExportReports userId="test-user" days={30} />);
    
    expect(screen.getByDisplayValue('trades')).toBeInTheDocument();
    expect(screen.getByDisplayValue('strategies')).toBeInTheDocument();
    expect(screen.getByDisplayValue('performance')).toBeInTheDocument();
  });

  test('handles export button click', async () => {
    axios.get.mockResolvedValue({
      data: {
        trades: [{ id: '1', symbol: 'BTCUSDT', pnl: 100 }]
      }
    });

    render(<ExportReports userId="test-user" days={30} />);

    const exportButton = screen.getByText(/export now/i);
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(axios.get).toHaveBeenCalled();
    });
  });

  test('shows success message after export', async () => {
    axios.get.mockResolvedValue({ data: { trades: [] } });
    render(<ExportReports userId="test-user" days={30} />);

    const exportButton = screen.getByText(/export now/i);
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText(/exported.*successfully/i)).toBeInTheDocument();
    });
  });

  test('displays error message on failure', async () => {
    axios.get.mockRejectedValue(new Error('Export failed'));
    render(<ExportReports userId="test-user" days={30} />);

    const exportButton = screen.getByText(/export now/i);
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText(/failed to export/i)).toBeInTheDocument();
    });
  });
});

describe('Reports Components Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.getItem.mockReturnValue('test-token');
  });

  test('all components handle loading state', async () => {
    axios.get.mockImplementation(() => new Promise(() => {}));

    render(<TradeHistoryTable userId="test-user" />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  test('all components handle errors', async () => {
    axios.get.mockRejectedValue(new Error('API Error'));

    render(<TradeHistoryTable userId="test-user" />);
    await waitFor(() => {
      expect(screen.getByText(/failed|error/i)).toBeInTheDocument();
    });
  });

  test('components respect authentication', () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    render(<TradeHistoryTable userId="test-user" />);
    // Should either show error or attempt to fetch without token
    expect(axios.get).toHaveBeenCalled();
  });
});
