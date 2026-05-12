"""
주문분배 시뮬레이터

[올리브영 방식] 테크블로그 4단계 로직 구현
  1단계. SKU 재고 보유 센터 확인
  2단계. CAPA 여유 확인
  3단계. 우편번호 기준 권역 매칭 → 최적 센터 우선순위
  4단계. 최적 센터 확정 → 출하지시

[쿠팡식 방식] 구조적 차이 비교용
  - 주문 즉시 재고 확정 (선점 방식) → 팬텀 재고 없음
  - 단일 대형 FC 중심 출고
  - CAPA 초과 시 대기열(지연) 처리
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass


@dataclass
class CenterState:
    center_id: str
    name: str
    daily_capa: int
    processed: int = 0

    @property
    def remaining_capa(self) -> int:
        return max(0, self.daily_capa - self.processed)

    @property
    def utilization(self) -> float:
        return self.processed / self.daily_capa if self.daily_capa > 0 else 0

    @property
    def is_overloaded(self) -> bool:
        return self.processed >= self.daily_capa


# ── 올리브영 방식 ────────────────────────────────────────────────
def simulate_oliveyoung(orders, skus, centers_df):
    sku_map = skus.set_index("sku_id").to_dict("index")
    center_states = {
        row["center_id"]: CenterState(
            center_id=row["center_id"],
            name=row["name"],
            daily_capa=row["daily_capa"],
        )
        for _, row in centers_df.iterrows()
    }

    lead_time_map = {
        ("YANGJI",    "수도권"):   4,
        ("YANGJI",    "비수도권"): 18,
        ("GYEONGSAN", "비수도권"): 4,
        ("GYEONGSAN", "수도권"):   18,
    }

    results = []
    for _, order in orders.iterrows():
        sku = sku_map.get(order["sku_id"], {})
        region = order["region"]

        # 권역 우선순위
        priority = ["YANGJI", "GYEONGSAN"] if region == "수도권" else ["GYEONGSAN", "YANGJI"]

        # 1단계: 재고 보유 센터
        stock_ok = []
        if sku.get("yangji_stock", 0) > 0:
            stock_ok.append("YANGJI")
        if sku.get("gyeongsan_stock", 0) > 0:
            stock_ok.append("GYEONGSAN")

        if not stock_ok:
            results.append(_make_result(order, None, "취소_재고없음", 0))
            continue

        # 2단계: CAPA 여유 센터
        capa_ok = [c for c in stock_ok if not center_states[c].is_overloaded]
        if not capa_ok:
            results.append(_make_result(order, None, "취소_CAPA초과(팬텀재고)", 0))
            continue

        # 3단계: 권역 기반 최적 센터
        assigned = next((c for c in priority if c in capa_ok), None)

        # 4단계: 출하지시
        center_states[assigned].processed += 1
        lead_time = lead_time_map.get((assigned, region), 18)
        results.append(_make_result(order, assigned, "출고완료", lead_time))

    return pd.DataFrame(results)


# ── 쿠팡식 방식 ──────────────────────────────────────────────────
def simulate_coupang(orders, skus, centers_df):
    """
    쿠팡식: 주문 즉시 재고 선점 + 단일 대형 FC
    - 양지+경산 통합 재고 풀에서 즉시 선점 → 팬텀 재고 없음
    - CAPA 초과 시 취소 없이 지연 처리
    """
    sku_df = skus.set_index("sku_id")
    reserved = (sku_df["yangji_stock"] + sku_df["gyeongsan_stock"]).to_dict()

    # 단일 대형 FC CAPA (양지+경산 합산의 1.2배)
    main_fc_capa = int(centers_df["daily_capa"].sum() * 1.2)
    processed = 0
    queue_delay = 0

    results = []
    for _, order in orders.iterrows():
        sku_id = order["sku_id"]
        region = order["region"]

        # 재고 즉시 선점
        if reserved.get(sku_id, 0) <= 0:
            results.append(_make_result(order, None, "취소_재고없음", 0))
            continue

        reserved[sku_id] -= 1  # 선점 완료

        if processed >= main_fc_capa:
            # CAPA 초과 → 대기열(지연)
            queue_delay += 1
            delay_extra = (queue_delay // 500) * 4
            base_lt = 4 if region == "수도권" else 20
            results.append(_make_result(order, "MAIN_FC", "출고완료_지연", base_lt + delay_extra))
        else:
            processed += 1
            lead_time = 4 if region == "수도권" else 20
            results.append(_make_result(order, "MAIN_FC", "출고완료", lead_time))

    return pd.DataFrame(results)


# ── 공통 ─────────────────────────────────────────────────────────
def _make_result(order, center_id, status, lead_time):
    return {
        "order_id":       order["order_id"],
        "sku_id":         order["sku_id"],
        "region":         order["region"],
        "order_hour":     order["order_hour"],
        "scenario":       order["scenario"],
        "assigned_center": center_id,
        "status":         status,
        "lead_time":      lead_time,
        "is_cancelled":   "취소" in status,
        "is_delayed":     "지연" in status,
        "is_completed":   "출고완료" in status,
    }


def compute_kpi(result_df):
    total = len(result_df)
    cancelled = result_df["is_cancelled"].sum()
    delayed   = result_df["is_delayed"].sum()
    completed = result_df["is_completed"].sum()
    avg_lead  = result_df[result_df["lead_time"] > 0]["lead_time"].mean()
    return {
        "total_orders":    total,
        "completed":       int(completed),
        "cancelled":       int(cancelled),
        "delayed":         int(delayed),
        "cancel_rate":     round(cancelled / total * 100, 2),
        "delay_rate":      round(delayed   / total * 100, 2),
        "completion_rate": round(completed / total * 100, 2),
        "avg_lead_time":   round(float(avg_lead), 1),
    }
