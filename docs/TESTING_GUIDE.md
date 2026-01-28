# DeepPulseAI Reports System - Test Suite

Comprehensive test coverage for the Reports & Analytics system with 10 implementation tasks.

## 📋 Test Overview

This test suite includes:
- **Backend API Tests**: FastAPI endpoint testing with pytest
- **Frontend Component Tests**: React component unit tests with Jest
- **Integration Tests**: Complete workflow testing
- **Data Validation Tests**: Consistency and integrity checks
- **Performance Tests**: Response time and load testing

## 🗂️ Test Files

### Backend Tests

#### `tests/api/test_reports_endpoints.py` (250+ lines)
Tests all Reports API endpoints:
- `GET /api/reports/dashboard` - Dashboard summary
- `GET /api/reports/trades` - Trade history with filters
- `GET /api/reports/trades/context-performance` - Market context breakdown
- `GET /api/reports/strategies` - Strategy list and performance
- `GET /api/reports/strategies/{strategy_name}` - Strategy details
- `GET /api/reports/equity-curve` - Equity curve data
- `GET /api/reports/drawdown-history` - Drawdown tracking
- `GET /api/reports/performance` - Overall performance metrics

**Test Classes:**
- `TestReportsEndpoints` - Basic endpoint functionality (10 tests)
- `TestReportsDataValidation` - Data accuracy checks (4 tests)
- `TestReportsPerformance` - Response time validation (2 tests)
- `TestReportsAggregation` - Data consistency (3 tests)

#### `tests/integration/test_reports_integration.py` (400+ lines)
Complete workflow integration tests:
- Dashboard viewing workflow
- Trade analysis workflow
- Strategy comparison workflow
- Performance charting workflow
- Multi-period comparison
- Export preparation workflow
- Data consistency validation
- Error handling scenarios
- Authentication/authorization
- Concurrent request handling

**Test Classes:**
- `TestReportsWorkflow` - User workflows (6 tests)
- `TestReportsDataConsistency` - Cross-endpoint consistency (3 tests)
- `TestReportsErrorHandling` - Error scenarios (6 tests)
- `TestReportsAuthentication` - Auth/security (2 tests)
- `TestReportsPerformance` - Performance characteristics (4 tests)
test 
### Frontend Tests

#### `tests/frontend/test_reports_components.test.js` (500+ lines)
React component unit tests:

**Components Tested:**
1. `TradeHistoryTable` (6 tests)
   - Loading state
   - Data rendering
   - Filtering
   - Summary stats
   - Error handling

2. `StrategyPerformanceChart` (3 tests)
   - Table rendering
   - Metrics display
   - Detail view

3. `DashboardKPIs` (5 tests)
   - KPI card rendering
   - Period selector
   - Data updates
   - Positive/negative P&L styling

4. `PerformanceCharts` (4 tests)
   - Chart section rendering
   - All chart types
   - Data handling
   - Period updates

5. `MarketContextAnalysis` (1 test)
   - Context distribution

6. `ExportReports` (7 tests)
   - Export controls
   - Format options
   - Export type options
   - Button interaction
   - Success messages
   - Error handling

7. **Integration Tests** (3 tests)
   - Loading state handling
   - Error handling
   - Authentication

#### `tests/frontend/test_reports_page.test.js` (200+ lines)
Reports page integration tests (20 tests):
- Page rendering
- Tab navigation
- Period selector
- Tab switching
- Active state management
- Icon display
- Accessibility

## 🚀 Running Tests

### Backend Tests

**Install pytest (if not already installed):**
```bash
pip install pytest pytest-cov pytest-asyncio httpx
```

**Run all backend tests:**
```bash
pytest tests/
```

**Run specific test file:**
```bash
pytest tests/api/test_reports_endpoints.py -v
```

**Run with coverage:**
```bash
pytest tests/ --cov=app --cov-report=html
```

**Run specific test class:**
```bash
pytest tests/api/test_reports_endpoints.py::TestReportsEndpoints -v
```

**Run specific test:**
```bash
pytest tests/api/test_reports_endpoints.py::TestReportsEndpoints::test_get_trades_history -v
```

### Frontend Tests

**Install Jest and dependencies:**
```bash
cd frontend
npm install
```

