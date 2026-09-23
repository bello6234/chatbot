"""
Trading Bot with Binance Integration - Termux Compatible
Supports both paper trading and live trading on Binance
"""

import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json
import time
import random

# Import binance client
try:
    from binance_client import BinanceClient
except ImportError:
    BinanceClient = None


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class PositionStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class TradeMode(Enum):
    PAPER = "PAPER"
    TESTNET = "TESTNET"
    LIVE = "LIVE"


class StrategyType(Enum):
    SMA_CROSSOVER = "SMA Crossover + RSI"
    MEAN_REVERSION = "Mean Reversion"
    BREAKOUT = "Breakout Strategy"
    TREND_FOLLOWING = "Trend Following"


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
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: str = ""
    order_id: Optional[int] = None
    symbol: str = "BTCUSDT"
    
    def close_trade(self, exit_time: datetime, exit_price: float) -> float:
        """Close the trade and calculate profit"""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.status = PositionStatus.CLOSED
        
        if self.order_type == OrderType.BUY:
            self.profit = (exit_price - self.entry_price) * self.quantity
        elif self.order_type == OrderType.SELL:
            self.profit = (self.entry_price - exit_price) * self.quantity
        
        return self.profit
    
    def check_stop_loss(self, current_price: float) -> bool:
        """Check if stop loss is hit"""
        if self.stop_loss is None:
            return False
        if self.order_type == OrderType.BUY:
            return current_price <= self.stop_loss
        elif self.order_type == OrderType.SELL:
            return current_price >= self.stop_loss
        return False
    
    def check_take_profit(self, current_price: float) -> bool:
        """Check if take profit is hit"""
        if self.take_profit is None:
            return False
        if self.order_type == OrderType.BUY:
            return current_price >= self.take_profit
        elif self.order_type == OrderType.SELL:
            return current_price <= self.take_profit
        return False


