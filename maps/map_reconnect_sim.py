"""
올리브영 오늘드림 재연동 리스크 시뮬레이션
- 30분 초과 시 재연동 발생 (내부 브이로그 공개 자료 참고)
- 22년 상반기 기준 평균 처리 26분
- MFC 우선순위 매칭 시 처리시간 단축 효과 시뮬레이션
"""

import pandas as pd
import numpy as np
import folium
from folium.plugins import AntPath

np.random.seed(42)

df = pd.read_csv("data/stores_with_coords.csv")

MFC_LIST = [
    {"name": "MFC 강남",    "lat": 37.4996, "lng": 127.0357, "color": "#ef4444", "has_24h": True},
    {"name": "MFC 성북",    "lat": 37.6063, "lng": 127.0208, "color": "#f97316", "has_24h": False},
    {"name": "MFC 연희",    "lat": 37.5655, "lng": 126.9230, "color": "#eab308", "has_24h": True},
    {"name": "MFC 서대문",  "lat": 37.5794, "lng": 126.9368, "color": "#84cc16", "has_24h": False},
    {"name": "MFC 관악",    "lat": 37.4784, "lng": 126.9516, "color": "#06b6d4", "has_24h": False},
    {"name": "MFC 구로강서", "lat": 37.5255, "lng": 126.8527, "color": "#8b5cf6", "has_24h": False},
    {"name": "MFC 광진강동", "lat": 37.5381, "lng": 127.0866, "color": "#ec4899", "has_24h": False},
    {"name": "MFC 노원",    "lat": 37.6542, "lng": 127.0568, "color": "#14b8a6", "has_24h": False},
]
mfc_map = {m["name"]: m for m in MFC_LIST}

def get_dist_km(lat1, lng1, lat2, lng2):
    return (((lat1-lat2)*111)**2 + ((lng1-lng2)*88)**2)**0.5

def assign_nearest_mfc(row):
    dists = sorted([(get_dist_km(row["lat"], row["lng"], m["lat"], m["lng"]), m) for m in MFC_LIST])
    return dists[0][1]["name"], dists[0][0], dists[1][1]["name"], dists[1][0]

results = df.apply(lambda r: assign_nearest_mfc(r), axis=1)
df["nearest_mfc"]     = results.apply(lambda x: x[0])
df["nearest_dist_km"] = results.apply(lambda x: x[1])
df["second_mfc"]      = results.apply(lambda x: x[2])
df["in_mfc_zone"]     = df["nearest_dist_km"] <= 5

# 처리 시간 시뮬레이션 (평균 26분 기준)
df["peak_process_min"] = np.random.normal(26, 5, len(df)).clip(10, 45) * np.random.uniform(1.3, 1.8, len(df))
df.loc[df["in_mfc_zone"], "peak_process_min"] *= 0.6  # MFC 우선매칭 시 40% 단축
df["peak_over30"] = df["peak_process_min"] > 30

# 지도
m = folium.Map(location=[37.545, 127.0], zoom_start=11, tiles="CartoDB positron")

# MFC 커버리지
for mfc in MFC_LIST:
    folium.Circle(location=[mfc["lat"], mfc["lng"]], radius=5000,
        color=mfc["color"], weight=1.5, fill=True,
        fill_color=mfc["color"], fill_opacity=0.08).add_to(m)

# MFC 마커
for mfc in MFC_LIST:
    folium.CircleMarker(location=[mfc["lat"], mfc["lng"]],
        radius=16, color=mfc["color"], weight=4,
        fill=True, fill_color=mfc["color"], fill_opacity=0.9,
        tooltip=f"📦 {mfc['name']} {'| 24H ✓' if mfc['has_24h'] else ''}",
        popup=folium.Popup(
            f"<b>{mfc['name']}</b><br>24H: {'✅' if mfc['has_24h'] else '❌'}<br>배송반경: 5km",
            max_width=200)).add_to(m)
    folium.Marker(location=[mfc["lat"]+0.011, mfc["lng"]],
        icon=folium.DivIcon(
            html=f'<div style="font-size:10px;font-weight:bold;color:{mfc["color"]};white-space:nowrap;text-shadow:1px 1px 2px white;">{mfc["name"]}{"⭐" if mfc["has_24h"] else ""}</div>',
            icon_size=(130,20))).add_to(m)

