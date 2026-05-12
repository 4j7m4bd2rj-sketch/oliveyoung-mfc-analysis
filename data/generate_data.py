"""
올리브영 멀티 센터 주문분배 시뮬레이션 - 가상 데이터 생성
데이터 설계 근거:
- 테크블로그 공개 수치: 총 출고량 34.4% 증가, 리드타임 14시간 단축, 수동개입 49.2% 감소
- 센터: 양지(수도권 중심), 경산(비수도권 중심)
- 오늘드림 배송건수 2025년 1,920만건 기준 → 일평균 약 5.3만건
- 올영세일 피크타임: 평상시 대비 약 2.5배 주문 집중
"""

import pandas as pd
import numpy as np
import json
import os

np.random.seed(42)

# ── 1. 센터 데이터 ──────────────────────────────────────────────
centers = pd.DataFrame([
    {
        "center_id": "YANGJI",
        "name": "양지센터",
        "lat": 37.1953,
        "lng": 127.2006,
        "daily_capa": 30000,       # 일 최대 처리 건수
        "region": "수도권",
        "lead_time_inzone": 4,     # 권역 내 리드타임(시간)
        "lead_time_outzone": 18,   # 권역 외 리드타임(시간)
    },
    {
        "center_id": "GYEONGSAN",
        "name": "경산센터",
        "lat": 35.8197,
        "lng": 128.7409,
        "daily_capa": 20000,
        "region": "비수도권",
        "lead_time_inzone": 4,
        "lead_time_outzone": 18,
    },
])

# ── 2. 권역 데이터 (우편번호 앞 2자리 기준) ────────────────────
regions = {
    "수도권": list(range(1, 10)) + list(range(10, 20)),   # 01~19
    "비수도권": list(range(20, 100)),                      # 20~99
}

region_center_map = {
    "수도권": "YANGJI",
    "비수도권": "GYEONGSAN",
}

# ── 3. 상품 SKU 데이터 ──────────────────────────────────────────
skus = pd.DataFrame([
    {"sku_id": f"SKU{str(i).zfill(4)}", 
     "name": f"상품_{i}",
     "yangji_stock": np.random.randint(0, 500),
     "gyeongsan_stock": np.random.randint(0, 300),
     "category": np.random.choice(["스킨케어", "색조", "헤어", "바디", "향수"])}
    for i in range(1, 101)
])

# 고수요 상품 10개는 재고 충분히
skus.loc[:9, "yangji_stock"] = np.random.randint(300, 500, 10)
skus.loc[:9, "gyeongsan_stock"] = np.random.randint(200, 400, 10)

# ── 4. 주문 데이터 생성 함수 ────────────────────────────────────
def generate_orders(n_orders: int, scenario: str = "normal") -> pd.DataFrame:
    """
    scenario: 'normal' | 'peak'
    peak = 올영세일 피크타임 (주문 폭주, 양지 CAPA 초과)
    """
    postal_prefixes = list(range(1, 100))
    
    # 피크타임: 수도권 주문 비중 더 높음 (70%)
    if scenario == "peak":
        weights = [0.7 / 19 if p <= 19 else 0.3 / 80 for p in postal_prefixes]
    else:
        weights = [0.55 / 19 if p <= 19 else 0.45 / 80 for p in postal_prefixes]

    weights = np.array(weights)
    weights /= weights.sum()

    postal_codes = np.random.choice(postal_prefixes, size=n_orders, p=weights)
    sku_ids = np.random.choice(skus["sku_id"].values, size=n_orders,
                               p=np.ones(len(skus)) / len(skus))

    # 시간대 분포: 피크타임은 특정 시간대 집중
    if scenario == "peak":
        peak_p = np.array([0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
                           0.05, 0.08, 0.10, 0.12, 0.10, 0.08,
                           0.08, 0.07, 0.06, 0.05, 0.04, 0.03,
                           0.03, 0.02, 0.01, 0.01, 0.01, 0.01])
        peak_p /= peak_p.sum()
        hours = np.random.choice(range(24), size=n_orders, p=peak_p)
    else:
        hours = np.random.choice(range(24), size=n_orders)

    orders = pd.DataFrame({
        "order_id": [f"ORD{str(i).zfill(6)}" for i in range(n_orders)],
        "postal_prefix": postal_codes,
        "region": ["수도권" if p <= 19 else "비수도권" for p in postal_codes],
        "sku_id": sku_ids,
        "order_hour": hours,
        "scenario": scenario,
    })

    return orders


# ── 5. 데이터 저장 ──────────────────────────────────────────────
os.makedirs("data", exist_ok=True)

centers.to_csv("data/centers.csv", index=False, encoding="utf-8-sig")
skus.to_csv("data/skus.csv", index=False, encoding="utf-8-sig")

# 평상시 주문 (일평균 53,000건의 60% → 약 31,800건)
normal_orders = generate_orders(31800, "normal")
normal_orders.to_csv("data/orders_normal.csv", index=False, encoding="utf-8-sig")

# 피크타임 주문 (평상시 대비 2.5배 → 약 79,500건)
peak_orders = generate_orders(79500, "peak")
peak_orders.to_csv("data/orders_peak.csv", index=False, encoding="utf-8-sig")

with open("data/region_center_map.json", "w", encoding="utf-8") as f:
    json.dump(region_center_map, f, ensure_ascii=False)

print("✅ 데이터 생성 완료")
print(f"  - 센터: {len(centers)}개")
print(f"  - SKU: {len(skus)}개")
print(f"  - 평상시 주문: {len(normal_orders):,}건")
print(f"  - 피크타임 주문: {len(peak_orders):,}건")
