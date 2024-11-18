import streamlit as st
import plotly.graph_objects as go
import yfinance as yf 
from datetime import datetime, timedelta
import ta


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
    try:
        # Use .item() to properly convert pandas Series to native Python numbers
        last_close = data['Close'].iloc[-1].item()
        prev_close = data['Close'].iloc[0].item()
        change = last_close - prev_close
        pct_change = (change / prev_close) * 100
        
        # Use .item() for aggregation results
        high = data['High'].max().item()
        low = data['Low'].min().item()
        volume = data['Volume'].sum().item()
        avg_volume = data['Volume'].mean().item()
        
        # Return values (already native Python numbers)
        return last_close, change, pct_change, high, low, volume, avg_volume
    except Exception as e:
        st.error(f"Error in calculate_metric: {str(e)}")
        # Return default values in case of error
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

def add_technical_indicators(data):
    # Ensure Close price is a 1D series by squeezing any extra dimensions
    close_series = data['Close'].squeeze()
    close_series = close_series.ffill()
    
    # Moving averages
    data['SMA_20'] = ta.trend.sma_indicator(close_series, window=20)
    data['EMA_20'] = ta.trend.ema_indicator(close_series, window=20)
    
    # RSI
    data['RSI'] = ta.momentum.rsi(close_series, window=14)
    
    # MACD
    macd = ta.trend.MACD(close_series)
    data['MACD'] = macd.macd()
    data['MACD_Signal'] = macd.macd_signal()
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close_series)
    data['BB_Upper'] = bb.bollinger_hband()
    data['BB_Lower'] = bb.bollinger_lband()
    data['BB_Middle'] = bb.bollinger_mavg()
    
    return data

def plot_volume_chart(data):
    try:
        # Ensure 'Datetime' is in the correct format
        if 'Datetime' not in data.columns:
            st.error("Error: 'Datetime' column is missing in data.")
            return None
        
        # Create the volume bar chart
        volume_fig = go.Figure()
        volume_fig.add_trace(go.Bar(
            x=data['Datetime'], 
            y=data['Volume'], 
            name='Volume',
            marker_color='blue'  # Color customization
        ))
        
        # Update layout for better appearance
        volume_fig.update_layout(
            title=dict(
                text='Trading Volume',
                x=0.5,  # Center-align title
                font=dict(size=16)
            ),
            xaxis_title='Time',
            yaxis_title='Volume',
            height=400,  # Slightly increase height for better visibility
            margin=dict(l=50, r=50, t=50, b=50),
            template='plotly_dark',  # Add a consistent theme
            xaxis=dict(
                showgrid=True, 
                gridcolor='rgba(128,128,128,0.2)'  # Subtle gridlines
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='rgba(128,128,128,0.2)'  # Subtle gridlines
            )
        )
        return volume_fig
    except Exception as e:
        st.error(f"Error in plot_volume_chart: {str(e)}")
        return None

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
            col1.metric(
                label=f"{ticker} Last Price", 
                value=f"{last_close:,.2f} USD", 
                delta=f"{change:,.2f} ({pct_change:.2f}%)"
            )
            col2.metric(
                "Day's Range", 
                f"{low:,.2f} - {high:,.2f} USD"
            )
            col3.metric(
                "Volume", 
                f"{int(volume):,}", 
                delta=f"{((volume/avg_volume)-1)*100:.1f}% vs avg"
            )

            # Create tabs for different charts
            tab1, tab2= st.tabs(["Price Chart", "Technical Analysis"])
            
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
                        name='Price',
                        increasing_line_color='#26A69A',    # Green color for increasing
                        decreasing_line_color='#EF5350',    # Red color for decreasing
                        line=dict(width=1)                  # Adjust candlestick visibility
                    ))
                elif chart_type == 'Line':
                    fig.add_trace(go.Scatter(
                        x=data['Datetime'],
                        y=data['Close'],
                        mode='lines',
                        name='Price',
                        line=dict(color='#2962FF', width=1),
                        showlegend=True
                    ))

                # Add selected technical indicators with specific colors
                if 'SMA 20' in indicators:
                    fig.add_trace(go.Scatter(
                        x=data['Datetime'], 
                        y=data['SMA_20'],
                        name='SMA 20',
                        line=dict(color='#ADA930', width=1.5),  # Updated color for better distinction
                        showlegend=True
                    ))
                if 'EMA 20' in indicators:
                    fig.add_trace(go.Scatter(
                        x=data['Datetime'], 
                        y=data['EMA_20'],
                        name='EMA 20',
                        line=dict(color='#FF6D00', width=1.5),
                        showlegend=True
                    ))
                if 'Bollinger Bands' in indicators:
                    fig.add_trace(go.Scatter(
                        x=data['Datetime'],
                        y=data['BB_Upper'],
                        name='BB Upper',
                        line=dict(color='#FF5733', width=1.5),
                        showlegend=True
                    ))
                    fig.add_trace(go.Scatter(
                        x=data['Datetime'],
                        y=data['BB_Lower'],
                        name='BB_Lower',
                        line=dict(color='#33CFFF', width=1.5),
                    ))
                    fig.add_trace(go.Scatter(
                        x=data['Datetime'],
                        y=data['BB_Middle'],
                        name='BB_Middle',
                        line=dict(color='#FFC300', width=1.5),
                        showlegend=True
                    ))

                # Update layout with improved visibility settings
                fig.update_layout(
                    title=f'{ticker} {time_period.upper()} Chart',
                    xaxis_title='Time',
                    yaxis_title='Price (USD)',
                    height=600,
                    template='plotly_dark',
                    plot_bgcolor='black',           # Set black background
                    paper_bgcolor='black',
                    showlegend=True,
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="right",
                        x=0.99,
                        bgcolor="rgba(0,0,0,0.5)",
                        font=dict(color="white")
                    ),
                    xaxis=dict(
                        gridcolor='rgba(128,128,128,0.2)',
                        showgrid=True,
                        linecolor='rgba(128,128,128,0.2)',
                        rangeslider=dict(visible=True)  # Add range slider for candlestick
                    ),
                    yaxis=dict(
                        gridcolor='rgba(128,128,128,0.2)',
                        showgrid=True,
                        linecolor='rgba(128,128,128,0.2)',
                        side='right'               # Move price axis to right side
                    ),
                    margin=dict(l=50, r=50, t=50, b=50),
                    hoverdistance=100,            # Make hover more sensitive
                    spikedistance=100,           
                    hovermode='x unified'         # Show all hover info together
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
st.sidebar.info("This dashboard provides stock data and technical indicators for various time periods")