import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pykrx import stock
import datetime

st.set_page_config(
    page_title="수급 스크리너",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.main .block-container{max-width:420px;padding:0.8rem 1rem}
h1{font-size:1.2rem!important}
.stTabs [data-baseweb="tab"]{font-size:0.85rem;padding:8px 10px}
div[data-testid="metric-container"]{background:#f0f4ff;border-radius:10px;padding:8px 12px;border:1px solid #e0e8ff}
.tag-drop{background:#fde8e8;color:#b91c1c;padding:2px 8px;border-radius:6px;font-size:0.75rem}
.tag-buy{background:#e0f2fe;color:#0369a1;padding:2px 8px;border-radius:6px;font-size:0.75rem}
.tag-vol{background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:6px;font-size:0.75rem}
.tag-inst{background:#fef9c3;color:#854d0e;padding:2px 8px;border-radius:6px;font-size:0.75rem}
</style>
""", unsafe_allow_html=True)

def get_last_bizday(offset=1):
    d = datetime.datetime.now() - datetime.timedelta(days=offset)
    while d.weekday() >= 5:
        d -= datetime.timedelta(days=1)
    return d.strftime("%Y%m%d")

def get_prev_bizday(date_str, n=1):
    d = datetime.datetime.strptime(date_str, "%Y%m%d")
    count = 0
    while count < n:
        d -= datetime.timedelta(days=1)
        if d.weekday() < 5:
            count += 1
    return d.strftime("%Y%m%d")

def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return df.columns[0]

@st.cache_data(ttl=1800)
def load_ohlcv(date_str):
    try:
        df1 = stock.get_market_ohlcv_by_ticker(date_str, market="KOSPI")
        df2 = stock.get_market_ohlcv_by_ticker(date_str, market="KOSDAQ")
        return pd.concat([df1, df2])
    except Exception as e:
        st.error(f"OHLCV 로드 오류: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_foreign(date_str):
    try:
        k1 = stock.get_market_net_purchases_of_equities_by_ticker(date_str, date_str, "KOSPI", "외국인")
        k2 = stock.get_market_net_purchases_of_equities_by_ticker(date_str, date_str, "KOSDAQ", "외국인")
        return pd.concat([k1, k2])
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_institution(date_str):
    try:
        k1 = stock.get_market_net_purchases_of_equities_by_ticker(date_str, date_str, "KOSPI", "기관합계")
        k2 = stock.get_market_net_purchases_of_equities_by_ticker(date_str, date_str, "KOSDAQ", "기관합계")
        return pd.concat([k1, k2])
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_52w_high(ticker):
    try:
        d_end = get_last_bizday(1)
        d_start = (datetime.datetime.strptime(d_end, "%Y%m%d") - datetime.timedelta(days=365)).strftime("%Y%m%d")
        df = stock.get_market_ohlcv_by_date(d_start, d_end, ticker)
        if df.empty:
            return None
        col = find_col(df, ["고가", "High", "high"])
        return df[col].max()
    except Exception:
        return None

@st.cache_data(ttl=3600)
def load_volume_avg(ticker, days=20):
    try:
        d_end = get_last_bizday(2)
        d_start = get_prev_bizday(d_end, days)
        df = stock.get_market_ohlcv_by_date(d_start, d_end, ticker)
        if df.empty or len(df) < 5:
            return None
        col = find_col(df, ["거래량", "Volume", "volume"])
        return df[col].mean()
    except Exception:
        return None

@st.cache_data(ttl=3600)
def load_chart(ticker, days=30):
    try:
        d_end = get_last_bizday(1)
        d_start = get_prev_bizday(d_end, days)
        df = stock.get_market_ohlcv_by_date(d_start, d_end, ticker)
        if df.empty:
            return pd.Series()
        col = find_col(df, ["종가", "Close", "close"])
        return df[col]
    except Exception:
        return pd.Series()

@st.cache_data(ttl=1800)
def debug_ohlcv_columns(date_str):
    try:
        df = stock.get_market_ohlcv_by_ticker(date_str, market="KOSPI")
        return list(df.columns)
    except Exception as e:
        return [str(e)]

def get_price(row):
    for c in ["종가", "Close", "close"]:
        if c in row.index:
            return row[c]
    return row.iloc[3] if len(row) > 3 else 0

def get_volume(row):
    for c in ["거래량", "Volume", "volume"]:
        if c in row.index:
            return row[c]
    return row.iloc[4] if len(row) > 4 else 0

def get_chg(row):
    for c in ["등락률", "Change", "change", "등락"]:
        if c in row.index:
            return row[c]
    return 0

st.title("📈 수급 스크리너")
bizday = get_last_bizday(1)
st.caption(f"기준일: {bizday[:4]}.{bizday[4:6]}.{bizday[6:]} · 장 마감 후 업데이트")

# 디버깅: 실제 컬럼명 확인
with st.expander("🔧 데이터 컬럼 확인 (문제해결용)"):
    cols = debug_ohlcv_columns(bizday)
    st.write("OHLCV 컬럼명:", cols)
    f_df = load_foreign(bizday)
    if not f_df.empty:
        st.write("외국인 수급 컬럼명:", list(f_df.columns))
    else:
        st.write("외국인 수급 데이터 없음")

tab1, tab2, tab3 = st.tabs(["📊 주도섹터", "🔍 낙폭과대주", "⚙️ 설정"])

with tab1:
    st.markdown("#### 오늘의 주도 섹터 (외국인+기관)")
    with st.spinner("데이터 불러오는 중..."):
        try:
            foreign_df = load_foreign(bizday)
            inst_df    = load_institution(bizday)
            ohlcv_df   = load_ohlcv(bizday)

            if foreign_df.empty:
                st.warning("외국인 수급 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.")
            elif ohlcv_df.empty:
                st.warning("주가 데이터를 불러올 수 없습니다.")
            else:
                f_col = foreign_df.columns[0]
                i_col = inst_df.columns[0] if not inst_df.empty else None

                merged = pd.DataFrame({"외국인": foreign_df[f_col]})
                merged["기관"] = inst_df[i_col] if i_col else 0
                merged = merged.fillna(0)
                merged["합계"] = merged["외국인"] + merged["기관"]

                sector_dict = {}
                for ticker in merged.index:
                    try:
                        sector = stock.get_market_sector_classifications(bizday, ticker)
                        if not sector:
                            continue
                        if sector not in sector_dict:
                            sector_dict[sector] = {"외국인": 0, "기관": 0, "합계": 0, "종목": []}
                        sector_dict[sector]["외국인"] += merged.loc[ticker, "외국인"]
                        sector_dict[sector]["기관"]   += merged.loc[ticker, "기관"]
                        sector_dict[sector]["합계"]   += merged.loc[ticker, "합계"]
                        sector_dict[sector]["종목"].append(ticker)
                    except Exception:
                        continue

                if not sector_dict:
                    st.warning("섹터 데이터를 불러올 수 없습니다.")
                else:
                    sector_sorted = sorted(sector_dict.items(), key=lambda x: x[1]["합계"], reverse=True)[:8]
                    names  = [s[0] for s in sector_sorted]
                    totals = [s[1]["합계"] / 1e8 for s in sector_sorted]
                    colors = ["#E24B4A" if v >= 0 else "#378ADD" for v in totals]

                    fig = go.Figure(go.Bar(
                        x=names, y=totals,
                        marker_color=colors,
                        text=[f"{v:.0f}억" for v in totals],
                        textposition="outside",
                    ))
                    fig.update_layout(
                        height=280,
                        margin=dict(l=0, r=0, t=10, b=60),
                        yaxis_title="순매수 (억원)",
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        font=dict(size=11),
                        xaxis=dict(tickangle=-30),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    top_name, top_data = sector_sorted[0]
                    st.markdown(f"#### 🏆 오늘 1위: **{top_name}**")
                    st.markdown(
                        f"<span class='tag-buy'>외국인 {top_data['외국인']/1e8:+.0f}억</span> "
                        f"<span class='tag-inst'>기관 {top_data['기관']/1e8:+.0f}억</span>",
                        unsafe_allow_html=True
                    )
                    st.markdown("---")
                    st.markdown("##### 주요 종목")
                    for ticker in top_data["종목"][:10]:
                        try:
                            name = stock.get_market_ticker_name(ticker)
                            if ticker not in ohlcv_df.index:
                                continue
                            row   = ohlcv_df.loc[ticker]
                            price = get_price(row)
                            chg   = get_chg(row)
                            f_val = merged.loc[ticker, "외국인"] / 1e8 if ticker in merged.index else 0
                            i_val = merged.loc[ticker, "기관"] / 1e8 if ticker in merged.index else 0
                            c1, c2 = st.columns([2, 1])
                            with c1:
                                st.markdown(f"**{name}**")
                                st.markdown(
                                    f"<span class='tag-buy'>외인 {f_val:+.0f}억</span> "
                                    f"<span class='tag-inst'>기관 {i_val:+.0f}억</span>",
                                    unsafe_allow_html=True
                                )
                            with c2:
                                st.metric("", f"{int(price):,}원", f"{chg:+.1f}%",
                                          delta_color="normal" if chg >= 0 else "inverse")
                            st.divider()
                        except Exception:
                            continue
        except Exception as e:
            st.error(f"데이터 오류: {e}")

with tab2:
    st.markdown("#### 낙폭과대 + 외국인/기관 동시 매수")
    min_drop = st.session_state.get("min_drop", 30)
    min_vol  = st.session_state.get("min_vol", 1.5)
    st.caption(f"조건: 고점대비 -{min_drop}% 이상 · 거래량 {min_vol}배↑ · 외인+기관 동시 순매수")

    if st.button("🔍 전체 시장 스크리닝", use_container_width=True):
        with st.spinner("전체 종목 분석 중... (1~2분 소요)"):
            results = []
            try:
                foreign_df = load_foreign(bizday)
                inst_df    = load_institution(bizday)
                ohlcv_df   = load_ohlcv(bizday)

                if foreign_df.empty:
                    st.warning("수급 데이터 없음. 잠시 후 다시 시도해 주세요.")
                else:
                    f_col = foreign_df.columns[0]
                    i_col = inst_df.columns[0] if not inst_df.empty else None
                    progress = st.progress(0)
                    all_tickers = list(ohlcv_df.index)

                    for i, ticker in enumerate(all_tickers):
                        progress.progress(min(int((i+1)/len(all_tickers)*100), 100))
                        try:
                            row      = ohlcv_df.loc[ticker]
                            price    = get_price(row)
                            volume   = get_volume(row)
                            chg      = get_chg(row)
                            if price == 0:
                                continue
                            f_val = foreign_df.loc[ticker, f_col] if ticker in foreign_df.index else 0
                            i_val = inst_df.loc[ticker, i_col] if (i_col and ticker in inst_df.index) else 0
                            if f_val <= 0 or i_val <= 0:
                                continue
                            high52 = load_52w_high(ticker)
                            if not high52 or high52 == 0:
                                continue
                            drop_pct = (price - high52) / high52 * 100
                            if drop_pct > -min_drop:
                                continue
                            avg_vol   = load_volume_avg(ticker)
                            vol_ratio = volume / avg_vol if avg_vol and avg_vol > 0 else 0
                            if vol_ratio < min_vol:
                                continue
                            results.append({
                                "ticker": ticker,
                                "name":   stock.get_market_ticker_name(ticker),
                                "price":  price,
                                "chg":    chg,
                                "drop":   drop_pct,
                                "vol":    vol_ratio,
                                "f_val":  f_val / 1e8,
                                "i_val":  i_val / 1e8,
                            })
                        except Exception:
                            continue

                    progress.empty()

                    if results:
                        st.success(f"✅ {len(results)}개 종목 발견")
                        for r in sorted(results, key=lambda x: -(x["f_val"]+x["i_val"]))[:20]:
                            c1, c2 = st.columns([2, 1])
                            with c1:
                                st.markdown(f"**{r['name']}** `{r['ticker']}`")
                                st.markdown(
                                    f"<span class='tag-drop'>고점대비 {r['drop']:.1f}%</span> "
                                    f"<span class='tag-buy'>외인 +{r['f_val']:.0f}억</span> "
                                    f"<span class='tag-inst'>기관 +{r['i_val']:.0f}억</span> "
                                    f"<span class='tag-vol'>거래량 {r['vol']:.1f}배</span>",
                                    unsafe_allow_html=True
                                )
                            with c2:
                                st.metric("", f"{int(r['price']):,}원", f"{r['chg']:+.1f}%",
                                          delta_color="normal" if r["chg"] >= 0 else "inverse")
                            chart = load_chart(r["ticker"])
                            if not chart.empty:
                                fig = go.Figure(go.Scatter(
                                    x=chart.index, y=chart.values,
                                    mode="lines",
                                    line=dict(color="#378ADD", width=1.5),
                                    fill="tozeroy",
                                    fillcolor="rgba(55,138,221,0.1)",
                                ))
                                fig.update_layout(
                                    height=100,
                                    margin=dict(l=0,r=0,t=0,b=0),
                                    xaxis=dict(visible=False),
                                    yaxis=dict(visible=False),
                                    plot_bgcolor="white",
                                    paper_bgcolor="white",
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            st.divider()
                    else:
                        st.warning("조건에 맞는 종목 없음. 설정에서 조건을 완화해 보세요.")
            except Exception as e:
                st.error(f"오류: {e}")

with tab3:
    st.markdown("#### 스크리닝 조건 설정")
    drop_val = st.slider("52주 고점 대비 낙폭 (%)", 10, 60,
                         st.session_state.get("min_drop", 30), 5)
    vol_val  = st.slider("거래량 배수 (20일 평균 대비)", 1.0, 5.0,
                         st.session_state.get("min_vol", 1.5), 0.5)
    if st.button("✅ 조건 저장", use_container_width=True):
        st.session_state["min_drop"] = drop_val
        st.session_state["min_vol"]  = vol_val
        st.success("저장됐습니다!")
    st.divider()
    if st.button("🔄 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()
st.caption("⚠️ 본 앱은 참고용이며 투자 추천이 아닙니다.")
