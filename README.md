# Trading Bot

A simple cryptocurrency trading bot with paper trading capabilities. Built with Python and Streamlit for easy visualization and control.

## Features

- **Paper Trading**: Test trading strategies without real money
- **Technical Indicators**: 
  - Simple Moving Average (SMA) Crossover
  - Relative Strength Index (RSI)
- **Real-time Dashboard**: Interactive Streamlit interface
- **Backtesting**: Test strategies on historical data
- **Trade Tracking**: Monitor open positions and trade history

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Run the Dashboard
```bash
streamlit run app.py
```

### Run Backtest
```bash
python trading_bot.py
```

## Configuration

Edit `config.py` to customize:
- Initial balance
- Trading pair
- Trade quantity
- Strategy parameters (SMA periods, RSI settings)

## Strategy

The bot uses a combination of:
1. **SMA Crossover**: Buy when short SMA crosses above long SMA, sell when it crosses below
2. **RSI Filter**: Only trade when RSI is not in overbought (>70) or oversold (<30) conditions

## Project Structure

- `app.py`: Streamlit dashboard application
- `trading_bot.py`: Core trading bot logic and strategies
- `config.py`: Configuration settings
- `requirements.txt`: Python dependencies

## Requirements

- Python 3.8+
- Streamlit
- Pandas
- NumPy
- Plotly

## Note

This is a **paper trading bot** designed for educational purposes. It does not connect to real exchanges or use real money. Always test thoroughly before using with real funds.
