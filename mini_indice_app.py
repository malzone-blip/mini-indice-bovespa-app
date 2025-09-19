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
