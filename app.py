"""
Streamlit Trading Bot Dashboard
Real-time visualization and control for the trading bot
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import numpy as np

from trading_bot import TradingBot, OrderType, PositionStatus
from config import INITIAL_BALANCE, TRADE_SYMBOL, TRADE_QUANTITY


# Page configuration
st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .trade-card {
        background: #f8f9fa;
        padding: 0.75rem;
        border-radius: 0.25rem;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    .trade-card.sell {
        border-left-color: #dc3545;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def create_trading_bot():
    """Create and cache the trading bot instance"""
    return TradingBot(initial_balance=INITIAL_BALANCE)


def generate_sample_data(days: int = 7) -> pd.DataFrame:
    """Generate realistic sample price data"""
    np.random.seed(42)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='15min')
    
    # Create more realistic BTC-like price data
    base_trend = np.linspace(45000, 52000, len(dates))
    volatility = np.random.randn(len(dates)) * 1000
    noise = np.random.randn(len(dates)) * 200
    
    prices = base_trend + volatility.cumsum() + noise
    
    # Add some patterns
    midpoint = len(dates) // 2
    prices[midpoint:midpoint+50] = prices[midpoint:midpoint+50] + np.linspace(0, 1500, 50)
    prices[midpoint+100:midpoint+150] = prices[midpoint+100:midpoint+150] - np.linspace(0, 1000, 50)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices - np.abs(np.random.randn(len(dates)) * 100),
        'high': prices + np.abs(np.random.randn(len(dates)) * 150),
        'low': prices - np.abs(np.random.randn(len(dates)) * 150),
        'close': prices,
        'volume': np.random.randint(50, 500, len(dates)) * 10
    })
    
    return data


def display_metrics(bot: TradingBot):
    """Display key metrics in the dashboard"""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Balance", f"${bot.current_balance:.2f}", 
                 f"${bot.current_balance - INITIAL_BALANCE:.2f}")
    
    with col2:
        st.metric("Total Value", f"${bot.total_value:.2f}")
    
    with col3:
        st.metric("Open Positions", bot.open_positions_count)
    
    with col4:
        total_trades = len(bot.trade_history)
        st.metric("Total Trades", total_trades)
    
    with col5:
        win_rate = bot.win_rate if total_trades > 0 else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")


def display_balance_chart(bot: TradingBot, history: list):
    """Display balance over time"""
    if not history:
        st.warning("No trading history available")
        return
    
    df = pd.DataFrame(history)
    df['time'] = pd.to_datetime(df['time'])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['balance'],
        name='Balance',
        line=dict(color='#1f77b4', width=2),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.1)'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['time'],
        y=df['total_value'],
        name='Total Value',
        line=dict(color='#ff7f0e', width=2)
    ))
    
    # Add buy/sell markers
    buy_actions = df[df['action'] == 'BUY']
    sell_actions = df[df['action'] == 'SELL']
    
    if len(buy_actions) > 0:
        fig.add_trace(go.Scatter(
            x=buy_actions['time'],
            y=buy_actions['balance'],
            mode='markers',
            name='Buy Signal',
            marker=dict(color='green', size=10, symbol='triangle-up')
        ))
    
    if len(sell_actions) > 0:
        fig.add_trace(go.Scatter(
            x=sell_actions['time'],
            y=sell_actions['balance'],
            mode='markers',
            name='Sell Signal',
            marker=dict(color='red', size=10, symbol='triangle-down')
        ))
    
    fig.update_layout(
        title="Account Balance Over Time",
        xaxis_title="Time",
        yaxis_title="Value (USD)",
        hovermode='x unified',
        height=400,
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True)


def display_price_chart(data: pd.DataFrame, bot: TradingBot):
    """Display price chart with indicators"""
    fig = go.Figure()
    
    # Candlestick chart
    fig.add_trace(go.Candlestick(
        x=data['timestamp'],
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name='Price',
        increasing_line_color='#28a745',
        decreasing_line_color='#dc3545'
    ))
    
    # Add SMA indicators
    sma_10 = bot.calculate_sma(data, 10)
    sma_30 = bot.calculate_sma(data, 30)
    
    fig.add_trace(go.Scatter(
        x=data['timestamp'],
        y=sma_10,
        name='SMA 10',
        line=dict(color='blue', width=1)
    ))
    
    fig.add_trace(go.Scatter(
        x=data['timestamp'],
        y=sma_30,
        name='SMA 30',
        line=dict(color='purple', width=1)
    ))
    
    # Add RSI in a separate subplot
    rsi = bot.calculate_rsi(data)
    
    fig.update_layout(
        title=f"{TRADE_SYMBOL} Price Chart with Indicators",
        xaxis_title="Time",
        yaxis_title="Price (USD)",
        height=500,
        template="plotly_white",
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # RSI subplot
    fig_rsi = go.Figure()
    
    fig_rsi.add_trace(go.Scatter(
        x=data['timestamp'],
        y=rsi,
        name='RSI',
        line=dict(color='orange', width=2)
    ))
    
    # Add overbought/oversold lines
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", 
                     annotation_text="Overbought (70)")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", 
                     annotation_text="Oversold (30)")
    
    fig_rsi.update_layout(
        title="Relative Strength Index (RSI)",
        xaxis_title="Time",
        yaxis_title="RSI",
        height=300,
        template="plotly_white",
        yaxis_range=[0, 100]
    )
    
    st.plotly_chart(fig_rsi, use_container_width=True)


def display_trade_history(bot: TradingBot):
    """Display trade history table"""
    if not bot.trade_history:
        st.info("No trades executed yet")
        return
    
    trade_data = []
    for trade in bot.trade_history:
        trade_data.append({
            'Type': trade.order_type.value if trade.order_type else 'N/A',
            'Entry Time': trade.entry_time,
            'Entry Price': f"${trade.entry_price:.2f}",
            'Exit Time': trade.exit_time,
            'Exit Price': f"${trade.exit_price:.2f}" if trade.exit_price else 'Open',
            'Quantity': trade.quantity,
            'Profit': f"${trade.profit:.4f}" if trade.profit else 'Open',
            'Status': trade.status.value
        })
    
    df = pd.DataFrame(trade_data)
    
    # Color code profits
    def color_profit(val):
        if val == 'Open':
            return 'color: blue'
        elif float(val.replace('$', '')) > 0:
            return 'color: green'
        else:
            return 'color: red'
    
    st.dataframe(
        df.style.applymap(color_profit, subset=['Profit']),
        use_container_width=True,
        height=400
    )


def display_open_positions(bot: TradingBot):
    """Display currently open positions"""
    open_positions = [p for p in bot.positions if p.status == PositionStatus.OPEN]
    
    if not open_positions:
        st.info("No open positions")
        return
    
    for pos in open_positions:
        profit = (pos.entry_price - bot.current_balance) * pos.quantity if pos.order_type == OrderType.SELL else \
                (bot.current_balance - pos.entry_price) * pos.quantity
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Type", pos.order_type.value)
        with col2:
            st.metric("Entry Price", f"${pos.entry_price:.2f}")
        with col3:
            st.metric("Quantity", pos.quantity)
        with col4:
            st.metric("Unrealized P&L", f"${profit:.4f}", 
                     delta_color="normal" if profit >= 0 else "inverse")


def run_simulation(bot: TradingBot, days: int = 7):
    """Run a trading simulation"""
    with st.spinner("Running simulation..."):
        # Generate sample data
        data = generate_sample_data(days=days)
        
        # Store initial state
        initial_balance = bot.current_balance
        
        # Run backtest
        results = bot.run_backtest(data, quantity=TRADE_QUANTITY)
        
        return data, results


def main():
    """Main application"""
    # Header
    st.markdown('<div class="main-header">📈 Trading Bot Dashboard</div>', unsafe_allow_html=True)
    st.markdown("### Paper Trading with $5 USDT")
    
    # Initialize bot
    bot = create_trading_bot()
    
    # Sidebar
    st.sidebar.title("⚙️ Settings")
    
    # Trading parameters
    st.sidebar.subheader("Trading Parameters")
    initial_balance = st.sidebar.number_input(
        "Initial Balance (USDT)", 
        value=INITIAL_BALANCE, 
        min_value=1.0, 
        step=1.0
    )
    
    trade_symbol = st.sidebar.text_input("Trading Pair", value=TRADE_SYMBOL)
    trade_quantity = st.sidebar.number_input(
        "Trade Quantity", 
        value=TRADE_QUANTITY, 
        min_value=0.00001, 
        step=0.00001,
        format="%.5f"
    )
    
    # Strategy parameters
    st.sidebar.subheader("Strategy Settings")
    short_sma = st.sidebar.slider("Short SMA Period", 5, 50, 10)
    long_sma = st.sidebar.slider("Long SMA Period", 10, 100, 30)
    rsi_period = st.sidebar.slider("RSI Period", 5, 30, 14)
    
    # Simulation controls
    st.sidebar.subheader("Simulation")
    sim_days = st.sidebar.slider("Simulation Days", 1, 30, 7)
    
    if st.sidebar.button("Reset Bot", use_container_width=True):
        bot = create_trading_bot()
        st.rerun()
    
    # Update bot configuration
    bot.initial_balance = initial_balance
    bot.current_balance = initial_balance
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard", 
        "📈 Price Analysis", 
        "💼 Trade History",
        "⚡ Simulation"
    ])
    
    with tab1:
        # Display metrics
        display_metrics(bot)
        
        st.markdown("---")
        
        # Display open positions
        st.subheader("📋 Open Positions")
        display_open_positions(bot)
        
        # Display balance chart
        st.subheader("📈 Performance Chart")
        
        # For demo, create some sample history if none exists
        if not hasattr(bot, '_history') or not bot._history:
            sample_history = []
            for i in range(24):
                sample_history.append({
                    'time': datetime.now() - timedelta(hours=24-i),
                    'balance': initial_balance + np.random.randn() * 0.5,
                    'total_value': initial_balance + np.random.randn() * 0.5,
                    'action': np.random.choice(['HOLD', 'BUY', 'SELL'])
                })
            bot._history = sample_history
        
        display_balance_chart(bot, bot._history)
    
    with tab2:
        st.subheader(f"📊 {trade_symbol} Price Analysis")
        
        # Generate sample data
        sample_data = generate_sample_data(days=sim_days)
        display_price_chart(sample_data, bot)
        
        # Strategy signals
        st.subheader("🎯 Current Signals")
        col1, col2 = st.columns(2)
        
        with col1:
            buy_signal = bot.check_buy_signal(sample_data)
            st.metric("Buy Signal", "✅ YES" if buy_signal else "❌ NO",
                     delta="Active" if buy_signal else "Inactive")
        
        with col2:
            sell_signal = bot.check_sell_signal(sample_data)
            st.metric("Sell Signal", "✅ YES" if sell_signal else "❌ NO",
                     delta="Active" if sell_signal else "Inactive")
    
    with tab3:
        st.subheader("📜 Trade History")
        display_trade_history(bot)
        
        # Summary statistics
        if bot.trade_history:
            st.subheader("📊 Trade Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            total_trades = len(bot.trade_history)
            winning_trades = len([t for t in bot.trade_history if t.profit > 0])
            losing_trades = total_trades - winning_trades
            total_profit = bot.total_profit
            
            with col1:
                st.metric("Total Trades", total_trades)
            with col2:
                st.metric("Winning Trades", winning_trades, 
                         f"{winning_trades/total_trades*100:.1f}%" if total_trades > 0 else "0%")
            with col3:
                st.metric("Losing Trades", losing_trades)
            with col4:
                st.metric("Total Profit", f"${total_profit:.2f}")
    
    with tab4:
        st.subheader("⚡ Run Simulation")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"""
            ### Simulation Settings
            - **Initial Balance:** ${initial_balance:.2f} USDT
            - **Trading Pair:** {trade_symbol}
            - **Trade Quantity:** {trade_quantity:.5f}
            - **Duration:** {sim_days} days
            - **Strategy:** SMA Crossover + RSI
            """)
        
        with col2:
            st.markdown(f"""
            ### Strategy Parameters
            - **Short SMA:** {short_sma} periods
            - **Long SMA:** {long_sma} periods
            - **RSI Period:** {rsi_period} periods
            """)
        
        if st.button("🚀 Start Simulation", use_container_width=True):
            # Reset bot
            bot = TradingBot(initial_balance=initial_balance)
            
            # Run simulation
            data, results = run_simulation(bot, days=sim_days)
            
            # Store history
            bot._history = results['balance_history']
            
            # Display results
            st.success("Simulation completed!")
            
            # Summary
            summary = results['summary']
            st.subheader("📊 Simulation Results")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Initial Balance", f"${summary['initial_balance']:.2f}")
            with col2:
                st.metric("Final Balance", f"${summary['final_balance']:.2f}")
            with col3:
                st.metric("Total Profit", f"${summary['total_profit']:.2f}",
                         f"{summary['return_pct']:.2f}%")
            with col4:
                st.metric("Win Rate", f"{summary['win_rate']:.1f}%")
            
            # Trade details
            st.subheader("📈 Trade Details")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Trades", summary['total_trades'])
            with col2:
                st.metric("Winning Trades", summary['winning_trades'])
            with col3:
                st.metric("Losing Trades", summary['losing_trades'])
            
            # Display charts
            st.subheader("📊 Performance Charts")
            display_balance_chart(bot, results['balance_history'])
            display_price_chart(data, bot)
            
            # Trade history
            st.subheader("📜 Trade History")
            display_trade_history(bot)


if __name__ == "__main__":
    main()
