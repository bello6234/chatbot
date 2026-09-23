"""
Simple Trading Bot for Cryptocurrency
Uses SMA Crossover and RSI strategies for paper trading
"""

import pandas as pd
import numpy as np
import time
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass
class Trade:
    """Represents a single trade"""
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    quantity: float = 0.0
    order_type: Optional[OrderType] = None
    status: PositionStatus = PositionStatus.OPEN
    profit: float = 0.0
    
    def close_trade(self, exit_time: datetime, exit_price: float) -> float:
        """Close the trade and calculate profit"""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.status = PositionStatus.CLOSED
        
        if self.order_type == OrderType.BUY:
            # Long position: profit = (exit_price - entry_price) * quantity
            self.profit = (exit_price - self.entry_price) * self.quantity
        elif self.order_type == OrderType.SELL:
            # Short position: profit = (entry_price - exit_price) * quantity
            self.profit = (self.entry_price - exit_price) * self.quantity
        
        return self.profit


@dataclass 
class TradingBot:
    """Main trading bot class"""
    initial_balance: float = 5.0
    current_balance: float = 5.0
    trades: list = field(default_factory=list)
    positions: list = field(default_factory=list)
    trade_history: list = field(default_factory=list)
    
    def __post_init__(self):
        self.current_balance = self.initial_balance
        self.start_time = datetime.now()
        
    @property
    def total_value(self) -> float:
        """Calculate total portfolio value"""
        open_positions_value = sum(
            pos.quantity * pos.entry_price for pos in self.positions 
            if pos.status == PositionStatus.OPEN
        )
        return self.current_balance + open_positions_value
    
    @property 
    def open_positions_count(self) -> int:
        """Number of currently open positions"""
        return len([p for p in self.positions if p.status == PositionStatus.OPEN])
    
    @property
    def total_profit(self) -> float:
        """Calculate total profit from closed trades"""
        return sum(trade.profit for trade in self.trade_history if trade.status == PositionStatus.CLOSED)
    
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage"""
        closed_trades = [t for t in self.trade_history if t.status == PositionStatus.CLOSED]
        if not closed_trades:
            return 0.0
        winning_trades = len([t for t in closed_trades if t.profit > 0])
        return (winning_trades / len(closed_trades)) * 100
    
    def calculate_sma(self, data: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return data['close'].rolling(window=period).mean()
    
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def check_buy_signal(self, data: pd.DataFrame, short_sma: int = 10, long_sma: int = 30) -> bool:
        """Check if buy signal is triggered"""
        sma_short = self.calculate_sma(data, short_sma)
        sma_long = self.calculate_sma(data, long_sma)
        rsi = self.calculate_rsi(data)
        
        # Get latest values
        latest_sma_short = sma_short.iloc[-1]
        latest_sma_long = sma_long.iloc[-1]
        prev_sma_short = sma_short.iloc[-2] if len(sma_short) > 1 else latest_sma_short
        prev_sma_long = sma_long.iloc[-2] if len(sma_long) > 1 else latest_sma_long
        latest_rsi = rsi.iloc[-1]
        
        # SMA Crossover: Short SMA crosses above Long SMA
        sma_crossover = prev_sma_short <= prev_sma_long and latest_sma_short > latest_sma_long
        
        # RSI condition: Not overbought
        rsi_condition = latest_rsi < 70
        
        return sma_crossover and rsi_condition
    
    def check_sell_signal(self, data: pd.DataFrame, short_sma: int = 10, long_sma: int = 30) -> bool:
        """Check if sell signal is triggered"""
        sma_short = self.calculate_sma(data, short_sma)
        sma_long = self.calculate_sma(data, long_sma)
        rsi = self.calculate_rsi(data)
        
        # Get latest values
        latest_sma_short = sma_short.iloc[-1]
        latest_sma_long = sma_long.iloc[-1]
        prev_sma_short = sma_short.iloc[-2] if len(sma_short) > 1 else latest_sma_short
        prev_sma_long = sma_long.iloc[-2] if len(sma_long) > 1 else latest_sma_long
        latest_rsi = rsi.iloc[-1]
        
        # SMA Crossover: Short SMA crosses below Long SMA
        sma_crossover = prev_sma_short >= prev_sma_long and latest_sma_short < latest_sma_long
        
        # RSI condition: Not oversold
        rsi_condition = latest_rsi > 30
        
        return sma_crossover and rsi_condition
    
    def open_position(self, price: float, quantity: float, order_type: OrderType) -> Trade:
        """Open a new trading position"""
        trade = Trade(
            entry_time=datetime.now(),
            entry_price=price,
            quantity=quantity,
            order_type=order_type
        )
        self.positions.append(trade)
        logger.info(f"Opened {order_type.value} position at ${price:.2f} with quantity {quantity}")
        return trade
    
    def close_position(self, trade: Trade, price: float) -> float:
        """Close an existing position"""
        profit = trade.close_trade(datetime.now(), price)
        self.current_balance += profit
        self.trade_history.append(trade)
        self.positions.remove(trade)
        logger.info(f"Closed {trade.order_type.value} position. Profit: ${profit:.4f}")
        return profit
    
    def close_all_positions(self, price: float) -> float:
        """Close all open positions at current price"""
        total_profit = 0.0
        for trade in self.positions[:]:  # Iterate over a copy
            if trade.status == PositionStatus.OPEN:
                total_profit += self.close_position(trade, price)
        return total_profit
    
    def execute_trade(self, data: pd.DataFrame, price: float, quantity: float) -> str:
        """Execute trading logic based on signals"""
        current_price = price
        
        # Check if we should close existing positions
        for trade in self.positions[:]:
            if trade.status == PositionStatus.OPEN:
                if trade.order_type == OrderType.BUY:
                    # Check if we should sell
                    if self.check_sell_signal(data):
                        self.close_position(trade, current_price)
                        return "SELL"
                elif trade.order_type == OrderType.SELL:
                    # Check if we should buy back
                    if self.check_buy_signal(data):
                        self.close_position(trade, current_price)
                        return "BUY"
        
        # Check if we should open new position
        if self.open_positions_count == 0:
            if self.check_buy_signal(data):
                self.open_position(current_price, quantity, OrderType.BUY)
                return "BUY"
            elif self.check_sell_signal(data):
                self.open_position(current_price, quantity, OrderType.SELL)
                return "SELL"
        
        return "HOLD"
    
    def generate_sample_data(self, days: int = 30) -> pd.DataFrame:
        """Generate sample price data for testing"""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=days * 24, freq='h')
        
        # Create synthetic price data with trends
        base_prices = np.cumsum(np.random.randn(len(dates)) * 0.5) + 50000
        prices = base_prices + np.random.randn(len(dates)) * 200
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices - np.abs(np.random.randn(len(dates)) * 50),
            'high': prices + np.abs(np.random.randn(len(dates)) * 100),
            'low': prices - np.abs(np.random.randn(len(dates)) * 100),
            'close': prices,
            'volume': np.random.randint(100, 1000, len(dates))
        })
        
        # Add some trends for testing
        data.loc[100:150, 'close'] = data.loc[100:150, 'close'] + np.linspace(0, 2000, len(data.loc[100:150]))
        data.loc[200:250, 'close'] = data.loc[200:250, 'close'] - np.linspace(0, 1500, len(data.loc[200:250]))
        
        return data
    
    def run_backtest(self, data: pd.DataFrame, quantity: float = 0.0001) -> dict:
        """Run a backtest on historical data"""
        results = {
            'trades': [],
            'balance_history': [],
            'positions_history': []
        }
        
        initial_balance = self.current_balance
        
        for i in range(len(data)):
            candle = data.iloc[i]
            current_price = candle['close']
            
            # Execute trade logic
            action = self.execute_trade(data.iloc[:i+1], current_price, quantity)
            
            # Record state
            results['balance_history'].append({
                'time': candle['timestamp'],
                'balance': self.current_balance,
                'total_value': self.total_value,
                'action': action
            })
            results['positions_history'].append(self.open_positions_count)
        
        # Close all positions at the end
        self.close_all_positions(current_price)
        
        # Calculate final metrics
        final_balance = self.current_balance
        total_profit = final_balance - initial_balance
        
        results['summary'] = {
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'total_profit': total_profit,
            'return_pct': (total_profit / initial_balance) * 100,
            'total_trades': len(self.trade_history),
            'winning_trades': len([t for t in self.trade_history if t.profit > 0]),
            'losing_trades': len([t for t in self.trade_history if t.profit < 0]),
            'win_rate': self.win_rate
        }
        
        return results


# Example usage
if __name__ == "__main__":
    # Create bot with $5 initial balance
    bot = TradingBot(initial_balance=5.0)
    
    # Generate sample data
    sample_data = bot.generate_sample_data(days=10)
    
    # Run backtest
    results = bot.run_backtest(sample_data, quantity=0.0001)
    
    # Print summary
    print("\n" + "="*50)
    print("TRADING BOT BACKTEST RESULTS")
    print("="*50)
    print(f"Initial Balance: ${results['summary']['initial_balance']:.2f}")
    print(f"Final Balance: ${results['summary']['final_balance']:.2f}")
    print(f"Total Profit: ${results['summary']['total_profit']:.2f}")
    print(f"Return: {results['summary']['return_pct']:.2f}%")
    print(f"Total Trades: {results['summary']['total_trades']}")
    print(f"Winning Trades: {results['summary']['winning_trades']}")
    print(f"Losing Trades: {results['summary']['losing_trades']}")
    print(f"Win Rate: {results['summary']['win_rate']:.1f}%")
    print("="*50)
