import streamlit as st
import requests
import pandas as pd
import numpy as np

BRAPI_TOKEN = '7LYDUnPwyJuUoNs5uzEjha'  # Seu token BRAPI

def get_historical_data(symbol='PETR4', range_days='7d'):
    url = f'https://brapi.dev/api/stock/{symbol}/chart/{range_days}?token={BRAPI_TOKEN}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        st.write("Dados brutos da API BRAPI (histórico):", data)  # debug
        # Alguns endpoints retornam os dados direto como lista
        if 'results' in data and len(data['results']) > 0:
            df = pd.DataFrame(data['results'])
        elif isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame()
        if not df.empty:
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

        df['Volume'] = np.nan  # Volume pode estar indisponível na API BRAPI
    return df

def generate_trade_signals(df, profit_target=0.05, stop_loss=0.02):
    signals = []
    position = None
    entry_price = 0

    for i in range(len(df)):
        if i == 0:
            signals.append('HOLD')
            continue

        # Estratégia simples:
        # Compra quando EMA9 cruza acima EMA21, RSI < 70 e preço abaixo UpperBB
        buy_cond = (df['EMA9'].iloc[i] > df['EMA21'].iloc[i]) and \
                   (df['EMA9'].iloc[i - 1] <= df['EMA21'].iloc[i - 1]) and \
                   (df['RSI14'].iloc[i] < 70) and \
                   (df['close'].iloc[i] < df['UpperBB'].iloc[i])

        # Venda se preço alcançar lucro, stop ou indicadores mudarem
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
    st.write('Configure símbolo e período para exibir análise com sinais e gráficos.')

    symbol = st.text_input('Símbolo (ex: PETR4, VALE3)', value='PETR4').upper()
    range_days = st.selectbox('Período', ['7d', '1m', '3m', '6m'], index=0)

    if st.button('Atualizar Dados e Sinais'):
        with st.spinner('Obtendo dados e processando indicadores...'):
            df = get_historical_data(symbol=symbol, range_days=range_days)
            if df is not None and not df.empty:
                df = calculate_indicators(df)
                df = generate_trade_signals(df)

                st.subheader(f'Últimos dados e sinais para {symbol}')
                st.dataframe(df[['date', 'close', 'EMA9', 'EMA21', 'RSI14', 'UpperBB', 'LowerBB', 'Signal']].tail(20))

                st.subheader('Gráficos')
                st.line_chart(df.set_index('date')[['close', 'EMA9', 'EMA21']])
                st.line_chart(df.set_index('date')[['UpperBB', 'LowerBB']])

                # Alertas simples
                sinais_compras = df[df['Signal'] == 'BUY']
                sinais_vendas = df[df['Signal'] == 'SELL']

                if not sinais_compras.empty:
                    st.success(f"Sinal de COMPRA detectado em {sinais_compras.iloc[-1]['date'].date()} preço {sinais_compras.iloc[-1]['close']:.2f}")
                if not sinais_vendas.empty:
                    st.warning(f"Sinal de VENDA detectado em {sinais_vendas.iloc[-1]['date'].date()} preço {sinais_vendas.iloc[-1]['close']:.2f}")

            else:
                st.error('Dados insuficientes para análise.')

if __name__ == '__main__':
    main()
