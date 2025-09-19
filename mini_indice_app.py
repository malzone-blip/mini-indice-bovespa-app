import streamlit as st
import requests
import pandas as pd

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
                "1. open": "open",
                "2. high": "high",
                "3. low": "low",
                "4. close": "close",
                "5. volume": "volume"
            }, inplace=True)
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            df = df.astype(float)
            df.reset_index(inplace=True)
            df.rename(columns={"index": "date"}, inplace=True)
            return df["date"], df["close"], df["open"], df["high"], df["low"], df["volume"]
        else:
            st.error("Resposta da API não contém 'Time Series (Daily)'")
    else:
        st.error(f"Erro HTTP {response.status_code} ao acessar Alpha Vantage")
    return None

def main():
    st.set_page_config(page_title="Monitoramento Alpha Vantage", layout="wide")
    st.title("Monitoramento de Ações com Alpha Vantage")
    symbol = st.text_input("Símbolo (ex: PETR4.SA)", value="PETR4.SA")
    if st.button("Atualizar Dados e Sinais"):
        with st.spinner("Buscando dados e processando..."):
            result = get_historical_data(symbol)
            if result:
                date, close, open_, high, low, volume = result
                df = pd.DataFrame({
                    "Date": date,
                    "Close": close,
                    "Open": open_,
                    "High": high,
                    "Low": low,
                    "Volume": volume
                })
                st.subheader(f"Últimos dados diários para {symbol}")
                st.dataframe(df.tail(20))
            else:
                st.error("Não foi possível obter dados para análise.")

if __name__ == "__main__":
    main()
