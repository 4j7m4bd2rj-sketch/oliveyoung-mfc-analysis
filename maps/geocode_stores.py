import requests
import pandas as pd
import time

KAKAO_API_KEY = "1c833f7f910402fc624ba8fa13182be2"
INPUT_FILE = "올리브영 서울특별시 매장 개수와 위치.xlsx"
OUTPUT_FILE = "stores_with_coords.csv"

def get_coords(address):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": address}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        data = resp.json()
        if data["documents"]:
            doc = data["documents"][0]
            return float(doc["y"]), float(doc["x"])
    except Exception as e:
        print(f"  오류: {e}")
    return None, None

def main():
    df = pd.read_excel(INPUT_FILE)
    df = df[["매장명", "위치"]].dropna(subset=["매장명", "위치"])
    print(f"총 {len(df)}개 매장 좌표 변환 시작...")
    lats, lngs = [], []
    for i, (_, row) in enumerate(df.iterrows()):
        lat, lng = get_coords(row["위치"])
        lats.append(lat)
        lngs.append(lng)
        if lat:
            print(f"[{i+1}/{len(df)}] ✅ {row['매장명']}: {lat:.4f}, {lng:.4f}")
        else:
            print(f"[{i+1}/{len(df)}] ❌ {row['매장명']}: 실패")
        time.sleep(0.1)
    df["lat"] = lats
    df["lng"] = lngs
    df["구"] = df["위치"].str.extract(r"서울특별시 (.+?구)")
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n✅ 완료! {OUTPUT_FILE} 저장됨")

if __name__ == "__main__":
    main()