class TradingBotBinance:
    """Trading bot with Binance integration"""
    
    def __init__(
        self,
        initial_balance: float = 5.0,
        symbol: str = "BTCUSDT",
        mode: TradeMode = TradeMode.PAPER,
        api_key: str = "",
        api_secret: str = ""
    ):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.symbol = symbol
        self.mode = mode
        self.positions: List[Trade] = []
        self.trade_history: List[Trade] = []
        self.start_time = datetime.now()
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Initialize Binance client
        self.binance = None
        if BinanceClient:
            self.binance = BinanceClient(api_key, api_secret, mode == TradeMode.TESTNET)
        
        # Strategy parameters
        self.short_sma_period = 5
        self.long_sma_period = 20
        self.rsi_period = 14
        self.rsi_overbought = 65
        self.rsi_oversold = 35
        
        # Risk management
        self.risk_per_trade = 0.02  # 2% of balance per trade
        self.stop_loss_pct = 0.01  # 1% stop loss
        self.take_profit_pct = 0.03  # 3% take profit
        
        # Strategy selection
        self.strategy = StrategyType.SMA_CROSSOVER
        
        # Performance tracking
        self.max_drawdown = 0.0
        self.peak_balance = initial_balance
        
        # State
        self.last_candle_time = None
        self.running = False
    
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
    
    @property
    def profit_factor(self) -> float:
        """Calculate profit factor (gross wins / gross losses)"""
        winning_trades = [t for t in self.trade_history if t.status == PositionStatus.CLOSED and t.profit > 0]
        losing_trades = [t for t in self.trade_history if t.status == PositionStatus.CLOSED and t.profit < 0]
        
        gross_wins = sum(t.profit for t in winning_trades)
        gross_losses = abs(sum(t.profit for t in losing_trades))
        
        if gross_losses == 0:
            return float('inf') if gross_wins > 0 else 0.0
        return gross_wins / gross_losses
    
    def calculate_position_size(self, entry_price: float, stop_loss: float, order_type: OrderType) -> float:
        """Calculate position size based on risk management"""
        risk_amount = self.current_balance * self.risk_per_trade
        
        if order_type == OrderType.BUY:
            risk_per_unit = entry_price - stop_loss
        else:  # SELL
            risk_per_unit = stop_loss - entry_price
        
        if risk_per_unit <= 0:
            return 0.0
        
        quantity = risk_amount / risk_per_unit
        
        # Apply minimum notional constraint for Binance
        if self.binance and self.mode != TradeMode.PAPER:
            min_notional = self.binance.get_min_notional(self.symbol)
            min_quantity = min_notional / entry_price
            if quantity < min_quantity:
                return 0.0
        
        return quantity
    
    def calculate_sma(self, prices: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return [sum(prices[:i+1]) / (i+1) for i in range(len(prices))]
        
        sma = []
        for i in range(len(prices)):
            start = max(0, i - period + 1)
            window = prices[start:i+1]
            sma.append(sum(window) / len(window))
        return sma
    
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return self.calculate_sma(prices, min(period, len(prices)))
        
        multiplier = 2 / (period + 1)
        ema = [sum(prices[:period]) / period]
        
        for i in range(period, len(prices)):
            ema_value = (prices[i] - ema[-1]) * multiplier + ema[-1]
            ema.append(ema_value)
        
        return ema
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index - Wilder's method"""
        if len(prices) < 2:
            return [50.0] * len(prices)
        
        rsi = [50.0]
        
        prev_avg_gain = 0.0
        prev_avg_loss = 0.0
        
        for i in range(1, len(prices)):
            delta = prices[i] - prices[i-1]
            
            if i == 1:
                if delta > 0:
                    prev_avg_gain = delta
                    prev_avg_loss = 0.0
                else:
                    prev_avg_gain = 0.0
                    prev_avg_loss = abs(delta)
                rsi.append(50.0)
                continue
            
            if delta > 0:
                gain = delta
                loss = 0.0
            else:
                gain = 0.0
                loss = abs(delta)
            
            if i <= period:
                gains = [prices[j] - prices[j-1] for j in range(1, i) if prices[j] > prices[j-1]]
                losses = [abs(prices[j] - prices[j-1]) for j in range(1, i) if prices[j] < prices[j-1]]
                
                avg_gain = sum(gains) / len(gains) if gains else 0.0
                avg_loss = sum(losses) / len(losses) if losses else 0.0001
            else:
                avg_gain = (prev_avg_gain * (period - 1) + gain) / period
                avg_loss = (prev_avg_loss * (period - 1) + loss) / period
            
            prev_avg_gain = avg_gain
            prev_avg_loss = avg_loss
            
            if avg_loss == 0:
                rs = 100
            else:
                rs = avg_gain / avg_loss
            
            rsi_value = 100 - (100 / (1 + rs))
            rsi.append(rsi_value)
        
        while len(rsi) < len(prices):
            rsi.append(rsi[-1] if rsi else 50.0)
        
        return rsi
    
    def check_buy_signal(self, prices: List[float]) -> Tuple[bool, str]:
        """Check if buy signal is triggered"""
        if self.strategy == StrategyType.SMA_CROSSOVER:
            return self._check_sma_buy_signal(prices)
        elif self.strategy == StrategyType.MEAN_REVERSION:
            return self._check_mean_reversion_buy_signal(prices)
        elif self.strategy == StrategyType.BREAKOUT:
            return self._check_breakout_buy_signal(prices)
        elif self.strategy == StrategyType.TREND_FOLLOWING:
            return self._check_trend_following_buy_signal(prices)
        return False, ""
    
    def _check_sma_buy_signal(self, prices: List[float]) -> Tuple[bool, str]:
        """SMA Crossover strategy buy signal"""
        if len(prices) < max(self.long_sma_period, self.rsi_period) + 1:
            return False, "Not enough data"
        
        sma_short = self.calculate_sma(prices, self.short_sma_period)
        sma_long = self.calculate_sma(prices, self.long_sma_period)
        rsi = self.calculate_rsi(prices, self.rsi_period)
        
        latest_sma_short = sma_short[-1]
        latest_sma_long = sma_long[-1]
        prev_sma_short = sma_short[-2]
        prev_sma_long = sma_long[-2]
        latest_rsi = rsi[-1]
        
        sma_crossover = prev_sma_short <= prev_sma_long and latest_sma_short > latest_sma_long
        rsi_condition = latest_rsi < self.rsi_overbought
        price_above = prices[-1] > latest_sma_long
        
        if sma_crossover and rsi_condition and price_above:
            return True, f"SMA Crossover + RSI ({latest_rsi:.1f})"
        return False, ""
    
    def _check_mean_reversion_buy_signal(self, prices: List[float]) -> Tuple[bool, str]:
        """Mean Reversion strategy buy signal"""
        if len(prices) < 20:
            return False, "Not enough data"
        
        sma = self.calculate_sma(prices, 20)
        rsi = self.calculate_rsi(prices, 14)
        
        latest_price = prices[-1]
        latest_sma = sma[-1]
        latest_rsi = rsi[-1]
        
        price_below = latest_price < latest_sma
        rsi_oversold = latest_rsi < self.rsi_oversold
        deviation_pct = ((latest_sma - latest_price) / latest_sma) * 100
        
        if price_below and rsi_oversold and deviation_pct > 1:
            return True, f"Mean Reversion ({deviation_pct:.1f}% below, RSI: {latest_rsi:.1f})"
        return False, ""
    
    def _check_breakout_buy_signal(self, prices: List[float]) -> Tuple[bool, str]:
        """Breakout strategy buy signal"""
        if len(prices) < 20:
            return False, "Not enough data"
        
        highs = [max(prices[max(0, i-20):i+1]) for i in range(len(prices))]
        latest_high = highs[-1]
        prev_high = highs[-2] if len(highs) > 1 else latest_high
        
        breakout = prices[-1] > latest_high and prices[-2] <= prev_high
        
        if breakout:
            return True, f"Breakout above ${latest_high:.2f}"
        return False, ""
    
    def _check_trend_following_buy_signal(self, prices: List[float]) -> Tuple[bool, str]:
        """Trend Following strategy buy signal"""
        if len(prices) < max(5, 20) + 1:
            return False, "Not enough data"
        
        ema_short = self.calculate_ema(prices, 5)
        ema_long = self.calculate_ema(prices, 20)
        
        latest_ema_short = ema_short[-1]
        latest_ema_long = ema_long[-1]
        prev_ema_short = ema_short[-2]
        prev_ema_long = ema_long[-2]
        
        crossover = prev_ema_short <= prev_ema_long and latest_ema_short > latest_ema_long
        price_above = prices[-1] > latest_ema_long
        
        if crossover and price_above:
            return True, f"EMA Crossover (5/20)"
        return False, ""
    
    def check_sell_signal(self, prices: List[float]) -> Tuple[bool, str]:
        """Check if sell signal is triggered"""
        if self.strategy == StrategyType.SMA_CROSSOVER:
            return self._check_sma_sell_signal(prices)
        elif self.strategy == StrategyType.MEAN_REVERSION:
            return self._check_mean_reversion_sell_signal(prices)
        elif self.strategy == StrategyType.BREAKOUT:
            return self._check_breakout_sell_signal(prices)
        elif self.strategy == StrategyType.TREND_FOLLOWING:
            return self._check_trend_following_sell_signal(prices)
        return False, ""
    
    def _check_sma_sell_signal(self, prices: List[float]) -> Tuple[bool, str]:
        """SMA Crossover strategy sell signal"""
        if len(prices) < max(self.long_sma_period, self.rsi_period) + 1:
            return False, ""
        
        sma_short = self.calculate_sma(prices, self.short_sma_period)
        sma_long = self.calculate_sma(prices, self.long_sma_period)
        rsi = self.calculate_rsi(prices, self.rsi_period)
        
        latest_sma_short = sma_short[-1]
        latest_sma_long = sma_long[-1]
        prev_sma_short = sma_short[-2]
        prev_sma_long = sma_long[-2]
        latest_rsi = rsi[-1]
        
        sma_crossover = prev_sma_short >= prev_sma_long and latest_sma_short < latest_sma_long
        rsi_condition = latest_rsi > self.rsi_oversold
        price_below = prices[-1] < latest_sma_long
        
        if sma_crossover and rsi_condition and price_below:
            return True, f"SMA Crossover + RSI ({latest_rsi:.1f})"
        return False, ""
    
    def _check_mean_reversion_sell_signal(self, prices: List[float]) -> Tuple[bool, str]:
        """Mean Reversion strategy sell signal"""
        if len(prices) < 20:
            return False, ""
        
        sma = self.calculate_sma(prices, 20)
        rsi = self.calculate_rsi(prices, 14)
        
        latest_price = prices[-1]
        latest_sma = sma[-1]
        latest_rsi = rsi[-1]
        
        price_above = latest_price > latest_sma
        rsi_overbought = latest_rsi > self.rsi_overbought
        deviation_pct = ((latest_price - latest_sma) / latest_sma) * 100
        
        if price_above and rsi_overbought and deviation_pct > 1:
            return True, f"Mean Reversion ({deviation_pct:.1f}% above, RSI: {latest_rsi:.1f})"
        return False, ""
    
    def _check_breakout_sell_signal(self, prices: List[float]) -> Tuple[bool, str]:
        """Breakout strategy sell signal"""
        if len(prices) < 20:
            return False, ""
        
        lows = [min(prices[max(0, i-20):i+1]) for i in range(len(prices))]
        latest_low = lows[-1]
        prev_low = lows[-2] if len(lows) > 1 else latest_low
        
        breakdown = prices[-1] < latest_low and prices[-2] >= prev_low
        
        if breakdown:
            return True, f"Breakdown below ${latest_low:.2f}"
        return False, ""
    
    def _check_trend_following_sell_signal(self, prices: List[float]) -> Tuple[bool, str]:
        """Trend Following strategy sell signal"""
        if len(prices) < max(5, 20) + 1:
            return False, ""
        
        ema_short = self.calculate_ema(prices, 5)
        ema_long = self.calculate_ema(prices, 20)
        
        latest_ema_short = ema_short[-1]
        latest_ema_long = ema_long[-1]
        prev_ema_short = ema_short[-2]
        prev_ema_long = ema_long[-2]
        
        crossover = prev_ema_short >= prev_ema_long and latest_ema_short < latest_ema_long
        price_below = prices[-1] < latest_ema_long
        
        if crossover and price_below:
            return True, f"EMA Crossover (5/20)"
        return False, ""
    
    def open_position(self, price: float, quantity: float, order_type: OrderType, signal: str = "") -> Trade:
        """Open a new trading position"""
        if order_type == OrderType.BUY:
            stop_loss = price * (1 - self.stop_loss_pct)
            take_profit = price * (1 + self.take_profit_pct)
        else:
            stop_loss = price * (1 + self.stop_loss_pct)
            take_profit = price * (1 - self.take_profit_pct)
        
        trade = Trade(
            entry_time=datetime.now(),
            entry_price=price,
            quantity=quantity,
            order_type=order_type,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy=signal,
            symbol=self.symbol
        )
        self.positions.append(trade)
        
        # Place actual order if in LIVE or TESTNET mode
        if self.mode != TradeMode.PAPER and self.binance:
            side = "BUY" if order_type == OrderType.BUY else "SELL"
            
            # Format quantity with correct precision
            quantity_str = self.binance.format_quantity(quantity, self.symbol)
            price_str = self.binance.format_price(price, self.symbol)
            stop_loss_str = self.binance.format_price(stop_loss, self.symbol)
            take_profit_str = self.binance.format_price(take_profit, self.symbol)
            
            if self.mode == TradeMode.TESTNET:
                # Use test order on testnet
                result = self.binance.create_test_order(
                    self.symbol, side, "LIMIT", quantity, price
                )
            else:
                # Real order
                result = self.binance.create_order(
                    self.symbol, side, "LIMIT", quantity, price
                )
            
            if 'orderId' in result:
                trade.order_id = result['orderId']
            elif 'error' not in result:
                trade.order_id = -1  # Mark as placed
        
        return trade
    
    def close_position(self, trade: Trade, price: float) -> float:
        """Close an existing position"""
        profit = trade.close_trade(datetime.now(), price)
        self.current_balance += profit
        self.trade_history.append(trade)
        self.positions.remove(trade)
        
        # Update max drawdown
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        drawdown = ((self.peak_balance - self.current_balance) / self.peak_balance) * 100
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        return profit
    
    def close_all_positions(self, price: float) -> float:
        """Close all open positions at current price"""
        total_profit = 0.0
        for trade in self.positions[:]:
            if trade.status == PositionStatus.OPEN:
                total_profit += self.close_position(trade, price)
        return total_profit
    
    def execute_trade(self, prices: List[float], current_price: float) -> Tuple[str, str]:
        """Execute trading logic based on signals"""
        # Check stop-loss and take-profit for existing positions
        for trade in self.positions[:]:
            if trade.status == PositionStatus.OPEN:
                if trade.check_stop_loss(current_price):
                    self.close_position(trade, current_price)
                    return "STOP_LOSS", f"Hit SL at ${current_price:.2f}"
                elif trade.check_take_profit(current_price):
                    self.close_position(trade, current_price)
                    return "TAKE_PROFIT", f"Hit TP at ${current_price:.2f}"
                elif trade.order_type == OrderType.BUY and self.check_sell_signal(prices)[0]:
                    self.close_position(trade, current_price)
                    return "SELL", self.check_sell_signal(prices)[1]
                elif trade.order_type == OrderType.SELL and self.check_buy_signal(prices)[0]:
                    self.close_position(trade, current_price)
                    return "BUY", self.check_buy_signal(prices)[1]
        
        # Check if we should open new position
        if self.open_positions_count == 0:
            buy_signal, buy_reason = self.check_buy_signal(prices)
            sell_signal, sell_reason = self.check_sell_signal(prices)
            
            if buy_signal:
                stop_loss = current_price * (1 - self.stop_loss_pct)
                quantity = self.calculate_position_size(current_price, stop_loss, OrderType.BUY)
                if quantity > 0:
                    self.open_position(current_price, quantity, OrderType.BUY, buy_reason)
                    return "BUY", buy_reason
            elif sell_signal:
                stop_loss = current_price * (1 + self.stop_loss_pct)
                quantity = self.calculate_position_size(current_price, stop_loss, OrderType.SELL)
                if quantity > 0:
                    self.open_position(current_price, quantity, OrderType.SELL, sell_reason)
                    return "SELL", sell_reason
        
        return "HOLD", ""
    
    def fetch_prices(self, interval: str = "1h", limit: int = 100) -> List[float]:
        """Fetch real prices from Binance"""
        if not self.binance:
            return []
        
        klines = self.binance.get_klines(self.symbol, interval, limit)
        return [k['close'] for k in klines]
    
    def generate_sample_data(self, hours: int = 500) -> Tuple[List[datetime], List[float]]:
        """Generate sample price data for paper trading"""
        random.seed(42)
        
        now = datetime.now()
        timestamps = [now - timedelta(hours=i) for i in range(hours, 0, -1)]
        
        base_price = 50000
        prices = []
        
        for i in range(hours):
            trend = base_price + (i / hours) * 2000
            volatility = random.uniform(-200, 200)
            noise = random.uniform(-100, 100)
            
            if i % 50 == 0:
                large_move = random.uniform(-500, 500)
            else:
                large_move = 0
            
            price = trend + volatility + noise + large_move
            prices.append(price)
        
        # Add patterns
        for i in range(100, 150):
            if i < len(prices):
                prices[i] = prices[i] + (i - 100) * 20
        
        for i in range(200, 250):
            if i < len(prices):
                prices[i] = prices[i] - (i - 200) * 25
        
        for i in range(300, 350):
            if i < len(prices):
                prices[i] = prices[i] + (i - 300) * 15
        
        return timestamps, prices
    
    def run_backtest(self, hours: int = 500) -> dict:
        """Run a backtest on generated data"""
        timestamps, prices = self.generate_sample_data(hours)
        
        results = {
            'timestamps': timestamps,
            'prices': prices,
            'actions': [],
            'balance_history': [],
            'total_value_history': [],
            'signals': []
        }
        
        initial_balance = self.current_balance
        
        for i in range(len(prices)):
            current_price = prices[i]
            action, reason = self.execute_trade(prices[:i+1], current_price)
            
            results['actions'].append(action)
            results['signals'].append(reason)
            results['balance_history'].append(self.current_balance)
            results['total_value_history'].append(self.total_value)
        
        self.close_all_positions(prices[-1])
        
        final_balance = self.current_balance
        total_profit = final_balance - initial_balance
        
        results['summary'] = {
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'total_profit': total_profit,
            'return_pct': (total_profit / initial_balance) * 100,
            'total_trades': len(self.trade_history),
            'winning_trades': len([t for t in self.trade_history if t.status == PositionStatus.CLOSED and t.profit > 0]),
            'losing_trades': len([t for t in self.trade_history if t.status == PositionStatus.CLOSED and t.profit < 0]),
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'max_drawdown': self.max_drawdown
        }
        
        return results
    
    def run_live(self, interval: str = "1h", hours: int = 24) -> None:
        """Run live trading"""
        if self.mode == TradeMode.PAPER:
            print("Cannot run live trading in PAPER mode. Use TESTNET or LIVE.")
            return
        
        if not self.binance:
            print("Binance client not available.")
            return
        
        print(f"Starting live trading on {self.symbol}...")
        print(f"Mode: {self.mode.value}")
        print(f"Strategy: {self.strategy.value}")
        
        self.running = True
        
        try:
            while self.running:
                # Get current price
                price_result = self.binance.get_ticker_price(self.symbol)
                if 'error' in price_result:
                    print(f"Error getting price: {price_result['error']}")
                    time.sleep(60)
                    continue
                
                current_price = float(price_result['price'])
                
                # Get historical data
                prices = self.fetch_prices(interval, 100)
                if len(prices) < 50:
                    print(f"Not enough data points: {len(prices)}")
                    time.sleep(60)
                    continue
                
                # Execute trade
                action, reason = self.execute_trade(prices, current_price)
                
                if action != "HOLD":
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {action}: {reason} @ ${current_price:.2f}")
                
                # Print dashboard periodically
                if len(self.trade_history) > 0 and len(self.trade_history) % 5 == 0:
                    self.print_dashboard()
                
                # Sleep for the interval
                sleep_seconds = 60  # 1 minute for testing
                if interval == "1h":
                    sleep_seconds = 3600
                elif interval == "4h":
                    sleep_seconds = 14400
                elif interval == "1d":
                    sleep_seconds = 86400
                
                time.sleep(sleep_seconds)
        
        except KeyboardInterrupt:
            print("\nStopping live trading...")
            self.running = False
            self.close_all_positions(current_price)
            self.print_dashboard()
    
    def print_dashboard(self):
        """Print current dashboard"""
        print("\n" + "=" * 60)
        print("TRADING BOT DASHBOARD".center(60))
        print("=" * 60)
        
        profit_color = 'green' if self.total_profit > 0 else 'red'
        
        print(f"Current Balance: ${self.current_balance:.2f}")
        print(f"Total Value:     ${self.total_value:.2f}")
        print(f"Open Positions:  {self.open_positions_count}")
        print(f"Total Trades:    {len(self.trade_history)}")
        print(f"Total Profit:    ${self.total_profit:+.2f} ({self.total_profit/self.initial_balance*100:+.2f}%)")
        print(f"Win Rate:        {self.win_rate:.1f}%")
        print(f"Profit Factor:   {self.profit_factor:.2f}")
        print(f"Max Drawdown:   {self.max_drawdown:.2f}%")
        
        if self.positions:
            print("\n--- OPEN POSITIONS ---")
            for pos in self.positions:
                if pos.status == PositionStatus.OPEN:
                    print(f"  {pos.order_type.value} {pos.quantity:.8f} @ ${pos.entry_price:.2f} | SL: ${pos.stop_loss:.2f} | TP: ${pos.take_profit:.2f}")
        
        print("=" * 60)


def print_colored(text: str, color: str = "white", end: str = '\n'):
    """Print colored text for Termux"""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'purple': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'bold': '\033[1m',
        'end': '\033[0m'
    }
    
    color_code = colors.get(color, colors['white'])
    print(f"{color_code}{text}{colors['end']}", end=end)


