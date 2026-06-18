import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import FinanceDataReader as fdr
import datetime
import requests
from bs4 import BeautifulSoup

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
    KST = datetime.timezone(datetime.timedelta(hours=9))
    d = datetime.datetime.now(KST) - datetime.timedelta(days=offset)
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

@st.cache_data(ttl=1800)
def load_market_data(date_str):
    try:
        kospi = fdr.StockListing('KOSPI')
        kosdaq = fdr.StockListing('KOSDAQ')
        df = pd.concat([kospi, kosdaq])
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_foreign_institution(date_str):
    try:
        url = f"https://finance.naver.com/sise/sise_quant.naver?sosok=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        result = []
        for sosok in ["0", "1"]:
            url = f"https://finance.naver.com/sise/sise_quant.naver?sosok={sosok}"
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "lxml")
            table = soup.find("table", {"class": "type_2"})
            if not table:
                continue
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 10:
                    continue
                try:
                    name   = cols[1].text.strip()
                    price  = cols[2].text.strip().replace(",", "")
                    chg    = cols[4].text.strip().replace(",", "").replace("%", "")
                    volume = cols[5].text.strip().replace(",", "")
                    f_buy  = cols[8].text.strip().replace(",", "")
                    if name and price:
                        result.append({
                            "종목명": name,
                            "현재가": int(price) if price.lstrip("-").isdigit() else 0,
                            "등락률": float(chg) if chg.lstrip("-").replace(".", "").isdigit() else 0,
                            "거래량": int(volume) if volume.isdigit() else 0,
                            "외국인순매수": int(f_buy) if f_buy.lstrip("-").isdigit() else 0,
                        })
                except Exception:
                    continue
        return pd.DataFrame(result)
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_investor_by_stock(date_str):
    try:
        url = "https://finance.naver.com/sise/sise_quant.naver?sosok=0"
        headers = {"User-Agent": "Mozilla/5.0"}
        result = []
        for sosok in ["0", "1"]:
            for page in range(1, 4):
                url = f"https://finance.naver.com/sise/sise_quant.naver?sosok={sosok}&page={page}"
                res = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, "lxml")
                table = soup.find("table", {"class": "type_2"})
                if not table:
                    continue
                rows = table.find_all("tr")
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) < 10:
                        continue
                    try:
                        name   = cols[1].text.strip()
                        price  = cols[2].text.strip().replace(",", "")
                        chg    = cols[4].text.strip().replace(",", "").replace("%", "")
                        volume = cols[5].text.strip().replace(",", "")
                        f_net  = cols[8].text.strip().replace(",", "")
                        if name and price and price.lstrip("-").isdigit():
                            result.append({
                                "종목명":     name,
                                "현재가":     int(price),
                                "등락률":     float(chg) if chg.lstrip("-").replace(".", "").isdigit() else 0,
                                "거래량":     int(volume) if volume.isdigit() else 0,
                                "외국인순매수": int(f_net) if f_net.lstrip("-").isdigit() else 0,
                            })
                    except Exception:
                        continue
        return pd.DataFrame(result) if result else pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_chart(ticker, days=30):
    try:
        d_end   = datetime.datetime.now().strftime("%Y-%m-%d")
        d_start = (datetime.datetime.now() - datetime.timedelta(days=days*2)).strftime("%Y-%m-%d")
        df = fdr.DataReader(ticker, d_start, d_end)
        return df["Close"].tail(days) if not df.empty else pd.Series()
    except Exception:
        return pd.Series()

@st.cache_data(ttl=3600)
def load_52w_high(ticker):
    try:
        d_end   = datetime.datetime.now().strftime("%Y-%m-%d")
        d_start = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
        df = fdr.DataReader(ticker, d_start, d_end)
        return df["High"].max() if not df.empty else None
    except Exception:
        return None

st.title("📈 수급 스크리너")
bizday = get_last_bizday(1)
st.caption(f"기준일: {bizday[:4]}.{bizday[4:6]}.{bizday[6:]} · 장 마감 후 업데이트")

tab1, tab2, tab3 = st.tabs(["📊 외국인 수급", "🔍 낙폭과대주", "⚙️ 설정"])

