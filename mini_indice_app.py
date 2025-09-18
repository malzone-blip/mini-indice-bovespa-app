import streamlit as st
import requests
import pandas as pd
import numpy as np

ALPHA_VANTAGE_KEY = 'KTZQVSJK1BOZOAJT'  # Sua API Key Alpha Vantage

def get_historical_data(symbol='PETR4.SA'):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHA_VANTAGE_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
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
        else:
            st.error("Erro: Resposta inválida da API Alpha Vantage")
            return None
    else:
        st.error(f"Erro HTTP {response.status_code} na requisição Alpha Vantage")
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
    st.title('Monitoramento Mini Índice Bovespa (via Alpha Vantage) - Sinais Automáticos')
    st.write('Informe o símbolo (ex: PETR4.SA) para obter sinais e gráficos')

    symbol = st.text_input('Símbolo', value='PETR4.SA').upper()

    if st.button('Atualizar Dados e Sinais'):
        with st.spinner('Consultando Alpha Vantage e processando...'):
            df = get_historical_data(symbol)
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                df = generate_trade_signals(df)

                st.subheader(f'Últimos dados e sinais para {symbol}')
                st.dataframe(df[['date', 'close', 'EMA9', 'EMA21', 'RSI14', 'UpperBB', 'LowerBB', 'Signal']].tail(20))

                st.subheader('Gráficos')
                st.line_chart(df.set_index('date')[['close', 'EMA9', 'EMA21']])
                st.line_chart(df.set_index('date')[['UpperBB', 'LowerBB']])

                sinais_compra = df[df['Signal'] == 'BUY']
                sinais_venda = df[df['Signal'] == 'SELL']

                if not sinais_compra.empty:
                    st.success(f'Sinal de COMPRA em {sinais_compra.iloc[-1]["date"]} preço {sinais_compra.iloc[-1]["close"]:.2f}')
                if not sinais_venda.empty:
                    st.warning(f'Sinal de VENDA em {sinais_venda.iloc[-1]["date"]} preço {sinais_venda.iloc[-1]["close"]:.2f}')
            else:
                st.error('Nenhum dado disponível para o símbolo informado.')

if __name__ == '__main__':
    main()
