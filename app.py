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

SECTOR_MAP = {
    "반도체":   ["삼성전자","SK하이닉스","삼성전기","DB하이텍","원익IPS","이오테크닉스","한미반도체","리노공업","심텍","ISC"],
    "2차전지":  ["LG에너지솔루션","삼성SDI","SK이노베이션","에코프로비엠","포스코퓨처엠","엘앤에프","천보","솔브레인","동화기업","피엔티"],
    "바이오":   ["삼성바이오로직스","셀트리온","유한양행","한미약품","HLB","알테오젠","리가켐바이오","에스티팜","오스코텍","메지온"],
    "자동차":   ["현대차","기아","현대모비스","한온시스템","만도","현대위아","HL만도","서연이화","성우하이텍","화신"],
    "유리기판": ["SKC","삼성전기","LG이노텍","필옵틱스","이수페타시스","심텍","대덕전자","코리아써키트","티씨케이","원익홀딩스"],
    "AI/IT":    ["NAVER","카카오","크래프톤","넥슨게임즈","엔씨소프트","펄어비스","카카오게임즈","더존비즈온","NHN","케이아이엔엑스"],
    "방산":     ["한화에어로스페이스","LIG넥스원","현대로템","한국항공우주","빅텍","퍼스텍","스페코","휴니드","한화시스템","LIG넥스원"],
    "조선":     ["HD현대중공업","삼성중공업","한화오션","HD현대미포","현대삼호중공업","HD현대","세진중공업","동성화인텍","케이에스피","강림인슈"],
}

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
def load_market_data():
    try:
        kospi  = fdr.StockListing('KOSPI')
        kosdaq = fdr.StockListing('KOSDAQ')
        df = pd.concat([kospi, kosdaq])
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=1800)
def load_investor_by_stock(date_str):
    try:
        result = []
        headers = {"User-Agent": "Mozilla/5.0"}
        for sosok in ["0", "1"]:
            for page in range(1, 3):
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
                                "종목명":      name,
                                "현재가":      int(price),
                                "등락률":      float(chg) if chg.lstrip("-").replace(".", "").isdigit() else 0,
                                "거래량":      int(volume) if volume.isdigit() else 0,
                                "외국인순매수": int(f_net) if f_net.lstrip("-").isdigit() else 0,
                            })
                    except Exception:
                        continue
        df = pd.DataFrame(result) if result else pd.DataFrame()
        if not df.empty:
            df = df.drop_duplicates(subset=["종목명"]).reset_index(drop=True)
        return df
    except Exception:
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

tab1, tab2, tab3 = st.tabs(["📊 섹터별 수급", "🔍 낙폭과대주", "⚙️ 설정"])

