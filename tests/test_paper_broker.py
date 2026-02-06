"""
Tests for PaperBroker - Paper trading simulation with virtual portfolio

TEST COVERAGE:
1. Order placement (BUY/SELL, MARKET/LIMIT)
2. Balance tracking (initial, after trades, insufficient funds)
3. Commission application (0.1% default)
4. Slippage simulation (BUY +0.05%, SELL -0.05%)
5. Order rejection (insufficient balance)
6. Multi-asset portfolio tracking
"""

import pytest
import pytest_asyncio
from typing import List

from app.brokers import PaperBroker, OrderSide, OrderType, OrderStatus
from app.brokers.data_sources import DataSource


# ============================================================================
# MOCK DATA SOURCE
# ============================================================================

class MockDataSource(DataSource):
    """Mock data source that returns predictable prices for testing"""
    
    def __init__(self):
        self.prices = {"BTCUSDT": 50000.0, "ETHUSDT": 3000.0}
    
    async def get_latest_price(self, symbol: str) -> float:
        """Return fixed price for symbol"""
        if symbol in self.prices:
            return self.prices[symbol]
        raise ValueError(f"Symbol {symbol} not found in MockDataSource")
    
    async def get_ticker(self, symbol: str) -> dict:
        """Return ticker dict with 'close' key"""
        price = await self.get_latest_price(symbol)
        return {"close": price}
    
    async def get_candles(self, symbol: str, interval: str, limit: int) -> List:
        """Not used in PaperBroker order execution"""
        return []


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture
async def mock_data_source():
    """Fixture that provides a MockDataSource instance"""
    return MockDataSource()


@pytest_asyncio.fixture
async def paper_broker(mock_data_source):
    """Fixture that provides a PaperBroker with mock data source"""
    return PaperBroker(
        data_source=mock_data_source,
        initial_balance=10000.0,
        slippage_pct=0.05,  # 0.05%
        commission_pct=0.1   # 0.1%
    )


# ============================================================================
# TEST 1: Basic BUY order with sufficient balance
# ============================================================================

@pytest.mark.asyncio
async def test_place_buy_order_success(paper_broker):
    """Test successful BUY order placement"""
    # Place BUY order
    result = await paper_broker.place_order(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1
    )
    
    # Validate OrderResult
    assert result is not None
    assert result.order_id is not None
    assert result.status == OrderStatus.FILLED
    assert result.commission > 0
    assert result.commission_asset == "USDT"
    
    # Check balances (using private _balance attribute)
    assert paper_broker._balance["USDT"] < 10000  # USDT decreased
    assert paper_broker._balance["BTC"] == 0.1    # BTC acquired


# ============================================================================
# TEST 2: SELL order (must have asset first)
# ============================================================================

@pytest.mark.asyncio
async def test_place_sell_order_success(paper_broker):
    """Test successful SELL order after buying"""
    # First BUY to have BTC
    await paper_broker.place_order(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1
    )
    
    usdt_after_buy = paper_broker._balance["USDT"]
    
    # Then SELL half
    result = await paper_broker.place_order(
        symbol="BTCUSDT",
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=0.05
    )
    
    # Validate SELL result
    assert result.status == OrderStatus.FILLED
    assert result.commission > 0
    
    # Check balances
    assert paper_broker._balance["USDT"] > usdt_after_buy  # USDT increased
    assert paper_broker._balance["BTC"] == 0.05  # BTC decreased to 0.05


# ============================================================================
# TEST 3: Insufficient balance rejection
# ============================================================================

@pytest.mark.asyncio
async def test_place_order_insufficient_balance(paper_broker):
    """Test order rejection when insufficient balance"""
    initial_balance = paper_broker._balance["USDT"]
    
    # Try to buy 1 BTC @ 50000 = 50000 USDT (> 10000 balance)
    with pytest.raises(Exception):
        await paper_broker.place_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0
        )
    
    # Balance should be unchanged
    assert paper_broker._balance["USDT"] == initial_balance


# ============================================================================
# TEST 4: Commission calculation
# ============================================================================

@pytest.mark.asyncio
async def test_commission_applied_correctly(paper_broker):
    """Test commission is calculated and applied correctly"""
    # Buy 0.1 BTC @ 50000 = 5000 USDT base
    result = await paper_broker.place_order(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1
    )
    
    # Commission should be ~5 USDT (0.1% of 5000, plus slippage)
    assert result.commission > 4.5
    assert result.commission < 5.5
    assert result.commission_asset == "USDT"


# ============================================================================
# TEST 5: Slippage simulation
# ============================================================================

