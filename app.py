import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="글로벌 주식 대시보드", layout="wide")

# ------------------------------------------------------------------
# 주요 글로벌 종목/지수 목록
# ------------------------------------------------------------------
TICKERS = {
    "S&P 500 (미국)": "^GSPC",
    "나스닥 (미국)": "^IXIC",
    "다우존스 (미국)": "^DJI",
    "코스피 (한국)": "^KS11",
    "코스닥 (한국)": "^KQ11",
    "니케이225 (일본)": "^N225",
    "항셍 (홍콩)": "^HSI",
    "상해종합 (중국)": "000001.SS",
    "DAX (독일)": "^GDAXI",
    "FTSE100 (영국)": "^FTSE",
    "CAC40 (프랑스)": "^FCHI",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "NVIDIA": "NVDA",
    "Amazon": "AMZN",
    "Alphabet (Google)": "GOOGL",
    "Tesla": "TSLA",
    "Samsung Electronics": "005930.KS",
    "TSMC": "TSM",
}

PERIOD_OPTIONS = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
    "5년": "5y",
    "10년": "10y",
    "최대": "max",
}

INTERVAL_OPTIONS = {
    "1일": "1d",
    "1주": "1wk",
    "1개월": "1mo",
}

# ------------------------------------------------------------------
# 사이드바 - 사용자 입력
# ------------------------------------------------------------------
st.sidebar.title("📊 대시보드 설정")

selected_names = st.sidebar.multiselect(
    "종목/지수 선택",
    options=list(TICKERS.keys()),
    default=["S&P 500 (미국)", "코스피 (한국)", "나스닥 (미국)", "니케이225 (일본)"],
)

custom_ticker = st.sidebar.text_input(
    "직접 티커 입력 (선택 사항, 쉼표로 구분)", placeholder="예: AAPL, 005930.KS"
)

period_label = st.sidebar.selectbox("기간", list(PERIOD_OPTIONS.keys()), index=3)
interval_label = st.sidebar.selectbox("간격", list(INTERVAL_OPTIONS.keys()), index=0)

chart_type = st.sidebar.radio("차트 종류", ["캔들스틱", "선 그래프"], index=0)
normalize = st.sidebar.checkbox("기준일 대비 변화율(%)로 정규화 비교", value=False)

st.sidebar.markdown("---")
st.sidebar.caption("데이터 출처: Yahoo Finance (yfinance)")

# ------------------------------------------------------------------
# 티커 목록 구성
# ------------------------------------------------------------------
tickers_to_fetch = {name: TICKERS[name] for name in selected_names}

if custom_ticker.strip():
    for t in [x.strip() for x in custom_ticker.split(",") if x.strip()]:
        tickers_to_fetch[t] = t

st.title("🌍 글로벌 주요 주식 대시보드")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if not tickers_to_fetch:
    st.info("왼쪽 사이드바에서 종목을 하나 이상 선택해주세요.")
    st.stop()

# ------------------------------------------------------------------
# 데이터 가져오기
# ------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    return df

data_dict = {}
for name, ticker in tickers_to_fetch.items():
    df = load_data(ticker, PERIOD_OPTIONS[period_label], INTERVAL_OPTIONS[interval_label])
    if not df.empty:
        data_dict[name] = df

if not data_dict:
    st.error("데이터를 불러오지 못했습니다. 티커를 확인해주세요.")
    st.stop()

# ------------------------------------------------------------------
# 요약 지표 (현재가 / 등락률)
# ------------------------------------------------------------------
st.subheader("📌 요약 지표")
cols = st.columns(min(len(data_dict), 5) or 1)

for i, (name, df) in enumerate(data_dict.items()):
    last_price = df["Close"].iloc[-1]
    prev_price = df["Close"].iloc[-2] if len(df) > 1 else last_price
    change = last_price - prev_price
    change_pct = (change / prev_price * 100) if prev_price else 0
    with cols[i % len(cols)]:
        st.metric(
            label=name,
            value=f"{last_price:,.2f}",
            delta=f"{change:,.2f} ({change_pct:+.2f}%)",
        )

st.markdown("---")

# ------------------------------------------------------------------
# 개별 차트 (캔들스틱 or 선 그래프)
# ------------------------------------------------------------------
if not normalize:
    st.subheader("📈 개별 차트")
    for name, df in data_dict.items():
        st.markdown(f"**{name}**")
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.7, 0.3], vertical_spacing=0.05,
        )

        if chart_type == "캔들스틱":
            fig.add_trace(
                go.Candlestick(
                    x=df.index, open=df["Open"], high=df["High"],
                    low=df["Low"], close=df["Close"], name=name,
                ),
                row=1, col=1,
            )
        else:
            fig.add_trace(
                go.Scatter(x=df.index, y=df["Close"], mode="lines", name=name),
                row=1, col=1,
            )

        fig.add_trace(
            go.Bar(x=df.index, y=df["Volume"], name="거래량", marker_color="gray"),
            row=2, col=1,
        )

        fig.update_layout(
            height=500,
            xaxis_rangeslider_visible=False,
            showlegend=False,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------
# 정규화 비교 차트 (기준일 대비 % 변화)
# ------------------------------------------------------------------
else:
    st.subheader("📊 기준일 대비 변화율(%) 비교")
    fig = go.Figure()
    for name, df in data_dict.items():
        base = df["Close"].iloc[0]
        normalized = (df["Close"] / base - 1) * 100
        fig.add_trace(go.Scatter(x=df.index, y=normalized, mode="lines", name=name))

    fig.update_layout(
        height=600,
        yaxis_title="변화율 (%)",
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------
# 원본 데이터 테이블
# ------------------------------------------------------------------
with st.expander("📄 원본 데이터 보기"):
    for name, df in data_dict.items():
        st.markdown(f"**{name}**")
        st.dataframe(df.tail(20))
