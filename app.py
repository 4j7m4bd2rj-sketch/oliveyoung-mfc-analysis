"""
올리브영 멀티 센터 주문분배 시뮬레이터
OliveYoung Delivery Optimization Simulator

데이터 출처:
- 올리브영 테크블로그 (2026.03.06): 배송최적화 시스템 구축기
- 올리브영 뉴스룸: 오늘드림 배송건수 2025년 1,920만건
- 기업분석자료: MFC 22개, 매장 1,400개
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import folium
from streamlit_folium import st_folium

from data.generate_data import generate_orders
from simulator.distributor import (
    simulate_oliveyoung, simulate_coupang, compute_kpi
)

# ── 페이지 설정 ──────────────────────────────────────────────────
st.set_page_config(
    page_title="OliveYoung Delivery Sim",
    page_icon="🫙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 스타일 ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@300;400;500;600&family=IBM+Plex+Mono&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans KR', sans-serif;
}
.main { background: #0f0f0f; }

.metric-card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
}
.metric-label {
    color: #888;
    font-size: 12px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 28px;
    font-weight: 600;
    font-family: 'IBM Plex Mono', monospace;
}
.metric-green { color: #4ade80; }
.metric-red { color: #f87171; }
.metric-yellow { color: #fbbf24; }
.metric-blue { color: #60a5fa; }

.insight-box {
    background: #1a1a1a;
    border-left: 3px solid #84cc16;
    padding: 16px 20px;
    border-radius: 0 8px 8px 0;
    margin: 12px 0;
    font-size: 14px;
    line-height: 1.7;
    color: #d1d5db;
}
.section-title {
    font-size: 13px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #2a2a2a;
}
.tag {
    display: inline-block;
    background: #1f2937;
    color: #9ca3af;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    margin: 2px;
    font-family: 'IBM Plex Mono', monospace;
}
</style>
""", unsafe_allow_html=True)

# ── 사이드바 ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🫙 OliveYoung\n### Delivery Sim")
    st.markdown("---")

    scenario = st.radio(
        "📦 시나리오",
        ["평상시", "피크타임 (올영세일)"],
        index=1,
    )
    scenario_key = "normal" if scenario == "평상시" else "peak"

    st.markdown("---")
    st.markdown("""
    <div class='section-title'>데이터 설계 근거</div>
    <div style='font-size:12px; color:#6b7280; line-height:1.8;'>
    📌 올리브영 테크블로그 공개 수치 기반<br>
    • 오늘드림 연간 1,920만건 (2025)<br>
    • 총 출고량 세일 전후 34.4%↑<br>
    • 리드타임 평균 14시간 단축<br>
    • 수동개입 49.2%↓<br>
    • 센터: 양지(수도권), 경산(비수도권)
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div class='section-title'>분배 로직 비교</div>
    <div style='font-size:12px; color:#6b7280; line-height:1.8;'>
    🟢 <b style='color:#4ade80'>올리브영</b><br>
    재고→CAPA→권역 순 필터링<br>
    CAPA 초과 시 취소(팬텀재고)<br><br>
    🔵 <b style='color:#60a5fa'>쿠팡식</b><br>
    주문 즉시 재고 선점<br>
    CAPA 초과 시 지연(취소없음)
    </div>
    """, unsafe_allow_html=True)

# ── 데이터 로드 ──────────────────────────────────────────────────
@st.cache_data
def load_data():
    centers = pd.read_csv("data/centers.csv")
    skus = pd.read_csv("data/skus.csv")
    return centers, skus

@st.cache_data
def run_simulation(scenario_key):
    centers, skus = load_data()
    n = 31800 if scenario_key == "normal" else 79500
    orders = generate_orders(n, scenario_key)

    oy_result = simulate_oliveyoung(orders, skus, centers)
    cp_result = simulate_coupang(orders, skus, centers)

    oy_kpi = compute_kpi(oy_result)
    cp_kpi = compute_kpi(cp_result)

    return orders, oy_result, cp_result, oy_kpi, cp_kpi, centers

