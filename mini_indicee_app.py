import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime

BRAPI_TOKEN = '7LYDUnPwyJuUoNs5uzEjha'  # Seu token BRAPI incluído aqui

def get_historical_data(symbol='PETR4', range_days='7d'):
    url = f'https://brapi.dev/api/quote/{symbol}?range={range_days}&token={BRAPI_TOKEN}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'results' in data and len(data['results']) > 0:
            df = pd.DataFrame(data['results'])
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['date'] = pd.to_datetime(df['date'])
            df = df.dropna(subset=['close'])
            df = df.reset_index(drop=True)
            return df
    st.error('Erro ao obter dados da API BRAPI ou dados insuficientes.')
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

        df['Volume'] = np.nan  # Volume não fornecido pela BRAPI gratuitamente
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
                   (df['EMA9'].iloc[i - 1] <= df['EMA21'].iloc[i - 1]) and \
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
    st.title('Monitoramento Mini Índice Bovespa (via BRAPI) - Sinais Automáticos')
    st.write('Configure o símbolo e período para atualizar os sinais e gráficos.')

    symbol = st.text_input('Símbolo (ex: PETR4, VALE3)', value='PETR4').upper()
    range_days = st.selectbox('Período (range do histórico)', options=['7d', '1m', '3m', '6m'], index=0)

    if st.button('Atualizar Dados e Sinais'):
        with st.spinner('Consultando API BRAPI e processando dados...'):
            df = get_historical_data(symbol=symbol, range_days=range_days)
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                df = generate_trade_signals(df)

                st.subheader(f'Últimos valores e sinais para {symbol}')
                st.dataframe(df[['date', 'close', 'EMA9', 'EMA21', 'RSI14', 'UpperBB', 'LowerBB', 'Signal']].tail(20))

                st.subheader('Gráfico Preço + Indicadores')
                st.line_chart(df.set_index('date')[['close', 'EMA9', 'EMA21']])
                st.line_chart(df.set_index('date')[['UpperBB', 'LowerBB']])

                signals_buy = df[df['Signal'] == 'BUY']
                signals_sell = df[df['Signal'] == 'SELL']

                st.subheader('Sinais de Compra')
                for idx in signals_buy.index:
                    st.write(f"Data: {df.loc[idx, 'date'].date()}, Preço: {df.loc[idx, 'close']}")

                st.subheader('Sinais de Venda')
                for idx in signals_sell.index:
                    st.write(f"Data: {df.loc[idx, 'date'].date()}, Preço: {df.loc[idx, 'close']}")
            else:
                st.error('Não foi possível obter dados para análise.')

if __name__ == "__main__":
    main()
