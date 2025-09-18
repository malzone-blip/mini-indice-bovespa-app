import streamlit as st
import requests
import pandas as pd
import numpy as np

ALPHA_VANTAGE_KEY = 'KTZQVSJK1BOZOAJT'  
BRAPI_TOKEN = '7LYDUnPwyJuUoNs5uzEjha'  
FINNHUB_TOKEN = 'd365ct9r01qumnp48d40d365ct9r01qumnp48d4g'  
TWELVE_DATA_TOKEN = '617057b083344783a89ef1e7b5538734'  

def get_data_alpha_vantage(symbol):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}'
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        if 'Time Series (Daily)' in data:
            ts = data['Time Series (Daily)']
            df = pd.DataFrame.from_dict(ts, orient='index')
            df = df.rename(columns={
                '1. open': 'open',
                '2. high': 'high',
                '3. low': 'low',
                '4. close': 'close',
                '5. volume': 'volume'
            })
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            df = df.astype(float)
            df.reset_index(inplace=True)
            df = df.rename(columns={'index': 'date'})
            return df[['date', 'close', 'open', 'high', 'low', 'volume']]
    return None

def get_data_brapi(symbol):
    url = f'https://brapi.dev/api/stock/{symbol}/chart/1m?token={BRAPI_TOKEN}'
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            if 'close' in df.columns and 'date' in df.columns:
                df['close'] = pd.to_numeric(df['close'], errors='coerce')
                df['date'] = pd.to_datetime(df['date'])
                df = df.dropna(subset=['close'])
                df = df.reset_index(drop=True)
                return df
        elif 'results' in data and len(data['results']) > 0:
            df = pd.DataFrame(data['results'])
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['date'] = pd.to_datetime(df['date'])
            df = df.dropna(subset=['close'])
            df = df.reset_index(drop=True)
            return df
    return None

def get_data_finnhub(symbol):
    url = f'https://finnhub.io/api/v1/stock/candle?symbol={symbol}&resolution=D&count=100&token={FINNHUB_TOKEN}'
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        if data.get('s') == 'ok':
            df = pd.DataFrame({
                'date': pd.to_datetime(data['t'], unit='s'),
                'close': data['c'],
                'open': data['o'],
                'high': data['h'],
                'low': data['l'],
                'volume': data['v']
            })
            return df
    return None

def get_data_twelvedata(symbol):
    url = f'https://api.twelvedata.com/time_series?symbol={symbol}&interval=1day&apikey={TWELVE_DATA_TOKEN}&format=json'
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        if 'values' in data:
            df = pd.DataFrame(data['values'])
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['open'] = pd.to_numeric(df['open'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            df['date'] = pd.to_datetime(df['datetime'])
            df = df.drop(columns=['datetime'])
            df = df.sort_values('date').reset_index(drop=True)
            return df
    return None

def calculate_indicators(df):
    if df is not None and not df.empty:
        df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['RSI14'] = 100 - (100 / (1 + rs))
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['STD20'] = df['close'].rolling(window=20).std()
        df['UpperBB'] = df['MA20'] + 2 * df['STD20']
        df['LowerBB'] = df['MA20'] - 2 * df['STD20']
    return df

def generate_trade_signals(df, profit_target=0.05, stop_loss=0.02):
    signals = []
    position = None
    entry_price = 0
    for i in range(len(df)):
        if i == 0:
            signals.append('HOLD')
            continue
        buy_cond = (df['EMA9'].iloc[i] > df['EMA21'].iloc[i]) and \
                   (df['EMA9'].iloc[i-1] <= df['EMA21'].iloc[i-1]) and \
                   (df['RSI14'].iloc[i] < 70) and \
                   (df['close'].iloc[i] < df['UpperBB'].iloc[i])
        sell_cond = (position == 'long' and (
            (df['close'].iloc[i] >= entry_price * (1 + profit_target)) or
            (df['close'].iloc[i] <= entry_price * (1 - stop_loss)) or
            (df['EMA9'].iloc[i] < df['EMA21'].iloc[i]) or
            (df['RSI14'].iloc[i] > 70) or
            (df['close'].iloc[i] > df['UpperBB'].iloc[i])
        ))
        if position == 'long':
            if sell_cond:
                signals.append('SELL')
                position = None
                entry_price = 0
            else:
                signals.append('HOLD')
        else:
            if buy_cond:
                signals.append('BUY')
                position = 'long'
                entry_price = df['close'].iloc[i]
            else:
                signals.append('HOLD')
    df['Signal'] = signals
    return df

def main():
    st.title('Monitoramento Mini Índice Bovespa - Escolha a API para buscar dados')
    
    symbol = st.text_input('Símbolo (ex: PETR4.SA)', 'PETR4.SA').upper()
    
    api_options = {
        'Alpha Vantage': get_data_alpha_vantage,
        'BRAPI': get_data_brapi,
        'Finnhub': get_data_finnhub,
        'Twelve Data': get_data_twelvedata
    }
    
    selected_api = st.selectbox('Selecione a API para buscar os dados:', list(api_options.keys()))
    
    if st.button('Atualizar Dados e Sinais'):
        with st.spinner(f'Buscando dados na API {selected_api}...'):
            df = api_options[selected_api](symbol)
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                df = generate_trade_signals(df)
                st.subheader(f'Dados e sinais para {symbol} via {selected_api}')
                st.dataframe(df[['date', 'close', 'EMA9', 'EMA21', 'RSI14', 'UpperBB', 'LowerBB', 'Signal']].tail(20))
                st.markdown("""
                **Legenda:**  
                - `date`: Data da cotação.  
                - `close`: Preço de fechamento.  
                - `EMA9`: Média móvel exponencial 9 períodos.  
                - `EMA21`: Média móvel exponencial 21 períodos.  
                - `RSI14`: Índice de força relativa 14 períodos.  
                - `UpperBB`: Banda superior de Bollinger.  
                - `LowerBB`: Banda inferior de Bollinger.  
                - `Signal`: Sinal da operação (BUY, SELL, HOLD).
                """)
            else:
                st.error(f'Não foi possível obter dados da API {selected_api} para o símbolo {symbol}.')

if __name__ == '__main__':
    main()