**Run all frontend tests:**
```bash
npm test
```

**Run tests in watch mode:**
```bash
npm run test:watch
```

**Run only report tests:**
```bash
npm run test:reports
```

**Run with coverage:**
```bash
npm run test:coverage
```

**Run specific test file:**
```bash
npm test test_reports_page.test.js
```

## 📊 Test Coverage

### Backend Coverage
- **Endpoints**: 100% (8 endpoints tested)
- **Routes**: All report routes covered
- **Data validation**: 4 validation tests
- **Error handling**: 6 error scenarios
- **Performance**: 4 performance tests

### Frontend Coverage
- **Components**: 6 report components fully tested
- **Pages**: Reports page with tab navigation
- **Interactions**: Filtering, sorting, period selection
- **Data states**: Loading, error, success states
- **Accessibility**: Basic a11y checks

## ✅ Test Checklist

### API Tests (15 tests)
- [x] Dashboard endpoint
- [x] Trades history with filters
- [x] Context performance matrix
- [x] Strategy list
- [x] Strategy details
- [x] Equity curve
- [x] Drawdown history
- [x] Overall performance
- [x] Data validation (P&L, win rate, profit factor)
- [x] Market context values

### Integration Tests (21 tests)
- [x] Dashboard workflow
- [x] Trade analysis workflow
- [x] Strategy analysis workflow
- [x] Performance charting workflow
- [x] Multi-period comparison
- [x] Export preparation
- [x] Data consistency
- [x] Error handling
- [x] Authentication
- [x] Performance

### Component Tests (29 tests)
- [x] TradeHistoryTable (6 tests)
- [x] StrategyPerformanceChart (3 tests)
- [x] DashboardKPIs (5 tests)
- [x] PerformanceCharts (4 tests)
- [x] MarketContextAnalysis (1 test)
- [x] ExportReports (7 tests)
- [x] Component integration (3 tests)

### Page Tests (20 tests)
- [x] Reports page rendering
- [x] Tab navigation
- [x] Period selector
- [x] Active state management
- [x] Accessibility

## 🎯 Total Tests: 85 tests across all suites

## 📝 Test Configuration

### pytest.ini
- Test discovery patterns
- Markers for categorization (unit, integration, performance, api, slow)
- Coverage settings
- Output formatting

### frontend/package.json
- Jest configuration
- Test scripts
- Coverage thresholds
- Test environment setup

### frontend/jest.setup.js
- localStorage mock
- window.matchMedia mock
- Console error suppression

## 🔍 Key Testing Scenarios

### 1. Data Validation
- Trade P&L consistency
- Win rate validity (0-100%)
- Profit factor positivity
- Market context values
- Trade counts consistency

### 2. Filtering & Sorting
- Filter by strategy
- Filter by symbol
- Filter by status
- Filter by market context
- Filter by P&L range
- Sortable columns

### 3. Performance
- Equity curve loading < 2s
- Trades list loading < 2s
- Strategies loading < 1s
- Concurrent request handling
- Large dataset (365 days) handling

### 4. Error Handling
- Invalid time periods
- Negative periods
- Excessive periods
- Nonexistent strategies
- API failures
- Missing data

### 5. Export Functionality
- CSV export
- PDF export
- Different export types
- Success/error messages

## 🛠️ CI/CD Integration

### Add to GitHub Actions (.github/workflows/tests.yml):
```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - run: pytest tests/ --cov

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: '18'
      - run: cd frontend && npm install
      - run: cd frontend && npm test -- --coverage
```

## 📚 Related Documentation

- [Reports Implementation](../IMPLEMENTATION_SUMMARY.txt)
- [Project Architecture](../docs/architecture/)
- [API Documentation](../docs/PROJECT_SPECIFICATIONS.md)

## 🐛 Debugging Tests

### Verbose output:
```bash
pytest tests/ -v -s
```

### Stop on first failure:
```bash
pytest tests/ -x
```

### Show print statements:
```bash
pytest tests/ -s
```

### Debug a specific test:
```bash
pytest tests/api/test_reports_endpoints.py::TestReportsEndpoints::test_get_trades_history -vvs
```

## 📞 Contact & Support

For test-related issues or improvements, refer to the main project documentation.
