
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="AI 클라우드 인프라 분석", page_icon="☁️", layout="wide")

# ------------------------------------------------------------------
# AI 클라우드 인프라 관련 핵심 종목 목록
# ------------------------------------------------------------------
CLOUD_INFRA_TICKERS = {
    "Microsoft (Azure)": "MSFT",
    "Amazon (AWS)": "AMZN",
    "Alphabet (Google Cloud)": "GOOGL",
    "Oracle (OCI)": "ORCL",
    "IBM": "IBM",
    "CoreWeave": "CRWV",
    "Super Micro Computer": "SMCI",
    "Dell Technologies": "DELL",
    "Hewlett Packard Enterprise": "HPE",
    "Vertiv (전력/냉각)": "VRT",
    "Equinix (데이터센터 리츠)": "EQIX",
    "Digital Realty (데이터센터 리츠)": "DLR",
    "Arista Networks (네트워크 장비)": "ANET",
    "Cisco Systems": "CSCO",
    "Nutanix": "NTNX",
    "Snowflake": "SNOW",
    "Palantir": "PLTR",
}

PERIOD_OPTIONS = {
    "1개월": "1mo", "3개월": "3mo", "6개월": "6mo",
    "1년": "1y", "2년": "2y", "5년": "5y", "최대": "max",
}

# ------------------------------------------------------------------
# 사이드바
# ------------------------------------------------------------------
st.sidebar.title("☁️ AI 클라우드 인프라 설정")

selected_names = st.sidebar.multiselect(
    "분석할 종목 선택",
    options=list(CLOUD_INFRA_TICKERS.keys()),
    default=["Microsoft (Azure)", "Amazon (AWS)", "Alphabet (Google Cloud)", "Oracle (OCI)", "Vertiv (전력/냉각)", "Equinix (데이터센터 리츠)"],
)

period_label = st.sidebar.selectbox("기간", list(PERIOD_OPTIONS.keys()), index=3)
chart_type = st.sidebar.radio("개별 차트 종류", ["캔들스틱", "선 그래프"], index=0)
ma_windows = st.sidebar.multiselect("이동평균선(MA) 표시", [5, 20, 60, 120], default=[20, 60])

st.sidebar.markdown("---")
st.sidebar.caption("데이터 출처: Yahoo Finance (yfinance)")

st.title("☁️ AI 클라우드 인프라 전문 분석 대시보드")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

tickers_to_fetch = {name: CLOUD_INFRA_TICKERS[name] for name in selected_names}

if not tickers_to_fetch:
    st.info("왼쪽 사이드바에서 종목을 하나 이상 선택해주세요.")
    st.stop()

# ------------------------------------------------------------------
# 데이터 로드
# ------------------------------------------------------------------
@st.cache_data(ttl=600)
def load_history(ticker: str, period: str) -> pd.DataFrame:
    return yf.Ticker(ticker).history(period=period)

@st.cache_data(ttl=600)
def load_info(ticker: str) -> dict:
    try:
        return yf.Ticker(ticker).info
    except Exception:
        return {}

data_dict, info_dict = {}, {}
for name, ticker in tickers_to_fetch.items():
    df = load_history(ticker, PERIOD_OPTIONS[period_label])
    if not df.empty:
        data_dict[name] = df
        info_dict[name] = load_info(ticker)

if not data_dict:
    st.error("데이터를 불러오지 못했습니다.")
    st.stop()

# ------------------------------------------------------------------
# 1. 요약 지표 (현재가 / 등락률 / 시가총액 / PER)
# ------------------------------------------------------------------
st.subheader("📌 요약 지표")
cols = st.columns(min(len(data_dict), 4) or 1)

for i, (name, df) in enumerate(data_dict.items()):
    last_price = df["Close"].iloc[-1]
    prev_price = df["Close"].iloc[-2] if len(df) > 1 else last_price
    change_pct = (last_price - prev_price) / prev_price * 100 if prev_price else 0
    info = info_dict.get(name, {})
    market_cap = info.get("marketCap")
    pe_ratio = info.get("trailingPE")

    with cols[i % len(cols)]:
        st.metric(label=name, value=f"{last_price:,.2f}", delta=f"{change_pct:+.2f}%")
        cap_str = f"{market_cap/1e9:,.1f}B" if market_cap else "N/A"
        pe_str = f"{pe_ratio:.1f}" if pe_ratio else "N/A"
        st.caption(f"시가총액: {cap_str} | PER: {pe_str}")

st.markdown("---")

# ------------------------------------------------------------------
# 2. 기준일 대비 수익률 비교
# ------------------------------------------------------------------
st.subheader("📊 종목별 누적 수익률 비교 (%)")
fig_compare = go.Figure()
for name, df in data_dict.items():
    base = df["Close"].iloc[0]
    normalized = (df["Close"] / base - 1) * 100
    fig_compare.add_trace(go.Scatter(x=df.index, y=normalized, mode="lines", name=name))

fig_compare.update_layout(
    height=550,
    yaxis_title="누적 수익률 (%)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=30, b=10),
)
st.plotly_chart(fig_compare, use_container_width=True)

st.markdown("---")

# ------------------------------------------------------------------
# 3. 상관관계 히트맵
# ------------------------------------------------------------------
st.subheader("🔗 종목 간 수익률 상관관계")
returns_df = pd.DataFrame({name: df["Close"].pct_change() for name, df in data_dict.items()}).dropna()
corr = returns_df.corr()

fig_corr = go.Figure(
    data=go.Heatmap(
        z=corr.values, x=corr.columns, y=corr.columns,
        colorscale="RdBu", zmid=0, zmin=-1, zmax=1,
        text=corr.round(2).values, texttemplate="%{text}",
    )
)
fig_corr.update_layout(height=500, margin=dict(l=10, r=10, t=30, b=10))
st.plotly_chart(fig_corr, use_container_width=True)

st.markdown("---")

# ------------------------------------------------------------------
# 4. 개별 종목 상세 차트
# ------------------------------------------------------------------
st.subheader("📈 개별 종목 상세 차트")
for name, df in data_dict.items():
    st.markdown(f"**{name}**")
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.75, 0.25], vertical_spacing=0.05,
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

    for window in ma_windows:
        ma = df["Close"].rolling(window=window).mean()
        fig.add_trace(
            go.Scatter(x=df.index, y=ma, mode="lines", name=f"MA{window}", line=dict(width=1)),
            row=1, col=1,
        )

    fig.add_trace(
        go.Bar(x=df.index, y=df["Volume"], name="거래량", marker_color="gray"),
        row=2, col=1,
    )

    fig.update_layout(
        height=500,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------
# 5. 원본 데이터
# ------------------------------------------------------------------
with st.expander("📄 원본 데이터 보기"):
    for name, df in data_dict.items():
        st.markdown(f"**{name}**")
        st.dataframe(df.tail(20))
