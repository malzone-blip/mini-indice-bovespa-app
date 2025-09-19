import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ALPHAVANTAGEKEY = "KTZQVSJK1BOZOAJT"

def get_historical_data(symbol="PETR4.SA"):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={ALPHAVANTAGEKEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "Time Series (Daily)" in data:
            ts = data["Time Series (Daily)"]
            df = pd.DataFrame.from_dict(ts, orient="index")
            df.rename(columns={
                "1. open": "Abertura",
                "2. high": "Máxima",
                "3. low": "Mínima",
                "4. close": "Fechamento",
                "5. volume": "Volume"
            }, inplace=True)
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            df = df.astype(float)
            df.reset_index(inplace=True)
            df.rename(columns={"index": "Data"}, inplace=True)
            return df
        else:
            st.error("Resposta da API não contém 'Time Series (Daily)'")
    else:
        st.error(f"Erro HTTP {response.status_code} ao acessar Alpha Vantage")
    return None

def calculate_indicators(df):
    df['EMA12'] = df['Fechamento'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Fechamento'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    delta = df['Fechamento'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['MiddleBand'] = df['Fechamento'].rolling(window=20).mean()
    df['UpperBand'] = df['MiddleBand'] + 2 * df['Fechamento'].rolling(window=20).std()
    df['LowerBand'] = df['MiddleBand'] - 2 * df['Fechamento'].rolling(window=20).std()
    
    df['Volume_MA20'] = df['Volume'].rolling(window=20).mean()
    
    low14 = df['Mínima'].rolling(window=14).min()
    high14 = df['Máxima'].rolling(window=14).max()
    df['%K'] = 100 * ((df['Fechamento'] - low14) / (high14 - low14))
    df['%D'] = df['%K'].rolling(window=3).mean()
    
    return df

def generate_alerts(df):
    alerts = []

    if len(df) >= 2:
        macd_now = df['MACD'].iloc[-1]
        signal_now = df['Signal'].iloc[-1]
        macd_prev = df['MACD'].iloc[-2]
        signal_prev = df['Signal'].iloc[-2]

        if macd_prev < signal_prev and macd_now > signal_now:
            alerts.append("Alerta de Compra: MACD cruzou a linha de sinal para cima.")
        elif macd_prev > signal_prev and macd_now < signal_now:
            alerts.append("Alerta de Venda: MACD cruzou a linha de sinal para baixo.")

    rsi_now = df['RSI'].iloc[-1]
    if rsi_now < 30:
        alerts.append("Alerta de Compra: RSI indica sobrevenda (<30).")
    elif rsi_now > 70:
        alerts.append("Alerta de Venda: RSI indica sobrecompra (>70).")

    close_now = df['Fechamento'].iloc[-1]
    upper = df['UpperBand'].iloc[-1]
    lower = df['LowerBand'].iloc[-1]

    if close_now < lower:
        alerts.append("Alerta de Compra: preço fechou abaixo da Banda Inferior de Bollinger.")
    elif close_now > upper:
        alerts.append("Alerta de Venda: preço fechou acima da Banda Superior de Bollinger.")

    if not alerts:
        alerts.append("Sem alertas de compra ou venda no momento.")

    return alerts

def plot_indicators(df, symbol):
    st.subheader(f"Gráficos para {symbol}")
    fig, axs = plt.subplots(4, 1, figsize=(12, 16), sharex=True)

    # Preço e Bandas de Bollinger
    axs[0].plot(df['Data'], df['Fechamento'], label='Fechamento', color='blue')
    axs[0].plot(df['Data'], df['UpperBand'], label='Banda Superior', linestyle='--', color='gray')
    axs[0].plot(df['Data'], df['MiddleBand'], label='Média Móvel 20 dias', linestyle='--', color='orange')
    axs[0].plot(df['Data'], df['LowerBand'], label='Banda Inferior', linestyle='--', color='gray')
    axs[0].fill_between(df['Data'], df['LowerBand'], df['UpperBand'], color='lightgray', alpha=0.3)
    axs[0].set_ylabel('Preço (R$)')
    axs[0].legend()
    axs[0].set_title('Preço Fechamento e Bandas de Bollinger')

    # MACD
    axs[1].plot(df['Data'], df['MACD'], label='MACD', color='blue')
    axs[1].plot(df['Data'], df['Signal'], label='Linha de Sinal', color='red')
    axs[1].axhline(0, color='black', lw=0.5)
    axs[1].set_ylabel('MACD')
    axs[1].legend()
    axs[1].set_title('MACD')

    # RSI
    axs[2].plot(df['Data'], df['RSI'], label='RSI', color='purple')
    axs[2].axhline(70, color='red', linestyle='--')
    axs[2].axhline(30, color='green', linestyle='--')
    axs[2].set_ylabel('RSI')
    axs[2].legend()
    axs[2].set_title('Índice de Força Relativa')

    # Volume com média móvel
    axs[3].bar(df['Data'], df['Volume'], label='Volume', color='lightblue')
    axs[3].plot(df['Data'], df['Volume_MA20'], label='Média Móvel Volume 20 dias', color='red')
    axs[3].set_ylabel('Volume')
    axs[3].legend()
    axs[3].set_title('Volume e Média Móvel')

    plt.tight_layout()
    st.pyplot(fig)

def main():
    st.title("Monitoramento Alpha Vantage - Análise Técnica com Alertas")
    symbol = st.text_input("Símbolo (ex: PETR4.SA)", "PETR4.SA")
    if st.button("Atualizar Dados e Análise"):
        with st.spinner("Buscando dados e calculando indicadores..."):
            df = get_historical_data(symbol)
            if df is not None:
                df = calculate_indicators(df)

                st.subheader("Descrição das Colunas")
                st.markdown("""
                - **Data**: Data do registro diário.
                - **Abertura**: Preço de abertura do dia.
                - **Máxima**: Preço máximo alcançado no dia.
                - **Mínima**: Preço mínimo alcançado no dia.
                - **Fechamento**: Preço de fechamento do dia.
                - **Volume**: Quantidade de ações negociadas no dia.
                - **EMA12, EMA26**: Médias móveis exponenciais de 12 e 26 dias.
                - **MACD, Signal**: Indicador MACD e sua linha de sinal.
                - **RSI**: Índice de Força Relativa, indica sobrecompra (>70) e sobrevenda (<30).
                - **Bandas de Bollinger**: faixa entre Banda Superior e Banda Inferior para medir volatilidade.
                - **Volume_MA20**: Média móvel de 20 dias do volume.
                - **%K, %D**: Indicador Estocástico para detectar eventual reversão.
                """)

                st.subheader("Tabela de Dados Recentes")
                st.dataframe(df.tail(20))

                plot_indicators(df, symbol)

                st.subheader("Alertas Automáticos")
                alerts = generate_alerts(df)
                for alert in alerts:
                    st.info(alert)

if __name__ == "__main__":
    main()
