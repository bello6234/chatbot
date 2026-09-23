"""
Lite Trading Bot - Termux Compatible
No numpy/pandas required - Pure Python
Uses SMA Crossover + RSI strategy for paper trading with $5 USDT
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random
import time


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
            self.profit = (exit_price - self.entry_price) * self.quantity
        elif self.order_type == OrderType.SELL:
            self.profit = (self.entry_price - exit_price) * self.quantity
        
        return self.profit


class TradingBotLite:
    """Lite trading bot without numpy/pandas"""
    
    def __init__(self, initial_balance: float = 5.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.positions: List[Trade] = []
        self.trade_history: List[Trade] = []
        self.start_time = datetime.now()
        
        # Strategy parameters
        self.short_sma_period = 10
        self.long_sma_period = 30
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
    
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
    
    def calculate_sma(self, prices: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average - Pure Python"""
        if len(prices) < period:
            return [sum(prices[:i+1]) / (i+1) for i in range(len(prices))]
        
        sma = []
        for i in range(len(prices)):
            start = max(0, i - period + 1)
            window = prices[start:i+1]
            sma.append(sum(window) / len(window))
        return sma
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calculate Relative Strength Index - Pure Python"""
        if len(prices) < 2:
            return [50.0] * len(prices)
        
        rsi = [50.0]  # Start with neutral value
        
        for i in range(1, len(prices)):
            # Calculate price changes
            delta = prices[i] - prices[i-1]
            
            if i < period + 1:
                # Initial period - use all available data
                gains = []
                losses = []
                for j in range(1, i):
                    change = prices[j] - prices[j-1]
                    if change > 0:
                        gains.append(change)
                    else:
                        losses.append(abs(change))
                
                if len(gains) == 0:
                    avg_gain = 0
                else:
                    avg_gain = sum(gains) / len(gains)
                
                if len(losses) == 0:
                    avg_loss = 0.0001  # Avoid division by zero
                else:
                    avg_loss = sum(losses) / len(losses)
            else:
                # Use exponential moving average approach
                prev_gain = gains[-1] if gains else 0
                prev_loss = losses[-1] if losses else 0.0001
                
                if delta > 0:
                    avg_gain = (prev_gain * (period - 1) + delta) / period
                    avg_loss = (prev_loss * (period - 1)) / period
                else:
                    avg_gain = (prev_gain * (period - 1)) / period
                    avg_loss = (prev_loss * (period - 1) + abs(delta)) / period
            
            # Store for next iteration
            gains = gains + [delta] if delta > 0 else gains
            losses = losses + [abs(delta)] if delta < 0 else losses
            
            if len(gains) < period:
                avg_gain = sum(gains) / len(gains) if gains else 0
                avg_loss = sum(losses) / len(losses) if losses else 0.0001
            
            if avg_loss == 0:
                rs = 100
            else:
                rs = avg_gain / avg_loss
            
            rsi_value = 100 - (100 / (1 + rs))
            rsi.append(rsi_value)
        
        return rsi
    
    def check_buy_signal(self, prices: List[float]) -> bool:
        """Check if buy signal is triggered"""
        if len(prices) < max(self.long_sma_period, self.rsi_period) + 1:
            return False
        
        sma_short = self.calculate_sma(prices, self.short_sma_period)
        sma_long = self.calculate_sma(prices, self.long_sma_period)
        rsi = self.calculate_rsi(prices, self.rsi_period)
        
        # Get latest values
        latest_sma_short = sma_short[-1]
        latest_sma_long = sma_long[-1]
        prev_sma_short = sma_short[-2]
        prev_sma_long = sma_long[-2]
        latest_rsi = rsi[-1]
        
        # SMA Crossover: Short SMA crosses above Long SMA
        sma_crossover = prev_sma_short <= prev_sma_long and latest_sma_short > latest_sma_long
        
        # RSI condition: Not overbought
        rsi_condition = latest_rsi < self.rsi_overbought
        
        return sma_crossover and rsi_condition
    
    def check_sell_signal(self, prices: List[float]) -> bool:
        """Check if sell signal is triggered"""
        if len(prices) < max(self.long_sma_period, self.rsi_period) + 1:
            return False
        
        sma_short = self.calculate_sma(prices, self.short_sma_period)
        sma_long = self.calculate_sma(prices, self.long_sma_period)
        rsi = self.calculate_rsi(prices, self.rsi_period)
        
        # Get latest values
        latest_sma_short = sma_short[-1]
        latest_sma_long = sma_long[-1]
        prev_sma_short = sma_short[-2]
        prev_sma_long = sma_long[-2]
        latest_rsi = rsi[-1]
        
        # SMA Crossover: Short SMA crosses below Long SMA
        sma_crossover = prev_sma_short >= prev_sma_long and latest_sma_short < latest_sma_long
        
        # RSI condition: Not oversold
        rsi_condition = latest_rsi > self.rsi_oversold
        
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
        return trade
    
    def close_position(self, trade: Trade, price: float) -> float:
        """Close an existing position"""
        profit = trade.close_trade(datetime.now(), price)
        self.current_balance += profit
        self.trade_history.append(trade)
        self.positions.remove(trade)
        return profit
    
    def close_all_positions(self, price: float) -> float:
        """Close all open positions at current price"""
        total_profit = 0.0
        for trade in self.positions[:]:  # Iterate over a copy
            if trade.status == PositionStatus.OPEN:
                total_profit += self.close_position(trade, price)
        return total_profit
    
    def execute_trade(self, prices: List[float], current_price: float, quantity: float) -> str:
        """Execute trading logic based on signals"""
        # Check if we should close existing positions
        for trade in self.positions[:]:
            if trade.status == PositionStatus.OPEN:
                if trade.order_type == OrderType.BUY:
                    if self.check_sell_signal(prices):
                        self.close_position(trade, current_price)
                        return "SELL"
                elif trade.order_type == OrderType.SELL:
                    if self.check_buy_signal(prices):
                        self.close_position(trade, current_price)
                        return "BUY"
        
        # Check if we should open new position
        if self.open_positions_count == 0:
            if self.check_buy_signal(prices):
                self.open_position(current_price, quantity, OrderType.BUY)
                return "BUY"
            elif self.check_sell_signal(prices):
                self.open_position(current_price, quantity, OrderType.SELL)
                return "SELL"
        
        return "HOLD"
    
    def generate_sample_data(self, hours: int = 240) -> Tuple[List[datetime], List[float]]:
        """Generate sample price data for testing - Pure Python"""
        random.seed(42)
        
        # Generate timestamps
        now = datetime.now()
        timestamps = [now - timedelta(hours=i) for i in range(hours, 0, -1)]
        
        # Generate realistic BTC-like price data
        base_price = 50000
        prices = []
        current = base_price
        
        for i in range(hours):
            # Add trend
            trend = (i / hours) * 2000  # Overall upward trend
            
            # Add volatility
            volatility = random.uniform(-100, 100)
            
            # Add noise
            noise = random.uniform(-50, 50)
            
            current = base_price + trend + volatility + noise
            prices.append(current)
        
        # Add some patterns for testing
        # Create a bullish crossover around hour 100
        for i in range(80, 120):
            if i < len(prices):
                prices[i] = prices[i] + (i - 80) * 10
        
        # Create a bearish crossover around hour 200
        for i in range(180, 220):
            if i < len(prices):
                prices[i] = prices[i] - (i - 180) * 15
        
        return timestamps, prices
    
    def run_backtest(self, hours: int = 240, quantity: float = 0.0001) -> dict:
        """Run a backtest on generated data"""
        timestamps, prices = self.generate_sample_data(hours)
        
        results = {
            'timestamps': timestamps,
            'prices': prices,
            'actions': [],
            'balance_history': [],
            'total_value_history': []
        }
        
        initial_balance = self.current_balance
        
        for i in range(len(prices)):
            current_price = prices[i]
            current_time = timestamps[i]
            
            # Execute trade logic
            action = self.execute_trade(prices[:i+1], current_price, quantity)
            results['actions'].append(action)
            
            # Record state
            results['balance_history'].append(self.current_balance)
            results['total_value_history'].append(self.total_value)
        
        # Close all positions at the end
        self.close_all_positions(prices[-1])
        
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
    print_colored("\n" + "=" * 50, 'cyan')
    print_colored(text.center(50), 'bold')
    print_colored("=" * 50, 'cyan')


def print_trade(trade: Trade):
    """Print trade details"""
    status_color = 'green' if trade.status == PositionStatus.CLOSED and trade.profit > 0 else \
                  'red' if trade.status == PositionStatus.CLOSED and trade.profit < 0 else 'yellow'
    
    type_str = trade.order_type.value if trade.order_type else 'N/A'
    entry = trade.entry_time.strftime('%Y-%m-%d %H:%M')
    exit_str = trade.exit_time.strftime('%Y-%m-%d %H:%M') if trade.exit_time else 'Open'
    
    print_colored(f"  {type_str:6} | {entry} | ${trade.entry_price:8.2f} | {exit_str:19} | ${trade.exit_price:8.2f} | "
                 f"{trade.quantity:10.6f} | ", end='')
    
    if trade.status == PositionStatus.CLOSED:
        profit_str = f"${trade.profit:8.4f}"
        print_colored(profit_str, status_color)
    else:
        print_colored("Open", 'yellow')


def print_dashboard(bot: TradingBotLite):
    """Print dashboard in terminal"""
    print_header("TRADING BOT DASHBOARD")
    
    # Metrics
    print_colored(f"\nCurrent Balance: ${bot.current_balance:.2f}", 'green')
    print_colored(f"Total Value:     ${bot.total_value:.2f}", 'cyan')
    print_colored(f"Open Positions:  {bot.open_positions_count}", 'yellow')
    print_colored(f"Total Trades:    {len(bot.trade_history)}", 'blue')
    print_colored(f"Win Rate:        {bot.win_rate:.1f}%", 'purple')
    
    # Open positions
    if bot.positions:
        print_colored("\n--- OPEN POSITIONS ---", 'yellow')
        for pos in bot.positions:
            if pos.status == PositionStatus.OPEN:
                print_trade(pos)
    
    # Trade history
    if bot.trade_history:
        print_colored("\n--- TRADE HISTORY ---", 'blue')
        print_colored(f"{'Type':6} | {'Entry Time':16} | {'Entry':>8} | {'Exit Time':16} | {'Exit':>8} | {'Qty':>10} | {'Profit':>8}", 'bold')
        print_colored("-" * 85, 'white')
        for trade in sorted(bot.trade_history, key=lambda x: x.entry_time, reverse=True):
            print_trade(trade)


def interactive_mode():
    """Run interactive trading bot in terminal"""
    print_header("LITE TRADING BOT - Termux Edition")
    print_colored("Starting with $5 USDT paper trading...\n")
    
    # Create bot
    bot = TradingBotLite(initial_balance=5.0)
    
    # Run backtest
    print_colored("Running backtest on sample data...", 'yellow')
    results = bot.run_backtest(hours=240, quantity=0.0001)
    
    # Display results
    print_dashboard(bot)
    
    # Summary
    summary = results['summary']
    print_header("BACKTEST SUMMARY")
    print_colored(f"Initial Balance:  ${summary['initial_balance']:.2f}", 'white')
    print_colored(f"Final Balance:    ${summary['final_balance']:.2f}", 'green' if summary['total_profit'] > 0 else 'red')
    print_colored(f"Total Profit:     ${summary['total_profit']:+.2f} ({summary['return_pct']:+.2f}%)", 
                 'green' if summary['total_profit'] > 0 else 'red')
    print_colored(f"Total Trades:     {summary['total_trades']}", 'white')
    print_colored(f"Winning Trades:   {summary['winning_trades']}", 'green')
    print_colored(f"Losing Trades:    {summary['losing_trades']}", 'red')
    print_colored(f"Win Rate:         {summary['win_rate']:.1f}%", 'white')
    
    # Show strategy parameters
    print_header("STRATEGY PARAMETERS")
    print_colored(f"Short SMA Period:    {bot.short_sma_period}", 'white')
    print_colored(f"Long SMA Period:     {bot.long_sma_period}", 'white')
    print_colored(f"RSI Period:          {bot.rsi_period}", 'white')
    print_colored(f"RSI Overbought:     {bot.rsi_overbought}", 'white')
    print_colored(f"RSI Oversold:       {bot.rsi_oversold}", 'white')
    
    print_colored("\n" + "=" * 50 + "\n", 'cyan')


def custom_backtest():
    """Run custom backtest with user input"""
    print_header("CUSTOM BACKTEST")
    
    try:
        initial = float(input("Initial balance ($): ") or "5.0")
        hours = int(input("Hours of data to simulate: ") or "240")
        quantity = float(input("Trade quantity (BTC): ") or "0.0001")
        short_sma = int(input("Short SMA period: ") or "10")
        long_sma = int(input("Long SMA period: ") or "30")
        rsi_period = int(input("RSI period: ") or "14")
    except (ValueError, EOFError):
        print_colored("Invalid input! Using defaults.", 'red')
        initial = 5.0
        hours = 240
        quantity = 0.0001
        short_sma = 10
        long_sma = 30
        rsi_period = 14
    
    bot = TradingBotLite(initial_balance=initial)
    bot.short_sma_period = short_sma
    bot.long_sma_period = long_sma
    bot.rsi_period = rsi_period
    
    print_colored("\nRunning backtest...", 'yellow')
    results = bot.run_backtest(hours=hours, quantity=quantity)
    
    print_dashboard(bot)
    print_header("BACKTEST RESULTS")
    summary = results['summary']
    print_colored(f"Return: {summary['return_pct']:+.2f}%", 
                 'green' if summary['return_pct'] > 0 else 'red')
    print_colored(f"Win Rate: {summary['win_rate']:.1f}%", 'white')


def main():
    """Main menu"""
    print_header("LITE TRADING BOT MENU")
    print_colored("1. Run default backtest ($5 USDT)", 'white')
    print_colored("2. Run custom backtest", 'white')
    print_colored("3. Exit", 'white')
    print()
    
    try:
        choice = input("Select option (1-3): ").strip()
    except EOFError:
        # Auto-run default if no input (for testing)
        choice = '1'
    
    if choice == '1':
        interactive_mode()
    elif choice == '2':
        custom_backtest()
    elif choice == '3':
        print_colored("Goodbye!\n", 'cyan')
    else:
        print_colored("Invalid choice. Using default.\n", 'red')
        interactive_mode()


if __name__ == "__main__":
    main()