with tab1:
    st.markdown("#### 섹터별 외국인 순매수")
    with st.spinner("데이터 불러오는 중..."):
        try:
            inv_df = load_investor_by_stock(bizday)
            if inv_df.empty:
                st.warning("데이터를 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.")
            else:
                inv_map = dict(zip(inv_df["종목명"], inv_df["외국인순매수"]))
                price_map = dict(zip(inv_df["종목명"], inv_df["현재가"]))
                chg_map   = dict(zip(inv_df["종목명"], inv_df["등락률"]))
                vol_map   = dict(zip(inv_df["종목명"], inv_df["거래량"]))

                # 섹터별 외국인 순매수 합계
                sector_totals = {}
                for sector, names in SECTOR_MAP.items():
                    total = sum(inv_map.get(n, 0) for n in names)
                    sector_totals[sector] = total

                sector_series = pd.Series(sector_totals).sort_values(ascending=False)

                # 섹터 막대 차트
                colors = ["#E24B4A" if v >= 0 else "#378ADD" for v in sector_series.values]
                fig = go.Figure(go.Bar(
                    x=sector_series.index,
                    y=sector_series.values,
                    marker_color=colors,
                    text=[f"{v:,}" for v in sector_series.values],
                    textposition="outside",
                ))
                fig.update_layout(
                    height=260,
                    margin=dict(l=0, r=0, t=10, b=50),
                    yaxis_title="외국인 순매수 (주)",
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(size=11),
                    xaxis=dict(tickangle=-30),
                )
                st.plotly_chart(fig, use_container_width=True, key="sector_chart")

                # 1위 섹터 강조
                top_sector = sector_series.idxmax()
                st.markdown(f"#### 🏆 오늘 1위: **{top_sector}**")
                st.markdown("---")

                # 섹터 선택 → 종목 보기
                selected = st.selectbox(
                    "섹터 선택해서 종목 보기",
                    list(SECTOR_MAP.keys()),
                    index=list(SECTOR_MAP.keys()).index(top_sector)
                )

                st.markdown(f"##### {selected} 종목")
                names_in_sector = SECTOR_MAP[selected]
                found = False
                for name in names_in_sector:
                    if name not in price_map:
                        continue
                    found = True
                    price  = price_map.get(name, 0)
                    chg    = chg_map.get(name, 0)
                    f_net  = inv_map.get(name, 0)
                    volume = vol_map.get(name, 0)
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.markdown(f"**{name}**")
                        color_tag = "tag-buy" if f_net >= 0 else "tag-drop"
                        sign = "+" if f_net >= 0 else ""
                        st.markdown(
                            f"<span class='{color_tag}'>외인 {sign}{f_net:,}주</span> "
                            f"<span class='tag-vol'>거래량 {volume:,}</span>",
                            unsafe_allow_html=True
                        )
                    with c2:
                        st.metric(
                            "", f"{price:,}원", f"{chg:+.1f}%",
                            delta_color="normal" if chg >= 0 else "inverse"
                        )
                    st.divider()
                if not found:
                    st.info("해당 섹터 종목 데이터가 없습니다.")
        except Exception as e:
            st.error(f"오류: {e}")

with tab2:
    st.markdown("#### 낙폭과대 + 외국인 순매수")
    min_drop = st.session_state.get("min_drop", 30)
    st.caption(f"조건: 고점대비 -{min_drop}% 이상 · 외국인 순매수")

    if st.button("🔍 스크리닝 실행", use_container_width=True):
        with st.spinner("분석 중... (1~2분 소요)"):
            try:
                inv_df = load_investor_by_stock(bizday)
                if inv_df.empty:
                    st.warning("데이터 없음. 잠시 후 다시 시도해 주세요.")
                else:
                    market_df  = load_market_data()
                    ticker_map = {}
                    if not market_df.empty:
                        for name_col in ["Name", "종목명"]:
                            for code_col in ["Symbol", "Code"]:
                                if name_col in market_df.columns and code_col in market_df.columns:
                                    ticker_map = dict(zip(market_df[name_col], market_df[code_col]))
                                    break

                    results  = []
                    cands    = inv_df[inv_df["외국인순매수"] > 0]
                    total    = len(cands)
                    progress = st.progress(0)

                    for i, (_, row) in enumerate(cands.iterrows()):
                        progress.progress(min(int((i+1)/max(total,1)*100), 100))
                        try:
                            name   = row["종목명"]
                            price  = row["현재가"]
                            chg    = row["등락률"]
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
                                st.metric(
                                    "", f"{r['price']:,}원", f"{r['chg']:+.1f}%",
                                    delta_color="normal" if r["chg"] >= 0 else "inverse"
                                )
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
                                st.plotly_chart(fig, use_container_width=True, key=f"chart_{r['ticker']}")
                            st.divider()
                    else:
                        st.warning("조건에 맞는 종목 없음. 설정에서 조건을 완화해 보세요.")
            except Exception as e:
                st.error(f"오류: {e}")

with tab3:
    st.markdown("#### 스크리닝 조건 설정")
    drop_val = st.slider("52주 고점 대비 낙폭 (%)", 10, 60,
                         st.session_state.get("min_drop", 30), 5)
    if st.button("✅ 조건 저장", use_container_width=True):
        st.session_state["min_drop"] = drop_val
        st.success("저장됐습니다!")
    st.divider()
    if st.button("🔄 데이터 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.divider()
st.caption("⚠️ 본 앱은 참고용이며 투자 추천이 아닙니다.")