orders, oy_result, cp_result, oy_kpi, cp_kpi, centers = run_simulation(scenario_key)

# ── 헤더 ─────────────────────────────────────────────────────────
st.markdown(f"""
<h1 style='font-size:28px; font-weight:600; margin-bottom:4px;'>
  올리브영 멀티센터 주문분배 시뮬레이터
</h1>
<p style='color:#6b7280; font-size:14px; margin-bottom:24px;'>
  OliveYoung Delivery Optimization · 
  <span class='tag'>{scenario}</span>
  <span class='tag'>{oy_kpi['total_orders']:,}건 주문</span>
</p>
""", unsafe_allow_html=True)

# ── 탭 ───────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 KPI 비교",
    "🗺️ 센터 지도",
    "⏱️ 시간대별 부하",
    "💡 인사이트",
])

# ══════════════════════════════════════════════════
# TAB 1: KPI 비교
# ══════════════════════════════════════════════════
with tab1:
    st.markdown("<div class='section-title'>핵심 지표 비교 — 올리브영 vs 쿠팡식</div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🟢 올리브영 방식")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>취소율</div>
                <div class='metric-value metric-red'>{oy_kpi['cancel_rate']}%</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>처리 완료율</div>
                <div class='metric-value metric-green'>{oy_kpi['completion_rate']}%</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>평균 리드타임</div>
                <div class='metric-value metric-yellow'>{oy_kpi['avg_lead_time']}h</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>지연 건수</div>
                <div class='metric-value metric-blue'>{oy_kpi['delayed']:,}</div>
            </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("#### 🔵 쿠팡식 방식")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>취소율</div>
                <div class='metric-value metric-red'>{cp_kpi['cancel_rate']}%</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>처리 완료율</div>
                <div class='metric-value metric-green'>{cp_kpi['completion_rate']}%</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>평균 리드타임</div>
                <div class='metric-value metric-yellow'>{cp_kpi['avg_lead_time']}h</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""<div class='metric-card'>
                <div class='metric-label'>지연 건수</div>
                <div class='metric-value metric-blue'>{cp_kpi['delayed']:,}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 상태별 분포 비교 차트
    st.markdown("<div class='section-title'>주문 처리 상태 분포</div>", unsafe_allow_html=True)

    oy_status = oy_result["status"].value_counts().reset_index()
    oy_status.columns = ["status", "count"]
    oy_status["method"] = "올리브영"

    cp_status = cp_result["status"].value_counts().reset_index()
    cp_status.columns = ["status", "count"]
    cp_status["method"] = "쿠팡식"

    combined = pd.concat([oy_status, cp_status])

    color_map = {
        "출고완료": "#4ade80",
        "출고완료_지연": "#fbbf24",
        "취소_CAPA초과(팬텀재고)": "#f87171",
        "취소_재고없음": "#ef4444",
    }

    fig = px.bar(
        combined, x="method", y="count", color="status",
        color_discrete_map=color_map,
        barmode="stack",
        labels={"count": "주문 건수", "method": "분배 방식", "status": "상태"},
    )
    fig.update_layout(
        paper_bgcolor="#0f0f0f",
        plot_bgcolor="#0f0f0f",
        font_color="#d1d5db",
        legend=dict(bgcolor="#1a1a1a"),
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)

    # 권역별 리드타임 비교
    st.markdown("<div class='section-title'>권역별 평균 리드타임 비교</div>", unsafe_allow_html=True)

    oy_lt = oy_result[oy_result["lead_time"] > 0].groupby("region")["lead_time"].mean().reset_index()
    oy_lt["method"] = "올리브영"
    cp_lt = cp_result[cp_result["lead_time"] > 0].groupby("region")["lead_time"].mean().reset_index()
    cp_lt["method"] = "쿠팡식"

    lt_combined = pd.concat([oy_lt, cp_lt])

    fig2 = px.bar(
        lt_combined, x="region", y="lead_time", color="method",
        barmode="group",
        color_discrete_map={"올리브영": "#4ade80", "쿠팡식": "#60a5fa"},
        labels={"lead_time": "평균 리드타임(시간)", "region": "권역"},
    )
    fig2.update_layout(
        paper_bgcolor="#0f0f0f",
        plot_bgcolor="#0f0f0f",
        font_color="#d1d5db",
        height=320,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════
# TAB 2: 센터 지도
# ══════════════════════════════════════════════════
with tab2:
    st.markdown("<div class='section-title'>센터 위치 및 주문 분배 현황</div>", unsafe_allow_html=True)

    m = folium.Map(location=[36.5, 127.8], zoom_start=7, tiles="CartoDB dark_matter")

    # 센터별 처리량 계산
    oy_center_counts = oy_result[oy_result["is_completed"]]["assigned_center"].value_counts().to_dict()

    center_info = {
        "YANGJI": {"color": "#4ade80", "name": "양지센터", "region": "수도권"},
        "GYEONGSAN": {"color": "#60a5fa", "name": "경산센터", "region": "비수도권"},
    }

    for _, row in centers.iterrows():
        cid = row["center_id"]
        count = oy_center_counts.get(cid, 0)
        info = center_info.get(cid, {})
        radius = 20 + (count / 1000)

        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=min(radius, 50),
            color=info.get("color", "#fff"),
            fill=True,
            fill_color=info.get("color", "#fff"),
            fill_opacity=0.7,
            popup=folium.Popup(
                f"""<b>{info.get('name')}</b><br>
                권역: {info.get('region')}<br>
                처리량: {count:,}건<br>
                CAPA: {int(row['daily_capa']):,}건/일<br>
                가동률: {count/row['daily_capa']*100:.1f}%""",
                max_width=200
            ),
            tooltip=f"{info.get('name')} · {count:,}건 처리"
        ).add_to(m)

        folium.Marker(
            location=[row["lat"] + 0.3, row["lng"]],
            icon=folium.DivIcon(
                html=f'<div style="font-size:12px;color:{info.get("color")};font-weight:bold;white-space:nowrap;">{info.get("name")}<br>{count:,}건</div>',
                icon_size=(120, 40),
            )
        ).add_to(m)

    # 수도권/비수도권 경계선 (위도 37도 기준 단순화)
    folium.PolyLine(
        locations=[[37.0, 124.5], [37.0, 130.0]],
        color="#6b7280", weight=1, dash_array="5 5",
        tooltip="수도권/비수도권 구분선 (단순화)"
    ).add_to(m)

    st_folium(m, width=None, height=500)

    # 센터별 CAPA 현황
    st.markdown("<div class='section-title'>센터별 CAPA 가동률</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    for i, (_, row) in enumerate(centers.iterrows()):
        cid = row["center_id"]
        count = oy_center_counts.get(cid, 0)
        util = count / row["daily_capa"] * 100
        info = center_info.get(cid, {})

        with (col1 if i == 0 else col2):
            st.markdown(f"**{info.get('name')}** ({info.get('region')})")
            st.progress(min(util / 100, 1.0))
            st.caption(f"처리 {count:,}건 / CAPA {int(row['daily_capa']):,}건 · 가동률 {util:.1f}%")

# ══════════════════════════════════════════════════
# TAB 3: 시간대별 부하
# ══════════════════════════════════════════════════
with tab3:
    st.markdown("<div class='section-title'>시간대별 주문 유입 및 센터 처리 현황</div>", unsafe_allow_html=True)

    # 시간대별 주문 건수
    hourly = orders.groupby("order_hour").size().reset_index(name="count")

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=hourly["order_hour"],
        y=hourly["count"],
        name="시간대별 주문",
        marker_color="#84cc16",
        opacity=0.8,
    ))
    fig3.update_layout(
        title="시간대별 주문 유입량",
        xaxis_title="시간(시)",
        yaxis_title="주문 건수",
        paper_bgcolor="#0f0f0f",
        plot_bgcolor="#1a1a1a",
        font_color="#d1d5db",
        height=300,
    )
    st.plotly_chart(fig3, use_container_width=True)

    # 시간대별 취소율 (올리브영)
    oy_hourly = oy_result.groupby("order_hour").agg(
        total=("order_id", "count"),
        cancelled=("is_cancelled", "sum"),
    ).reset_index()
    oy_hourly["cancel_rate"] = oy_hourly["cancelled"] / oy_hourly["total"] * 100

    cp_hourly = cp_result.groupby("order_hour").agg(
        total=("order_id", "count"),
        delayed=("is_delayed", "sum"),
    ).reset_index()
    cp_hourly["delay_rate"] = cp_hourly["delayed"] / cp_hourly["total"] * 100

    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=oy_hourly["order_hour"],
        y=oy_hourly["cancel_rate"],
        name="올리브영 취소율",
        line=dict(color="#f87171", width=2),
        fill="tozeroy",
        fillcolor="rgba(248,113,113,0.1)",
    ))
    fig4.add_trace(go.Scatter(
        x=cp_hourly["order_hour"],
        y=cp_hourly["delay_rate"],
        name="쿠팡식 지연율",
        line=dict(color="#60a5fa", width=2),
        fill="tozeroy",
        fillcolor="rgba(96,165,250,0.1)",
    ))
    fig4.update_layout(
        title="시간대별 취소율 / 지연율 비교",
        xaxis_title="시간(시)",
        yaxis_title="비율(%)",
        paper_bgcolor="#0f0f0f",
        plot_bgcolor="#1a1a1a",
        font_color="#d1d5db",
        height=320,
        legend=dict(bgcolor="#1a1a1a"),
    )
    st.plotly_chart(fig4, use_container_width=True)

    # 센터별 시간대 처리량
    st.markdown("<div class='section-title'>올리브영 — 센터별 시간대 처리량</div>", unsafe_allow_html=True)
    oy_center_hourly = oy_result[oy_result["is_completed"]].groupby(
        ["order_hour", "assigned_center"]
    ).size().reset_index(name="count")

    fig5 = px.line(
        oy_center_hourly,
        x="order_hour", y="count", color="assigned_center",
        color_discrete_map={"YANGJI": "#4ade80", "GYEONGSAN": "#60a5fa"},
        labels={"count": "처리 건수", "order_hour": "시간(시)", "assigned_center": "센터"},
    )
    fig5.update_layout(
        paper_bgcolor="#0f0f0f",
        plot_bgcolor="#1a1a1a",
        font_color="#d1d5db",
        height=300,
    )
    st.plotly_chart(fig5, use_container_width=True)

