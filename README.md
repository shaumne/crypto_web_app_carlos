# Crypto Trading Web Application

A comprehensive cryptocurrency trading platform built with Flask that provides automated technical analysis, trading signals, and portfolio management. This application replaces Google Sheets functionality with a robust web interface and eliminates API rate limiting issues.

## Features

### 🚀 Core Functionality
- **Real-time Technical Analysis**: RSI, Moving Averages (MA50, MA200), EMA10, ATR calculations
- **Automated Trading Signals**: Buy/Sell recommendations based on multiple technical indicators
- **Portfolio Management**: Track positions, orders, and performance
- **Risk Management**: Automatic Take Profit and Stop Loss monitoring
- **Exchange Integration**: Direct integration with Crypto.com exchange API

### 📊 Dashboard & Analytics
- **Live Dashboard**: Real-time overview of positions, orders, and performance
- **Interactive Charts**: Price movements, P&L tracking, and signal visualization
- **Performance Analytics**: Win rate, total trades, and profitability metrics
- **System Monitoring**: Real-time logs and system status

### 🔐 Security & Authentication
- **Secure Authentication**: Admin user with password change functionality
- **Session Management**: Secure login/logout with remember me option
- **Production-Ready**: Secure password hashing and session handling

### ⚡ Real-time Monitoring
- **TP/SL Monitor**: Automatic take profit and stop loss execution (10-second intervals)
- **Order Tracking**: Real-time order status updates and position management
- **Signal Generation**: Continuous market analysis and signal generation (30-second intervals)

## Installation

### Prerequisites
- Python 3.8 or higher
- Crypto.com Exchange account (for live trading)
- Optional: Virtual environment (recommended)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd crypto-trading-webapp
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv crypto_env
   source crypto_env/bin/activate  # On Windows: crypto_env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///crypto_trading.db
   
   # Crypto.com API credentials (optional for live trading)
   CRYPTO_API_KEY=your-api-key
   CRYPTO_API_SECRET=your-api-secret
   SANDBOX_MODE=True
   
   # Trading parameters
   DEFAULT_TRADE_AMOUNT=10.0
   RSI_OVERSOLD=30
   RSI_OVERBOUGHT=70
   ATR_MULTIPLIER=2.0
   VOLUME_THRESHOLD=1.5
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and navigate to `http://localhost:5000`

## Default Login Credentials

- **Username**: `admin`
- **Password**: `1234`

> ⚠️ **Important**: Change the default password immediately after first login through the settings page.

## Application Architecture

### Database Models
- **User**: Authentication and user management
- **Coin**: Cryptocurrency tracking and configuration
- **TechnicalAnalysis**: Technical indicator data and signals
- **Order**: Order tracking and management
- **Position**: Position tracking with P&L calculation
- **Trade**: Executed trade history
- **SystemLog**: Application logging and monitoring

### Core Services
- **TechnicalAnalysisService**: Calculates RSI, MA, EMA, ATR and generates signals
- **CryptoExchangeAPI**: Handles all exchange operations (orders, balances, prices)
- **TradingMonitor**: Background service for continuous market analysis
- **TpSlMonitor**: Real-time TP/SL monitoring and execution

### API Endpoints
- `/dashboard/api/overview` - Portfolio overview data
- `/dashboard/api/signals` - Latest trading signals
- `/dashboard/api/positions` - Open positions
- `/dashboard/api/orders` - Order management
- `/trading/api/coin-price/<id>` - Real-time price data
- `/trading/api/analyze-coin/<id>` - Trigger manual analysis

## Trading Algorithm

### Buy Signal Conditions
The system generates BUY signals when any of these conditions are met:

1. **Standard Condition**: RSI < 40 AND at least 2 moving averages are valid
2. **Oversold Condition**: RSI < 30 AND at least 1 moving average is valid  
3. **High Volume Condition**: RSI < 45 AND at least 1 moving average is valid AND volume ratio ≥ 1.5x