with tab1:
    st.markdown("#### 외국인 순매수 상위 종목")
    with st.spinner("네이버 금융에서 데이터 불러오는 중..."):
        try:
            df = load_investor_by_stock(bizday)
            if df.empty:
                st.warning("데이터를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.")
            else:
                top_f = df[df["외국인순매수"] > 0].sort_values("외국인순매수", ascending=False).head(15)
                if top_f.empty:
                    st.warning("외국인 순매수 데이터가 없습니다.")
                else:
                    for _, row in top_f.iterrows():
                        chg = row["등락률"]
                        c1, c2 = st.columns([2, 1])
                        with c1:
                            st.markdown(f"**{row['종목명']}**")
                            st.markdown(
                                f"<span class='tag-buy'>외인 +{row['외국인순매수']:,}주</span> "
                                f"<span class='tag-vol'>거래량 {row['거래량']:,}</span>",
                                unsafe_allow_html=True
                            )
                        with c2:
                            st.metric("", f"{row['현재가']:,}원", f"{chg:+.1f}%",
                                      delta_color="normal" if chg >= 0 else "inverse")
                        st.divider()
        except Exception as e:
            st.error(f"오류: {e}")

with tab2:
    st.markdown("#### 낙폭과대 + 외국인 순매수")
    min_drop = st.session_state.get("min_drop", 30)
    min_vol  = st.session_state.get("min_vol", 1.5)
    st.caption(f"조건: 고점대비 -{min_drop}% 이상 · 거래량 {min_vol}배↑ · 외국인 순매수")

    if st.button("🔍 스크리닝 실행", use_container_width=True):
        with st.spinner("분석 중... (1~2분 소요)"):
            try:
                df = load_investor_by_stock(bizday)
                if df.empty:
                    st.warning("데이터 없음. 잠시 후 다시 시도해 주세요.")
                else:
                    results = []
                    cands = df[df["외국인순매수"] > 0]
                    progress = st.progress(0)
                    total = len(cands)

                    market_df = load_market_data(bizday)
                    ticker_map = {}
                    if not market_df.empty:
                        for col in ["Symbol", "Code", "ticker"]:
                            if col in market_df.columns:
                                name_col = [c for c in market_df.columns if "Name" in c or "종목명" in c]
                                if name_col:
                                    ticker_map = dict(zip(market_df[name_col[0]], market_df[col]))
                                break

                    for i, (_, row) in enumerate(cands.iterrows()):
                        progress.progress(min(int((i+1)/max(total,1)*100), 100))
                        try:
                            name   = row["종목명"]
                            price  = row["현재가"]
                            chg    = row["등락률"]
                            volume = row["거래량"]
                            f_net  = row["외국인순매수"]
                            if price == 0:
                                continue
                            ticker = ticker_map.get(name)
                            if not ticker:
                                continue
                            high52 = load_52w_high(ticker)
                            if not high52 or high52 == 0:
                                continue
                            drop_pct = (price - high52) / high52 * 100
                            if drop_pct > -min_drop:
                                continue
                            results.append({
                                "name":   name,
                                "ticker": ticker,
                                "price":  price,
                                "chg":    chg,
                                "drop":   drop_pct,
                                "f_net":  f_net,
                            })
                        except Exception:
                            continue

                    progress.empty()

                    if results:
                        st.success(f"✅ {len(results)}개 종목 발견")
                        for r in sorted(results, key=lambda x: x["drop"])[:20]:
                            c1, c2 = st.columns([2, 1])
                            with c1:
                                st.markdown(f"**{r['name']}** `{r['ticker']}`")
                                st.markdown(
                                    f"<span class='tag-drop'>고점대비 {r['drop']:.1f}%</span> "
                                    f"<span class='tag-buy'>외인 +{r['f_net']:,}주</span>",
                                    unsafe_allow_html=True
                                )
                            with c2:
                                st.metric("", f"{r['price']:,}원", f"{r['chg']:+.1f}%",
                                          delta_color="normal" if r["chg"] >= 0 else "inverse")
                            chart = load_chart(r["ticker"])
                            if not chart.empty:
                                fig = go.Figure(go.Scatter(
                                    x=list(range(len(chart))),
                                    y=chart.values,
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