# 매장 표시 + 재연동 화살표
for _, row in df.iterrows():
    process_min = round(row["peak_process_min"], 1)
    in_zone = row["in_mfc_zone"]
    over30  = row["peak_over30"]

    if in_zone and not over30:
        color, radius = "#16a34a", 4
        tooltip = f"✅ {row['매장명']} | {process_min}분"
    elif in_zone and over30:
        color, radius = "#f97316", 5
        tooltip = f"⚠️ {row['매장명']} | {process_min}분 → 재연동"
    elif not in_zone and over30:
        color, radius = "#dc2626", 7
        tooltip = f"🔴 {row['매장명']} | {process_min}분 → 재연동"
        nearest = mfc_map.get(row["nearest_mfc"])
        if nearest:
            AntPath(
                locations=[[row["lat"], row["lng"]], [nearest["lat"], nearest["lng"]]],
                color="#dc2626", weight=2, opacity=0.6, delay=1000,
                tooltip=f"🔄 {row['매장명']} → {row['nearest_mfc']} 재연동",
                dash_array=[6,14], pulse_color="#fff").add_to(m)
    else:
        color, radius = "#eab308", 5
        tooltip = f"🟡 {row['매장명']} | {process_min}분"

    folium.CircleMarker(
        location=[row["lat"], row["lng"]],
        radius=radius, color=color, fill=True,
        fill_color=color, fill_opacity=0.85,
        tooltip=tooltip,
        popup=folium.Popup(
            f"<b>{row['매장명']}</b><br>MFC: {row['nearest_mfc']}<br>"
            f"피크 처리시간: {process_min}분<br>"
            f"{'🔴 30분 초과 → 재연동' if over30 else '✅ 정상 처리'}<br>"
            f"재연동 대상: {row['nearest_mfc'] if over30 else '-'}",
            max_width=220)).add_to(m)

safe_n       = int((df["in_mfc_zone"] & ~df["peak_over30"]).sum())
mfc_risk_n   = int((df["in_mfc_zone"] & df["peak_over30"]).sum())
no_mfc_risk_n = int((~df["in_mfc_zone"] & df["peak_over30"]).sum())
no_mfc_ok_n  = int((~df["in_mfc_zone"] & ~df["peak_over30"]).sum())

legend = f"""
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;
     background:white;padding:16px 20px;border-radius:10px;
     border:1px solid #e5e7eb;font-size:13px;line-height:2.1;
     box-shadow:0 2px 8px rgba(0,0,0,0.12);max-width:310px">
  <b style='font-size:14px'>🗺️ 오늘드림 재연동 리스크 시뮬레이션</b>
  <hr style='margin:6px 0'>
  <b>피크타임 기준 (30분 초과 → 재연동)</b><br>
  <span style='color:#16a34a'>●</span> 정상 처리: <b>{safe_n}개</b><br>
  <span style='color:#f97316'>●</span> MFC 커버 but 재연동 위험: <b>{mfc_risk_n}개</b><br>
  <span style='color:#eab308'>●</span> MFC 미커버 but 처리 가능: <b>{no_mfc_ok_n}개</b><br>
  <span style='color:#dc2626'>●</span> MFC 미커버 + 재연동 위험: <b style='color:#dc2626'>{no_mfc_risk_n}개 ← 핵심 병목</b><br>
  <span style='color:#dc2626'>——▶</span> 재연동 흐름<br>
  <hr style='margin:6px 0'>
  <span style='font-size:11px;color:#9ca3af'>
  참고: 공개 브이로그 기반 시뮬레이션<br>
  22년 상반기 평균 처리 26분 / 30분 초과 시 재연동<br>
  ⭐ = 24H 서비스 운영 MFC
  </span>
</div>"""
m.get_root().html.add_child(folium.Element(legend))
m.save("maps/oliveyoung_reconnect_sim.html")
print("✅ map_reconnect_sim.py 완료!")
print(f"핵심 병목 매장: {no_mfc_risk_n}개 ({no_mfc_risk_n/len(df)*100:.1f}%)")