# ══════════════════════════════════════════════════
# TAB 4: 인사이트
# ══════════════════════════════════════════════════
with tab4:
    st.markdown("<div class='section-title'>시뮬레이션 주요 인사이트</div>", unsafe_allow_html=True)

    cancel_diff = oy_kpi["cancel_rate"] - cp_kpi["cancel_rate"]
    lt_diff = cp_kpi["avg_lead_time"] - oy_kpi["avg_lead_time"]
    delayed_pct = cp_kpi["delay_rate"]

    # 인사이트 1
    st.markdown(f"""
    <div class='insight-box'>
    <b>💡 인사이트 1. 팬텀 재고 vs 대기열 지연 — 취소냐 지연이냐의 트레이드오프</b><br><br>
    {scenario} 시뮬레이션에서 올리브영 방식의 취소율은 <b>{oy_kpi['cancel_rate']}%</b>,
    쿠팡식의 취소율은 <b>{cp_kpi['cancel_rate']}%</b>로 나타났습니다.
    올리브영 방식은 CAPA 초과 시 주문을 <b>취소</b>하는 구조(팬텀 재고)인 반면,
    쿠팡식은 재고를 즉시 선점해 취소를 막되 <b>지연({cp_kpi['delay_rate']}%)</b>으로 대응합니다.
    이는 "취소 제로화"를 목표로 한다면 재고 선점 로직 고도화가 핵심임을 시사합니다.
    </div>
    """, unsafe_allow_html=True)

    # 인사이트 2
    st.markdown(f"""
    <div class='insight-box'>
    <b>💡 인사이트 2. 권역 기반 분배의 리드타임 우위</b><br><br>
    올리브영 방식의 평균 리드타임은 <b>{oy_kpi['avg_lead_time']}시간</b>,
    쿠팡식은 <b>{cp_kpi['avg_lead_time']}시간</b>으로
    올리브영이 <b>{abs(lt_diff):.1f}시간</b> {'단축' if lt_diff > 0 else '더 소요'}됩니다.
    이는 권역별 최적 센터 배정(수도권→양지, 비수도권→경산)이
    단일 허브 방식 대비 배송 속도에서 유의미한 차이를 만들어냄을 보여줍니다.
    테크블로그의 실제 개선치(14시간 단축)와 방향성이 일치합니다.
    </div>
    """, unsafe_allow_html=True)

    # 인사이트 3
    st.markdown(f"""
    <div class='insight-box'>
    <b>💡 인사이트 3. 피크타임일수록 분배 로직의 효과가 극대화</b><br><br>
    {'피크타임 시나리오에서' if scenario_key == 'peak' else '평상시 대비 피크타임에서'}
    주문이 특정 시간대에 집중될수록 단일 센터 방식의 병목이 심화됩니다.
    올리브영의 동적 분배 로직은 양지센터 과부하 시 경산센터로 즉시 이관하여
    전체 처리량을 유지하는 구조적 강점을 갖습니다.
    단, 현재 시뮬레이션 기준 CAPA 초과 취소가 발생하는 구간에서
    <b>재고 선제 배치 + 출고 가능 재고 우선 확정 로직</b> 고도화가
    "결제 후 취소 제로화"의 핵심 개선 포인트입니다.
    </div>
    """, unsafe_allow_html=True)

    # 인사이트 4: 면접 한 문장
    st.markdown("---")
    st.markdown("<div class='section-title'>📌 면접 활용 포인트</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style='background:#1a1a1a; border:1px solid #84cc16; border-radius:8px; padding:20px; margin-top:8px;'>
    <p style='color:#84cc16; font-size:13px; margin-bottom:8px;'>💬 1분 자기소개 / 자소서 3번 연계 멘트</p>
    <p style='color:#f9fafb; font-size:15px; line-height:1.9;'>
    "자소서에서 올리브영 오늘드림의 결제 후 취소 문제를 언급했는데,
    이를 직접 검증해보고 싶어 테크블로그 공개 수치를 기반으로
    멀티센터 주문분배 시뮬레이터를 구현했습니다.
    시뮬레이션 결과, 쿠팡식 재고 선점 방식과 비교했을 때
    올리브영 방식의 구조적 강점과 개선 포인트를 
    데이터로 확인할 수 있었습니다."
    </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='section-title'>시뮬레이션 요약</div>
    <div style='font-size:13px; color:#6b7280; line-height:2;'>
    • 시나리오: {scenario} · 총 주문 {oy_kpi['total_orders']:,}건<br>
    • 데이터 출처: 올리브영 테크블로그 공개 수치 기반 설계<br>
    • 분배 로직: 블로그 4단계 프로세스(SKU→CAPA→권역→출하지시) 직접 구현<br>
    • 비교 대상: 쿠팡식 재고 선점 + 단일 FC 구조 (구조적 차이 비교)
    </div>
    """, unsafe_allow_html=True)
