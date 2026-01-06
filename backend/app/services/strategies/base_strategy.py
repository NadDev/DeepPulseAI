"""
Base Strategy Pattern for Trading Bots
Provides an extensible architecture for implementing trading strategies
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class BaseStrategy(ABC):
    """
    Abstract base class for all trading strategies.
    Each strategy must implement the required methods.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize strategy with configuration
        
        Args:
            config: Strategy-specific configuration parameters
        """
        # Start with default config from schema
        self.config = self._get_default_config()
        # Override with provided config
        if config:
            self.config.update(config)
        self.name = self.__class__.__name__
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Extract default values from config schema"""
        defaults = {}
        schema = self.get_config_schema()
        for key, spec in schema.items():
            if 'default' in spec:
                defaults[key] = spec['default']
        return defaults
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Override in subclass to define configuration schema"""
        return {}
    
    @abstractmethod
    def validate_signal(self, market_data: Dict[str, Any]) -> bool:
        """
        Check if current market conditions generate a valid entry signal
        
        Args:
            market_data: Dictionary containing price, indicators, volume, etc.
                Expected keys: 'close', 'high', 'low', 'volume', 'indicators'
        
        Returns:
            bool: True if entry signal is valid
        """
        pass
    
    @abstractmethod
    def get_signal_direction(self, market_data: Dict[str, Any]) -> str:
        """
        Determine the direction of the trading signal
        
        Args:
            market_data: Market data dictionary
        
        Returns:
            str: 'BUY', 'SELL', or 'NONE'
        """
        pass
    
    @abstractmethod
    def calculate_position_size(
        self, 
        risk_amount: float, 
        entry_price: float, 
        stop_loss: float
    ) -> float:
        """
        Calculate position size based on risk management rules
        
        Args:
            risk_amount: Maximum amount to risk on this trade
            entry_price: Planned entry price
            stop_loss: Stop loss price
        
        Returns:
            float: Position size (quantity)
        """
        pass
    
    @abstractmethod
    def get_stop_loss(self, entry_price: float, direction: str, market_data: Dict[str, Any]) -> float:
        """
        Calculate stop loss price for a trade
        
        Args:
            entry_price: Entry price of the position
            direction: 'BUY' or 'SELL'
            market_data: Current market data
        
        Returns:
            float: Stop loss price
        """
        pass
    
    @abstractmethod
    def get_take_profit(self, entry_price: float, direction: str, market_data: Dict[str, Any]) -> Optional[float]:
        """
        Calculate take profit price for a trade (optional)
        
        Args:
            entry_price: Entry price of the position
            direction: 'BUY' or 'SELL'
            market_data: Current market data
        
        Returns:
            Optional[float]: Take profit price or None
        """
        pass
    
    @abstractmethod
    def should_exit(
        self, 
        open_trade: Dict[str, Any], 
        current_price: float,
        market_data: Dict[str, Any]
    ) -> bool:
        """
        Check if an open position should be closed
        
        Args:
            open_trade: Dictionary with trade info (entry_price, direction, quantity, etc.)
            current_price: Current market price
            market_data: Current market data
        
        Returns:
            bool: True if position should be closed
        """
        pass
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Return the configuration schema for this strategy.
        Used by the UI to generate configuration forms.
        
        Returns:
            Dict with parameter definitions:
            {
                'param_name': {
                    'type': 'int|float|str|bool',
                    'default': default_value,
                    'min': min_value (optional),
                    'max': max_value (optional),
                    'description': 'Parameter description'
                }
            }
        """
        return {}
    
    def get_description(self) -> str:
        """
        Return a human-readable description of the strategy
        
        Returns:
            str: Strategy description
        """
        return f"{self.name} trading strategy"
    
    def validate_config(self) -> bool:
        """
        Validate that the current configuration is valid
        
        Returns:
            bool: True if configuration is valid
        """
        schema = self.get_config_schema()
        for param, rules in schema.items():
            if param not in self.config:
                # Use default value if not provided
                if 'default' in rules:
                    self.config[param] = rules['default']
                else:
                    return False
            
            # Validate type
            value = self.config[param]
            expected_type = rules.get('type')
            
            if expected_type == 'int' and not isinstance(value, int):
                return False
            elif expected_type == 'float' and not isinstance(value, (int, float)):
                return False
            elif expected_type == 'str' and not isinstance(value, str):
                return False
            elif expected_type == 'bool' and not isinstance(value, bool):
                return False
            
            # Validate range
            if 'min' in rules and value < rules['min']:
                return False
            if 'max' in rules and value > rules['max']:
                return False
        
        return True


class StrategyRegistry:
    """
    Central registry for managing all available trading strategies.
    Supports dynamic registration and retrieval of strategies.
    """
    
    _strategies: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, strategy_class: type):
        """
        Register a new strategy in the registry
        
        Args:
            name: Unique identifier for the strategy
            strategy_class: Class that inherits from BaseStrategy
        
        Raises:
            ValueError: If strategy_class doesn't inherit from BaseStrategy
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"Strategy class must inherit from BaseStrategy")
        
        cls._strategies[name] = strategy_class
        print(f"✅ Strategy registered: {name}")
    
    @classmethod
    def get_strategy(cls, name: str, config: Dict[str, Any] = None) -> BaseStrategy:
        """
        Retrieve and instantiate a strategy by name
        
        Args:
            name: Strategy identifier
            config: Configuration parameters for the strategy
        
        Returns:
            BaseStrategy: Instance of the requested strategy
        
        Raises:
            ValueError: If strategy is not found
        """
        if name not in cls._strategies:
            available = ', '.join(cls._strategies.keys())
            raise ValueError(
                f"Strategy '{name}' not found. "
                f"Available strategies: {available}"
            )
        
        strategy_class = cls._strategies[name]
        return strategy_class(config=config)
    
    @classmethod
    def list_strategies(cls) -> List[Dict[str, Any]]:
        """
        List all available strategies with their metadata
        
        Returns:
            List of dictionaries with strategy information
        """
        strategies = []
        for name, strategy_class in cls._strategies.items():
            # Instantiate to get schema and description
            instance = strategy_class()
            strategies.append({
                'name': name,
                'class_name': strategy_class.__name__,
                'description': instance.get_description(),
                'config_schema': instance.get_config_schema()
            })
        
        return strategies
    
    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a strategy is registered
        
        Args:
            name: Strategy identifier
        
        Returns:
            bool: True if strategy is registered
        """
        return name in cls._strategies
    
    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        Remove a strategy from the registry
        
        Args:
            name: Strategy identifier
        
        Returns:
            bool: True if strategy was removed
        """
        if name in cls._strategies:
            del cls._strategies[name]
            return True
        return False
