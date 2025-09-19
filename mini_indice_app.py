import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
import tempfile

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

    axs[0].plot(df['Data'], df['Fechamento'], label='Fechamento', color='blue')
    axs[0].plot(df['Data'], df['UpperBand'], label='Banda Superior', linestyle='--', color='gray')
    axs[0].plot(df['Data'], df['MiddleBand'], label='Média Móvel 20 dias', linestyle='--', color='orange')
    axs[0].plot(df['Data'], df['LowerBand'], label='Banda Inferior', linestyle='--', color='gray')
    axs[0].fill_between(df['Data'], df['LowerBand'], df['UpperBand'], color='lightgray', alpha=0.3)
    axs[0].set_ylabel('Preço (R$)')
    axs[0].legend()
    axs[0].set_title('Preço Fechamento e Bandas de Bollinger')

    axs[1].plot(df['Data'], df['MACD'], label='MACD', color='blue')
    axs[1].plot(df['Data'], df['Signal'], label='Linha de Sinal', color='red')
    axs[1].axhline(0, color='black', lw=0.5)
    axs[1].set_ylabel('MACD')
    axs[1].legend()
    axs[1].set_title('MACD')

    axs[2].plot(df['Data'], df['RSI'], label='RSI', color='purple')
    axs[2].axhline(70, color='red', linestyle='--')
    axs[2].axhline(30, color='green', linestyle='--')
    axs[2].set_ylabel('RSI')
    axs[2].legend()
    axs[2].set_title('Índice de Força Relativa')

    axs[3].bar(df['Data'], df['Volume'], label='Volume', color='lightblue')
    axs[3].plot(df['Data'], df['Volume_MA20'], label='Média Móvel Volume 20 dias', color='red')
    axs[3].set_ylabel('Volume')
    axs[3].legend()
    axs[3].set_title('Volume e Média Móvel')

    plt.tight_layout()
    st.pyplot(fig)

def generate_pdf(df, alerts, symbol):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Relatório de Análise Técnica - {symbol}", ln=True, align="C")
    pdf.ln(10)

    pdf.cell(0, 10, f"Base histórica utilizada: {df['Data'].iloc[0].strftime('%d/%m/%Y')} até {df['Data'].iloc[-1].strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(5)

    pdf.cell(0, 10, "Alertas Automáticos:", ln=True)
    for alert in alerts:
        pdf.multi_cell(0, 10, f"- {alert}")
    pdf.ln(10)

    pdf.cell(0, 10, "Últimos dados:", ln=True)
    for i, row in df.tail(10).iterrows():
        line = f"{row['Data'].strftime('%d/%m/%Y')}: Open {row['Abertura']:.2f}, High {row['Máxima']:.2f}, Low {row['Mínima']:.2f}, Close {row['Fechamento']:.2f}, Volume {int(row['Volume'])}"
        pdf.multi_cell(0, 10, line)

    # Criar imagens temporárias dos gráficos para PDF
    with tempfile.TemporaryDirectory() as tmpdirname:
        fig, axs = plt.subplots(4, 1, figsize=(6, 8), sharex=True)

        axs[0].plot(df['Data'], df['Fechamento'], label='Fechamento', color='blue')
        axs[0].plot(df['Data'], df['UpperBand'], label='Banda Superior', linestyle='--', color='gray')
        axs[0].plot(df['Data'], df['MiddleBand'], label='Média Móvel 20 dias', linestyle='--', color='orange')
        axs[0].plot(df['Data'], df['LowerBand'], label='Banda Inferior', linestyle='--', color='gray')
        axs[0].fill_between(df['Data'], df['LowerBand'], df['UpperBand'], color='lightgray', alpha=0.3)
        axs[0].set_ylabel('Preço (R$)')
        axs[0].legend()
        axs[0].set_title('Preço Fechamento e Bandas de Bollinger')

        axs[1].plot(df['Data'], df['MACD'], label='MACD', color='blue')
        axs[1].plot(df['Data'], df['Signal'], label='Linha de Sinal', color='red')
        axs[1].axhline(0, color='black', lw=0.5)
        axs[1].set_ylabel('MACD')
        axs[1].legend()
        axs[1].set_title('MACD')

        axs[2].plot(df['Data'], df['RSI'], label='RSI', color='purple')
        axs[2].axhline(70, color='red', linestyle='--')
        axs[2].axhline(30, color='green', linestyle='--')
        axs[2].set_ylabel('RSI')
        axs[2].legend()
        axs[2].set_title('Índice de Força Relativa')

        axs[3].bar(df['Data'], df['Volume'], label='Volume', color='lightblue')
        axs[3].plot(df['Data'], df['Volume_MA20'], label='Média Móvel Volume 20 dias', color='red')
        axs[3].set_ylabel('Volume')
        axs[3].legend()
        axs[3].set_title('Volume e Média Móvel')

        plt.tight_layout()

        graph_path = f"{tmpdirname}/graph.png"
        fig.savefig(graph_path)
        plt.close(fig)

        pdf.add_page()
        pdf.image(graph_path, x=10, y=10, w=190)

    pdf_str = pdf.output(dest='S').encode('latin1')
    return pdf_str

def main():
    st.set_page_config(layout="wide")

    with st.sidebar:
        st.title("Descrição da Aplicação")
        st.markdown("""
        Este app faz análise técnica avançada usando dados históricos diários de ações.

        - **EMA12 e EMA26**: Médias móveis exponenciais que destacam tendências recentes de preço.
        - **MACD**: Indicador que mede a convergência/divergência entre duas EMAs, sinalizando mudanças na força e direção da tendência.
        - **RSI (Índice de Força Relativa)**: Indica potenciais condições de sobrecompra (>70) ou sobrevenda (<30) do ativo.
        - **Bandas de Bollinger**: Faixas de volatilidade que indicam limites de preço, úteis para identificar rompimentos e reversões.
        - **Volume MA20**: Média móvel do volume, ajuda a confirmar a força dos movimentos de preço.
        - **Estocástico (%K e %D)**: Indica reversões potenciais comparando o preço de fechamento com o intervalo de preços recente.

        - Alertas automáticos são gerados para ajudar no timing de compra e venda.
        """)

    st.title("Monitoramento Alpha Vantage - Análise Técnica com Alertas")

    symbol = st.text_input("Símbolo (ex: PETR4.SA)", "PETR4.SA")

    if st.button("Atualizar Dados e Análise"):
        with st.spinner("Buscando dados e calculando indicadores..."):
            df = get_historical_data(symbol)
            if df is not None:
                df = calculate_indicators(df)

                st.markdown(f"**Base histórica utilizada:** {df['Data'].iloc[0].strftime('%d/%m/%Y')} até {df['Data'].iloc[-1].strftime('%d/%m/%Y')}")

                st.subheader("Alertas Automáticos")
                alerts = generate_alerts(df)
                for alert in alerts:
                    st.info(alert)

                # Botão download logo após alertas
                pdf_file = generate_pdf(df, alerts, symbol)
                st.download_button(
                    label="Baixar relatório em PDF",
                    data=pdf_file,
                    file_name=f"analise_{symbol}.pdf",
                    mime="application/pdf"
                )

                st.subheader("Tabela de Dados Recentes")
                st.dataframe(df.tail(20))

                plot_indicators(df, symbol)

    else:
        st.write("Use o botão para atualizar a análise do símbolo informado.")

if __name__ == "__main__":
    main()
