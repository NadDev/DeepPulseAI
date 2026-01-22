/**
 * Test suite for Reports Page
 * Tests the main Reports page with tab navigation
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import axios from 'axios';
import Reports from '../src/pages/Reports';

jest.mock('axios');

const localStorageMock = {
  getItem: jest.fn(() => 'test-user-id'),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('Reports Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    axios.get.mockResolvedValue({ data: {} });
  });

  test('renders Reports page with title', () => {
    render(<Reports />);
    expect(screen.getByText(/trading reports & analytics/i)).toBeInTheDocument();
  });

  test('renders all tab buttons', () => {
    render(<Reports />);
    
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/trades/i)).toBeInTheDocument();
    expect(screen.getByText(/strategies/i)).toBeInTheDocument();
    expect(screen.getByText(/market context/i)).toBeInTheDocument();
    expect(screen.getByText(/charts/i)).toBeInTheDocument();
    expect(screen.getByText(/export/i)).toBeInTheDocument();
  });

  test('dashboard tab is active by default', () => {
    render(<Reports />);
    
    const dashboardTab = screen.getByText(/dashboard/i).closest('button');
    expect(dashboardTab).toHaveClass('active');
  });

  test('switches to trades tab on click', async () => {
    render(<Reports />);
    
    const tradesTab = screen.getByText(/trades/i).closest('button');
    fireEvent.click(tradesTab);
    
    await waitFor(() => {
      expect(tradesTab).toHaveClass('active');
    });
  });

  test('switches to strategies tab on click', async () => {
    render(<Reports />);
    
    const strategiesTab = screen.getByText(/strategies/i).closest('button');
    fireEvent.click(strategiesTab);
    
    await waitFor(() => {
      expect(strategiesTab).toHaveClass('active');
    });
  });

  test('switches to context tab on click', async () => {
    render(<Reports />);
    
    const contextTab = screen.getByText(/market context/i).closest('button');
    fireEvent.click(contextTab);
    
    await waitFor(() => {
      expect(contextTab).toHaveClass('active');
    });
  });

  test('switches to charts tab on click', async () => {
    render(<Reports />);
    
    const chartsTab = screen.getByText(/charts/i).closest('button');
    fireEvent.click(chartsTab);
    
    await waitFor(() => {
      expect(chartsTab).toHaveClass('active');
    });
  });

  test('switches to export tab on click', async () => {
    render(<Reports />);
    
    const exportTab = screen.getByText(/export/i).closest('button');
    fireEvent.click(exportTab);
    
    await waitFor(() => {
      expect(exportTab).toHaveClass('active');
    });
  });

  test('period selector is present', () => {
    render(<Reports />);
    
    const periodSelect = screen.getByDisplayValue('30');
    expect(periodSelect).toBeInTheDocument();
  });

  test('period options are available', () => {
    render(<Reports />);
    
    const periodSelect = screen.getByDisplayValue('30');
    expect(periodSelect.querySelector('option[value="7"]')).toBeInTheDocument();
    expect(periodSelect.querySelector('option[value="30"]')).toBeInTheDocument();
    expect(periodSelect.querySelector('option[value="60"]')).toBeInTheDocument();
    expect(periodSelect.querySelector('option[value="90"]')).toBeInTheDocument();
    expect(periodSelect.querySelector('option[value="365"]')).toBeInTheDocument();
  });

  test('changes period when selector changes', async () => {
    render(<Reports />);
    
    const periodSelect = screen.getByDisplayValue('30');
    fireEvent.change(periodSelect, { target: { value: '60' } });
    
    await waitFor(() => {
      expect(periodSelect.value).toBe('60');
    });
  });

  test('renders description text', () => {
    render(<Reports />);
    
    expect(screen.getByText(/comprehensive analysis of your trading performance/i)).toBeInTheDocument();
  });

  test('maintains active tab when period changes', async () => {
    render(<Reports />);
    
    // Switch to trades tab
    const tradesTab = screen.getByText(/trades/i).closest('button');
    fireEvent.click(tradesTab);
    
    // Change period
    const periodSelect = screen.getByDisplayValue('30');
    fireEvent.change(periodSelect, { target: { value: '60' } });
    
    // Trades tab should still be active
    await waitFor(() => {
      expect(tradesTab).toHaveClass('active');
    });
  });

  test('tabs have emoji icons', () => {
    render(<Reports />);
    
    const dashboardTab = screen.getByText(/dashboard/i).closest('button');
    expect(dashboardTab.textContent).toContain('📊');
  });

  test('renders tab content for active tab', async () => {
    render(<Reports />);
    
    // Dashboard tab should be rendering its content
    // (actual content depends on component rendering)
    const tabContent = screen.getByRole('main') || document.querySelector('.tab-content');
    expect(tabContent).toBeInTheDocument();
  });

  test('handles tab switching multiple times', async () => {
    render(<Reports />);
    
    const tabs = [
      { text: /dashboard/i, name: 'Dashboard' },
      { text: /trades/i, name: 'Trades' },
      { text: /strategies/i, name: 'Strategies' },
    ];
    
    for (const tab of tabs) {
      const tabButton = screen.getByText(tab.text).closest('button');
      fireEvent.click(tabButton);
      
      await waitFor(() => {
        expect(tabButton).toHaveClass('active');
      });
    }
  });

  test('renders all period options correctly', () => {
    render(<Reports />);
    
    const periodSelect = screen.getByDisplayValue('30');
    const options = periodSelect.querySelectorAll('option');
    
    expect(options.length).toBe(5);
    expect(options[0].value).toBe('7');
    expect(options[1].value).toBe('30');
    expect(options[2].value).toBe('60');
    expect(options[3].value).toBe('90');
    expect(options[4].value).toBe('365');
  });

  test('page renders without errors', () => {
    expect(() => {
      render(<Reports />);
    }).not.toThrow();
  });

  test('accessibility - tab buttons are keyboard accessible', async () => {
    render(<Reports />);
    
    const tradesTab = screen.getByText(/trades/i).closest('button');
    
    // Should be focusable
    tradesTab.focus();
    expect(document.activeElement).toBe(tradesTab);
  });
});