### Moving Average Validation
- **MA200**: Price > 200-period moving average
- **MA50**: Price > 50-period moving average  
- **EMA10**: Price > 10-period exponential moving average

### Risk Management
- **ATR-based Stop Loss**: Entry price - (ATR × multiplier)
- **ATR-based Take Profit**: Entry price + (ATR × multiplier)
- **Support/Resistance**: Integrated with technical levels
- **Position Sizing**: Configurable trade amounts and risk percentages

## Configuration

### Trading Parameters
- **Analysis Interval**: 30 seconds (configurable)
- **TP/SL Check Interval**: 10 seconds
- **RSI Period**: 14
- **ATR Period**: 14
- **ATR Multiplier**: 2.0
- **Volume Threshold**: 1.5x average

### Exchange Settings
- **Sandbox Mode**: Enable for testing without real trades
- **API Rate Limiting**: Built-in rate limiting to prevent API abuse
- **Error Handling**: Comprehensive error handling with retry mechanisms

## Usage

### Adding Coins for Tracking
1. Navigate to **Trading → Coin Management**
2. Click **"Add New Coin"**
3. Enter the coin symbol (e.g., BTC, ETH)
4. The system will validate the symbol on the exchange
5. Coin will be added and analysis will begin automatically

### Manual Trading
1. Navigate to **Trading → Manual Order**
2. Select coin, order type (Market/Limit), and quantity
3. Set price if using limit orders
4. Review and place order

### Monitoring Positions
1. Navigate to **Positions** to view all open positions
2. Monitor real-time P&L and price updates
3. View TP/SL levels and position status
4. Access detailed position history

### Performance Analytics
1. Navigate to **Analytics** for detailed performance metrics
2. View win rate, total trades, and profitability
3. Analyze performance over different time periods
4. Export data for external analysis

## Security Considerations

### Production Deployment
- Change default admin password immediately
- Use strong SECRET_KEY in production
- Configure HTTPS/SSL for web server
- Use secure database (PostgreSQL/MySQL) instead of SQLite
- Regularly backup database and logs
- Monitor system logs for security events

### API Security
- Store API credentials securely
- Use environment variables for sensitive data
- Enable IP whitelisting on exchange if available
- Monitor API usage and limits
- Use sandbox mode for testing

## Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Verify API credentials in .env file
   - Check internet connection
   - Verify exchange API status
   - Review rate limiting settings

2. **Database Errors**
   - Check database file permissions
   - Verify SQLAlchemy connection string
   - Review database logs for errors

3. **Missing Price Data**
   - Verify coin symbols are correct
   - Check exchange instrument availability
   - Review API response logs

4. **Signal Generation Issues**
   - Ensure sufficient historical data (200+ candles)
   - Verify technical indicator calculations
   - Check coin activation status

### Logs and Monitoring
- Application logs: `trading_bot.log`
- System logs: Available in the web interface
- Database logs: Check SQLAlchemy output
- API logs: Integrated in system logs

## Development

### Adding New Features
1. **New Technical Indicators**: Extend `TechnicalAnalysisService`
2. **Additional Exchanges**: Create new exchange API classes
3. **Custom Strategies**: Modify signal generation logic
4. **Enhanced UI**: Add new templates and static files

### Testing
1. Use sandbox mode for exchange testing
2. Test with small trade amounts
3. Monitor logs for errors
4. Verify calculations manually

## Support

For issues, feature requests, or questions:
1. Check the logs for error details
2. Verify configuration settings
3. Review this documentation
4. Check exchange API documentation

## License

This project is for educational and personal use. Please ensure compliance with your local financial regulations when trading cryptocurrencies.

---

**⚠️ Disclaimer**: Cryptocurrency trading involves substantial risk. This software is provided as-is without warranties. Users are responsible for their own trading decisions and should never trade with money they cannot afford to lose. 