@pytest.mark.asyncio
async def test_slippage_applied_on_market_orders(mock_data_source):
    """Test slippage is applied correctly for MARKET orders"""
    # Create broker with higher slippage for easier testing
    broker = PaperBroker(
        data_source=mock_data_source,
        initial_balance=100000.0,
        slippage_pct=0.1,  # 0.1% slippage
        commission_pct=0.0  # No commission for this test
    )
    
    # BUY order - price should increase
    buy_result = await broker.place_order(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=0.1
    )
    
    # Market price: 50000
    # With 0.1% slippage on BUY: 50000 * 1.001 = 50050
    # Expected cost: 0.1 * 50050 = 5005
    assert buy_result.fill_price > 50000  # Slippage applied
    
    # SELL order - price should decrease
    sell_result = await broker.place_order(
        symbol="BTCUSDT",
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=0.05
    )
    
    # With 0.1% slippage on SELL: 50000 * 0.999 = 49950
    assert sell_result.fill_price < 50000  # Slippage applied


# ============================================================================
# TEST 6: Multi-asset portfolio tracking
# ============================================================================

@pytest.mark.asyncio
async def test_multi_asset_portfolio(mock_data_source):
    """Test broker tracks multiple assets correctly"""
    broker = PaperBroker(
        data_source=mock_data_source,
        initial_balance=20000.0
    )
    
    # Buy BTC
    await broker.place_order("BTCUSDT", OrderSide.BUY, OrderType.MARKET, 0.1)
    assert "BTC" in broker._balance
    assert broker._balance["BTC"] == 0.1
    
    # Buy ETH
    await broker.place_order("ETHUSDT", OrderSide.BUY, OrderType.MARKET, 1.0)
    assert "ETH" in broker._balance
    assert broker._balance["ETH"] == 1.0
    
    # Sell some BTC
    await broker.place_order("BTCUSDT", OrderSide.SELL, OrderType.MARKET, 0.05)
    assert broker._balance["BTC"] == 0.05
    
    # Validate multi-asset state
    assert "USDT" in broker._balance
    assert "BTC" in broker._balance
    assert "ETH" in broker._balance


# ============================================================================
# TEST 7: LIMIT order (price specified)
# ============================================================================

@pytest.mark.asyncio
async def test_limit_order_execution(paper_broker):
    """Test LIMIT order uses specified price"""
    # Place LIMIT BUY @ 49000 (better than market 50000)
    result = await paper_broker.place_order(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=0.1,
        price=49000.0
    )
    
    # LIMIT order should execute at specified price (+ slippage)
    assert result.status == OrderStatus.FILLED
    assert result.fill_price < 50000  # Better price used
    
    # Cost should be based on limit price
    # 0.1 BTC @ 49000 = 4900 base (+ slippage + commission)
    usdt_spent = 10000 - paper_broker._balance["USDT"]
    assert usdt_spent < 5000  # Less than market price cost


# ============================================================================
# TEST 8: Get account balance
# ============================================================================

@pytest.mark.asyncio
async def test_get_account_balance(paper_broker, mock_data_source):
    """Test get_account_balance() returns correct AccountBalance"""
    # Initial state
    initial_balance = await paper_broker.get_account_balance()
    assert initial_balance.total_value_usdt == 10000.0
    assert initial_balance.free_usdt == 10000.0
    
    # After buying BTC
    await paper_broker.place_order("BTCUSDT", OrderSide.BUY, OrderType.MARKET, 0.1)
    
    balance_after = await paper_broker.get_account_balance()
    
    # Total value should be approximately 10000 (minus small fees)
    # USDT spent ~5000 + 0.1 BTC worth ~5000 = ~10000
    assert balance_after.total_value_usdt > 9900  # Allow for fees
    assert balance_after.total_value_usdt < 10100
    
    # Should have multiple assets
    assert len(balance_after.assets) >= 2  # USDT + BTC


# ============================================================================
# BONUS TEST: Order history tracking
# ============================================================================

@pytest.mark.asyncio
async def test_order_history_stored(paper_broker):
    """Test broker stores order history"""
    # Initial: no orders
    assert len(paper_broker._orders) == 0
    
    # Place 3 orders
    await paper_broker.place_order("BTCUSDT", OrderSide.BUY, OrderType.MARKET, 0.1)
    await paper_broker.place_order("BTCUSDT", OrderSide.BUY, OrderType.MARKET, 0.05)
    await paper_broker.place_order("BTCUSDT", OrderSide.SELL, OrderType.MARKET, 0.05)
    
    # Should have 3 orders in history
    assert len(paper_broker._orders) == 3
    
    # All should be FILLED
    for order in paper_broker._orders:
        assert order.status == OrderStatus.FILLED
