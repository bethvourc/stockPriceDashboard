import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd 
import yfinance as yf 
from datetime import datetime, timedelta
import pytz
import ta
import numpy as np

def fetch_stock_data(ticker, period, interval):
    end_date = datetime.now()
    if period == '1wk':
        start_date = end_date - timedelta(days=7)
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval)
    else:
        data = yf.download(ticker, period=period, interval=interval)
    return data

def process_data(data):
    if data.index.tzinfo is None:
        data.index = data.index.tz_localize('UTC')
    data.index = data.index.tz_convert('US/Eastern')
    data.reset_index(inplace=True)
    data.rename(columns={'Date': 'Datetime'}, inplace=True)
    return data

def calculate_metric(data):
    last_close = data['Close'].iloc[-1]
    prev_close = data['Close'].iloc[0]
    change = last_close - prev_close
    pct_change = (change / prev_close) * 100
    high = data['High'].max()
    low = data['Low'].min()
    volume = data['Volume'].sum()
    avg_volume = data['Volume'].mean()
    return last_close, change, pct_change, high, low, volume, avg_volume

def add_technical_indicators(data):
    data['Close'] = data['Close'].ffill()  # Changed from fillna(method='ffill')
    
    # Moving averages
    data['SMA_20'] = ta.trend.sma_indicator(data['Close'], window=20)
    data['EMA_20'] = ta.trend.ema_indicator(data['Close'], window=20)
    
    # Rest of the function remains the same
    data['RSI'] = ta.momentum.rsi(data['Close'], window=14)
    
    macd = ta.trend.MACD(data['Close'])
    data['MACD'] = macd.macd()
    data['MACD_Signal'] = macd.macd_signal()
    
    bb = ta.volatility.BollingerBands(data['Close'])
    data['BB_Upper'] = bb.bollinger_hband()
    data['BB_Lower'] = bb.bollinger_lband()
    data['BB_Middle'] = bb.bollinger_mavg()
    
    return data

def plot_volume_chart(data):
    volume_fig = go.Figure()
    volume_fig.add_trace(go.Bar(x=data['Datetime'], y=data['Volume'], name='Volume'))
    volume_fig.update_layout(
        title='Trading Volume',
        xaxis_title='Time',
        yaxis_title='Volume',
        height=300
    )
    return volume_fig

# Set up Streamlit page layout
st.set_page_config(layout='wide')
st.title("Stock Dashboard")

# Sidebar for user input parameters
st.sidebar.header('Chart Parameters')
ticker = st.sidebar.text_input('Ticker', 'ADBE')
time_period = st.sidebar.selectbox('Time Period', ['1d', '1wk', '1mo', '1y', 'max'])
chart_type = st.sidebar.selectbox('Chart Type', ['Candlestick', 'Line'])
indicators = st.sidebar.multiselect('Technical Indicators', 
    ['SMA 20', 'EMA 20', 'Bollinger Bands', 'RSI', 'MACD'])

# Mapping of time periods to data intervals
interval_mapping = {
    '1d': '1m',
    '1wk': '30m',
    '1mo': '1d',
    '1y': '1wk',
    'max': '1wk'
}

