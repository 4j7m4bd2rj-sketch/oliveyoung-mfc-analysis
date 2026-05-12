"""
올리브영 오늘드림 MFC 커버리지 분석
- 서울 377개 매장 기준 MFC 반경 5km 커버리지 시각화
- 데이터: 직접 수집 + 카카오 로컬 API 좌표 변환
- MFC 위치: 공개된 뉴스/테크블로그 기반
"""

import pandas as pd
import numpy as np
import folium
from folium.plugins import MarkerCluster
from sklearn.cluster import KMeans

# 데이터 로드
df = pd.read_csv("data/stores_with_coords.csv")

MFC_LIST = [
    {"name": "MFC 강남",    "lat": 37.4996, "lng": 127.0357, "color": "#ef4444"},
    {"name": "MFC 성북",    "lat": 37.6063, "lng": 127.0208, "color": "#f97316"},
    {"name": "MFC 연희",    "lat": 37.5655, "lng": 126.9230, "color": "#eab308"},
    {"name": "MFC 서대문",  "lat": 37.5794, "lng": 126.9368, "color": "#84cc16"},
    {"name": "MFC 관악",    "lat": 37.4784, "lng": 126.9516, "color": "#06b6d4"},
    {"name": "MFC 구로강서", "lat": 37.5255, "lng": 126.8527, "color": "#8b5cf6"},
    {"name": "MFC 광진강동", "lat": 37.5381, "lng": 127.0866, "color": "#ec4899"},
    {"name": "MFC 노원",    "lat": 37.6542, "lng": 127.0568, "color": "#14b8a6"},
]

def get_dist_km(lat1, lng1, lat2, lng2):
    dlat = (lat1 - lat2) * 111
    dlng = (lng1 - lng2) * 88
    return (dlat**2 + dlng**2)**0.5

# 가장 가까운 MFC 거리 계산
df["nearest_dist_km"] = df.apply(
    lambda r: min(get_dist_km(r["lat"], r["lng"], m["lat"], m["lng"]) for m in MFC_LIST), axis=1
)
df["in_mfc_zone"] = df["nearest_dist_km"] <= 5

# 미커버 매장 KMeans 군집 분석 (신규 MFC 후보)
uncovered = df[~df["in_mfc_zone"]].copy()
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
kmeans.fit(uncovered[["lat", "lng"]])
new_mfc_candidates = []
for i, center in enumerate(kmeans.cluster_centers_):
    cluster_stores = uncovered[kmeans.labels_ == i]
    new_mfc_candidates.append({
        "name": f"신규 MFC 후보 {i+1}",
        "lat": center[0], "lng": center[1],
        "covers": len(cluster_stores),
        "구": cluster_stores["구"].value_counts().index[0],
    })

all_mfc = MFC_LIST + [{"name": c["name"], "lat": c["lat"], "lng": c["lng"]} for c in new_mfc_candidates]
df["in_mfc_zone_new"] = df.apply(
    lambda r: min(get_dist_km(r["lat"], r["lng"], m["lat"], m["lng"]) for m in all_mfc) <= 5, axis=1
)

before = df["in_mfc_zone"].sum()
after  = df["in_mfc_zone_new"].sum()

# 지도 생성
m = folium.Map(location=[37.545, 127.0], zoom_start=11, tiles="CartoDB positron")
new_colors = ["#f59e0b", "#10b981", "#3b82f6"]

# 기존 MFC 커버리지
for mfc in MFC_LIST:
    folium.Circle(location=[mfc["lat"], mfc["lng"]], radius=5000,
        color=mfc["color"], weight=1.5, fill=True,
        fill_color=mfc["color"], fill_opacity=0.08).add_to(m)

# 신규 MFC 후보 커버리지
for i, cand in enumerate(new_mfc_candidates):
    folium.Circle(location=[cand["lat"], cand["lng"]], radius=5000,
        color=new_colors[i], weight=2.5, fill=True,
        fill_color=new_colors[i], fill_opacity=0.15,
        tooltip=f"✨ {cand['name']} | {cand['covers']}개 신규 커버").add_to(m)

# 기존 MFC 마커
for mfc in MFC_LIST:
    folium.CircleMarker(location=[mfc["lat"], mfc["lng"]],
        radius=14, color=mfc["color"], weight=3,
        fill=True, fill_color=mfc["color"], fill_opacity=0.9,
        tooltip=f"📦 {mfc['name']}").add_to(m)
    folium.Marker(location=[mfc["lat"]+0.011, mfc["lng"]],
        icon=folium.DivIcon(
            html=f'<div style="font-size:10px;font-weight:bold;color:{mfc["color"]};white-space:nowrap;text-shadow:1px 1px 2px white;">{mfc["name"]}</div>',
            icon_size=(120,20))).add_to(m)

# 신규 MFC 후보 마커
for i, cand in enumerate(new_mfc_candidates):
    folium.CircleMarker(location=[cand["lat"], cand["lng"]],
        radius=18, color=new_colors[i], weight=4,
        fill=True, fill_color=new_colors[i], fill_opacity=0.95,
        tooltip=f"✨ {cand['name']} | {cand['구']} 권역 | {cand['covers']}개 신규 커버").add_to(m)

# 매장 표시
cluster = MarkerCluster(name="매장 전체").add_to(m)
for _, row in df.iterrows():
    if row["in_mfc_zone"]:
        color, label = "#16a34a", "✅"
    elif row["in_mfc_zone_new"]:
        color, label = "#f59e0b", "🆕"
    else:
        color, label = "#dc2626", "⚠️"
    folium.CircleMarker(
        location=[row["lat"], row["lng"]],
        radius=4, color=color, fill=True,
        fill_color=color, fill_opacity=0.75,
        tooltip=f"{label} {row['매장명']}").add_to(cluster)

legend = f"""
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;
     background:white;padding:16px 20px;border-radius:10px;
     border:1px solid #e5e7eb;font-size:13px;line-height:2.1;
     box-shadow:0 2px 8px rgba(0,0,0,0.12);max-width:290px">
  <b style='font-size:14px'>✨ 신규 MFC 입지 추천 분석</b>
  <hr style='margin:6px 0'>
  기존 커버: <b>{before}개 ({before/len(df)*100:.1f}%)</b><br>
  신규 추가 후: <b style='color:#10b981'>{after}개 ({after/len(df)*100:.1f}%)</b><br>
  개선: <b style='color:#f59e0b'>+{after-before}개</b>
  <hr style='margin:6px 0'>
  <span style='color:#16a34a'>●</span> 기존 커버 매장<br>
  <span style='color:#f59e0b'>●</span> 신규 커버 매장<br>
  <span style='color:#dc2626'>●</span> 여전히 미커버<br>
  <span style='font-size:11px;color:#9ca3af'>분석: KMeans 군집화 기반 최적 입지<br>
  MFC 위치: 공개 자료 기반</span>
</div>"""
m.get_root().html.add_child(folium.Element(legend))
m.save("maps/oliveyoung_coverage.html")
print("✅ map_coverage.py 완료!")
print(f"커버리지: {before}개 → {after}개 (+{after-before}개)")