def print_header(text: str):
    """Print a header"""
    print_colored("\n" + "=" * 60, 'cyan')
    print_colored(text.center(60), 'bold')
    print_colored("=" * 60, 'cyan')


def save_api_keys(api_key: str, api_secret: str, filename: str = "binance_keys.json") -> bool:
    """Save API keys to file"""
    try:
        with open(filename, 'w') as f:
            json.dump({'api_key': api_key, 'api_secret': api_secret}, f)
        return True
    except Exception as e:
        print(f"Error saving API keys: {e}")
        return False


def load_api_keys(filename: str = "binance_keys.json") -> Tuple[str, str]:
    """Load API keys from file"""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            return data.get('api_key', ''), data.get('api_secret', '')
    except:
        return '', ''


def interactive_mode():
    """Run interactive trading bot"""
    print_header("BINANCE TRADING BOT - Termux Edition")
    
    # Load API keys if available
    api_key, api_secret = load_api_keys()
    
    # Mode selection
    print_colored("Select Trading Mode:", 'bold')
    print_colored("1. Paper Trading (simulated)", 'white')
    print_colored("2. Testnet Trading (real orders, fake money)", 'yellow')
    print_colored("3. Live Trading (real orders, real money)", 'red')
    print()
    
    mode_choice = input("Mode (1-3): ").strip() or "1"
    
    if mode_choice == '1':
        mode = TradeMode.PAPER
        symbol = input("Symbol (e.g., BTCUSDT): ").strip() or "BTCUSDT"
        initial = float(input("Initial balance ($): ").strip() or "5.0")
        api_key, api_secret = "", ""
    elif mode_choice == '2':
        mode = TradeMode.TESTNET
        symbol = input("Symbol (e.g., BTCUSDT): ").strip() or "BTCUSDT"
        initial = 100.0  # Testnet gives fake BTC and USDT
        
        if not api_key or not api_secret:
            print_colored("\nEnter your Binance API keys for testnet:", 'yellow')
            api_key = input("API Key: ").strip()
            api_secret = input("API Secret: ").strip()
            
            if api_key and api_secret:
                save_api_keys(api_key, api_secret)
    elif mode_choice == '3':
        mode = TradeMode.LIVE
        symbol = input("Symbol (e.g., BTCUSDT): ").strip() or "BTCUSDT"
        initial = 5.0
        
        if not api_key or not api_secret:
            print_colored("\nEnter your Binance API keys for LIVE trading:", 'red')
            print_colored("WARNING: This will use real money!", 'red')
            api_key = input("API Key: ").strip()
            api_secret = input("API Secret: ").strip()
            
            if api_key and api_secret:
                save_api_keys(api_key, api_secret)
    else:
        mode = TradeMode.PAPER
        symbol = "BTCUSDT"
        initial = 5.0
        api_key, api_secret = "", ""
    
    # Create bot
    bot = TradingBotBinance(
        initial_balance=initial,
        symbol=symbol,
        mode=mode,
        api_key=api_key,
        api_secret=api_secret
    )
    
    # Strategy selection
    print_colored("\nSelect Strategy:", 'bold')
    print_colored("1. SMA Crossover + RSI (default)", 'white')
    print_colored("2. Mean Reversion", 'white')
    print_colored("3. Breakout", 'white')
    print_colored("4. Trend Following", 'white')
    strategy_choice = input("Strategy (1-4): ").strip() or "1"
    
    strategy_map = {
        '1': StrategyType.SMA_CROSSOVER,
        '2': StrategyType.MEAN_REVERSION,
        '3': StrategyType.BREAKOUT,
        '4': StrategyType.TREND_FOLLOWING
    }
    bot.strategy = strategy_map.get(strategy_choice, StrategyType.SMA_CROSSOVER)
    
    # Risk parameters
    try:
        bot.risk_per_trade = float(input("Risk per trade (%%): ").strip() or "2.0") / 100
        bot.stop_loss_pct = float(input("Stop loss (%%): ").strip() or "1.0") / 100
        bot.take_profit_pct = float(input("Take profit (%%): ").strip() or "3.0") / 100
    except ValueError:
        pass
    
    print_colored(f"\nStarting {mode.value} trading on {symbol}...", 'yellow')
    print_colored(f"Strategy: {bot.strategy.value}", 'white')
    print_colored(f"Risk: {bot.risk_per_trade*100:.1f}% | SL: {bot.stop_loss_pct*100:.1f}% | TP: {bot.take_profit_pct*100:.1f}%\n", 'white')
    
    if mode == TradeMode.PAPER:
        # Run backtest
        hours = int(input("Hours of data to simulate: ").strip() or "500")
        print_colored("Running backtest...", 'yellow')
        results = bot.run_backtest(hours=hours)
        
        # Display results
        bot.print_dashboard()
        
        summary = results['summary']
        print_header("BACKTEST SUMMARY")
        
        profit_color = 'green' if summary['total_profit'] > 0 else 'red'
        win_color = 'green' if summary['win_rate'] > 50 else 'yellow' if summary['win_rate'] > 30 else 'red'
        pf_color = 'green' if summary['profit_factor'] > 1.5 else 'yellow' if summary['profit_factor'] > 1 else 'red'
        dd_color = 'green' if summary['max_drawdown'] < 10 else 'yellow' if summary['max_drawdown'] < 20 else 'red'
        
        print_colored(f"Initial Balance:  ${summary['initial_balance']:.2f}", 'white')
        print_colored(f"Final Balance:    ${summary['final_balance']:.2f}", profit_color)
        print_colored(f"Total Profit:     ", end='')
        print_colored(f"${summary['total_profit']:+.2f} ({summary['return_pct']:+.2f}%)", profit_color)
        print_colored(f"Total Trades:     {summary['total_trades']}", 'white')
        print_colored(f"Winning Trades:   {summary['winning_trades']}", 'green')
        print_colored(f"Losing Trades:    {summary['losing_trades']}", 'red')
        print_colored(f"Win Rate:         {summary['win_rate']:.1f}%", win_color)
        print_colored(f"Profit Factor:    {summary['profit_factor']:.2f}", pf_color)
        print_colored(f"Max Drawdown:    {summary['max_drawdown']:.2f}%", dd_color)
    else:
        # Live trading
        print_colored("Starting live trading... (Press Ctrl+C to stop)", 'green')
        print_colored("WARNING: This will execute real orders!", 'red')
        confirm = input("Type 'YES' to confirm: ").strip()
        
        if confirm == 'YES':
            bot.run_live()
        else:
            print_colored("Cancelled.", 'yellow')


if __name__ == "__main__":
    interactive_mode()