# Update the dashboard based on user input
if st.sidebar.button('Update'):
    try:
        data = fetch_stock_data(ticker, time_period, interval_mapping[time_period])
        if data.empty:
            st.error(f"No data found for ticker {ticker}")
        else:
            data = process_data(data)
            data = add_technical_indicators(data)

            last_close, change, pct_change, high, low, volume, avg_volume = calculate_metric(data)

            # Display main metrics in two rows
            col1, col2, col3 = st.columns(3)
            col1.metric(label=f"{ticker} Last Price", 
                       value=f"{last_close:.2f} USD", 
                       delta=f"{change:.2f} ({pct_change:.2f}%)")
            col2.metric("Day's Range", f"{low:.2f} - {high:.2f} USD")
            col3.metric("Volume", f"{volume:,.0f}", 
                       delta=f"{((volume/avg_volume)-1)*100:.1f}% vs avg")

            # Create tabs for different charts
            tab1, tab2, tab3 = st.tabs(["Price Chart", "Technical Analysis", "Volume"])
            
            with tab1:
                # Main price chart
                fig = go.Figure()
                if chart_type == 'Candlestick':
                    fig.add_trace(go.Candlestick(
                        x=data['Datetime'],
                        open=data['Open'],
                        high=data['High'],
                        low=data['Low'],
                        close=data['Close'],
                        name='Price'
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=data['Datetime'],
                        y=data['Close'],
                        mode='lines',
                        name='Price'
                    ))

                # Add selected technical indicators
                if 'Bollinger Bands' in indicators:
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['BB_Upper'], 
                                           name='BB Upper', line=dict(dash='dash')))
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['BB_Lower'], 
                                           name='BB Lower', line=dict(dash='dash')))
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['BB_Middle'], 
                                           name='BB Middle', line=dict(dash='dot')))

                if 'SMA 20' in indicators:
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['SMA_20'], 
                                           name='SMA 20'))
                if 'EMA 20' in indicators:
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['EMA_20'], 
                                           name='EMA 20'))

                fig.update_layout(
                    title=f'{ticker} {time_period.upper()} Chart',
                    xaxis_title='Time',
                    yaxis_title='Price (USD)',
                    height=600
                )
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                if 'RSI' in indicators:
                    rsi_fig = go.Figure()
                    rsi_fig.add_trace(go.Scatter(x=data['Datetime'], y=data['RSI'], 
                                               name='RSI'))
                    rsi_fig.add_hline(y=70, line_dash="dash", line_color="red")
                    rsi_fig.add_hline(y=30, line_dash="dash", line_color="green")
                    rsi_fig.update_layout(
                        title='Relative Strength Index (RSI)',
                        yaxis_title='RSI',
                        height=300
                    )
                    st.plotly_chart(rsi_fig, use_container_width=True)

                if 'MACD' in indicators:
                    macd_fig = go.Figure()
                    macd_fig.add_trace(go.Scatter(x=data['Datetime'], y=data['MACD'], 
                                                name='MACD'))
                    macd_fig.add_trace(go.Scatter(x=data['Datetime'], y=data['MACD_Signal'], 
                                                name='Signal'))
                    macd_fig.update_layout(
                        title='MACD',
                        yaxis_title='Value',
                        height=300
                    )
                    st.plotly_chart(macd_fig, use_container_width=True)

            with tab3:
                st.plotly_chart(plot_volume_chart(data), use_container_width=True)

            # Display data tables with toggles
            if st.checkbox('Show Historical Data'):
                st.dataframe(data[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']])

            if st.checkbox('Show Technical Indicators'):
                technical_cols = ['Datetime']
                if 'SMA 20' in indicators: technical_cols.append('SMA_20')
                if 'EMA 20' in indicators: technical_cols.append('EMA_20')
                if 'RSI' in indicators: technical_cols.append('RSI')
                if 'MACD' in indicators: 
                    technical_cols.extend(['MACD', 'MACD_Signal'])
                if 'Bollinger Bands' in indicators:
                    technical_cols.extend(['BB_Upper', 'BB_Middle', 'BB_Lower'])
                
                st.dataframe(data[technical_cols])

    except Exception as e:
        st.error(f"Error occurred: {str(e)}")

# Sidebar watchlist
st.sidebar.header('Real-Time Stock Price')
stock_symbols = ['AAPL', 'GOOGL', 'AMZN', 'MSFT']
for symbol in stock_symbols:
    real_time_data = fetch_stock_data(symbol, '1d', '1m')
    if not real_time_data.empty:
        real_time_data = process_data(real_time_data)
        last_price = real_time_data['Close'].iloc[-1].item()
        open_price = real_time_data['Open'].iloc[0].item()
        change = last_price - open_price
        pct_change = (change / open_price) * 100
        st.sidebar.metric(f"{symbol}", f"{last_price:.2f} USD", f"{change:.2f} ({pct_change:.2f}%)")

# Sidebar information
st.sidebar.info("This dashboard provides: Real-time stock data, Technical indicators, Custom watchlist and Interactive charts")