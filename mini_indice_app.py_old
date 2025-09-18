Aqui está o código completo do sistema para monitoramento e geração automática de sinais do mini índice Bovespa com interface Streamlit. Basta copiar todo o código abaixo, salvar num arquivo chamado `mini_indice_app.py`, substituir `'SEU_TOKEN_AQUI'` pelo seu token da API IbovFinancials, e seguir o roteiro de instalação e execução no Windows que enviei anteriormente.

```python
import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Coloque aqui seu token da API IbovFinancials
API_TOKEN = 'SEU_TOKEN_AQUI'  # Substitua pelo seu token real
BASE_URL = 'http://www.ibovfinancials.com/api/ibov'


def get_historical_data(symbol='WINV25', timeframe=5, days=7):
    url = f'{BASE_URL}/historical/'
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    params = {
        'symbol': symbol,
        'timeframe': timeframe,
        'start_date': start_date,
        'end_date': end_date,
        'token': API_TOKEN
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if 'data' in data and len(data['data']) > 0:
            df = pd.DataFrame(data['data'])
            df['close'] = pd.to_numeric(df['close'])
            return df
    st.error('Erro ao obter dados da API ou dados insuficientes.')
    return None


def calculate_indicators(df):
    if df is not None:
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

        if 'volume' in df.columns:
            df['Volume'] = pd.to_numeric(df['volume'])
        else:
            df['Volume'] = np.nan

    return df


def generate_trade_signals(df, profit_target=0.05, stop_loss=0.02):
    signals = []
    position = None
    entry_price = 0

    for i in range(len(df)):
        if i == 0:
            signals.append('HOLD')
            continue

        buy_cond = (df['EMA9'].iloc[i] > df['EMA21'].iloc[i]) and (df['EMA9'].iloc[i - 1] <= df['EMA21'].iloc[i - 1]) and (df['RSI14'].iloc[i] < 70) and (df['close'].iloc[i] < df['UpperBB'].iloc[i])
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
    st.title('Monitoramento Mini Índice Bovespa - Sinais Automáticos')
    st.write('Clique no botão abaixo para atualizar os sinais e gráficos.')

    if st.button('Atualizar Dados e Sinais'):
        with st.spinner('Consultando API e processando dados...'):
            df = get_historical_data()
            if df is not None:
                df = calculate_indicators(df)
                df = generate_trade_signals(df)

                st.subheader('Últimos valores e sinais')
                st.dataframe(df[['close', 'EMA9', 'EMA21', 'RSI14', 'UpperBB', 'LowerBB', 'Signal']].tail(20))

                st.subheader('Gráfico Price + Indicadores')
                st.line_chart(df[['close', 'EMA9', 'EMA21']])
                st.line_chart(df[['UpperBB', 'LowerBB']])

                signals_buy = df[df['Signal'] == 'BUY']
                signals_sell = df[df['Signal'] == 'SELL']

                st.subheader('Sinais de Compra')
                for idx in signals_buy.index:
                    st.write(f"Data/Hora: {df.loc[idx, 'datetime']}, Preço: {df.loc[idx, 'close']}")

                st.subheader('Sinais de Venda')
                for idx in signals_sell.index:
                    st.write(f"Data/Hora: {df.loc[idx, 'datetime']}, Preço: {df.loc[idx, 'close']}")

            else:
                st.error('Não foi possível obter dados para análise.')


if __name__ == "__main__":
    main()
```

***

Se precisar de qualquer ajuda para salvar esse arquivo, instalar o Python, Streamlit ou rodar o sistema, é só avisar!