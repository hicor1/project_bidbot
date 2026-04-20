"""
models.py 검증 — 시트 원시 dict → ProductRow 변환 + 고유키 인덱스.

Part A: 오프라인 케이스 (네트워크 호출 없음, 빠름)
  - 합성 dict 로 다양한 에지 케이스 검증
  - 파싱 유틸, is_active_*, compute_supply_price, 고유키

Part B: 온라인 케이스 (실제 시트 읽어서 모델 변환)
  - 01_read 와 동일한 경로 + parse_rows
"""

import _common  # noqa: F401

from sheets import models, schema


def 구분선(제목):
    print()
    print("=" * 60)
    print(제목)
    print("=" * 60)


# ─────────────────────────────────────────────────────────────
# Part A — 오프라인
# ─────────────────────────────────────────────────────────────
def part_a_offline():
    구분선("Part A. 오프라인 — 합성 dict 파싱")

    합성 = {
        "브랜드": "아디다스",
        "포이즌": "V",
        "크림": "v",                 # 소문자 허용
        "출고처": "정관",
        "NAME": "FIREBIRD SHO BLUE\t",  # 탭 있음
        "CODE": "JD0817",
        "SIZE": "M",
        "수량": "3",                  # 문자열도 int 로
        "정상가": 59000,
        "할인율": 0.3,
        "공급가(=하한가)": "",        # 비어있음
        "크림현재입찰가": "",
        "포이즌현재입찰가": "",
        "갱신일": "",
        "크림상태": "",
        "포이즌상태": "",
    }

    row = models.from_dict(합성, row_number=3)

    assert row.brand == "아디다스"
    assert row.poizon_on is True
    assert row.kream_on is True, "소문자 v 도 True"
    assert row.name == "FIREBIRD SHO BLUE", "탭 strip 되어야"
    assert row.code == "JD0817"
    assert row.size == "M"
    assert row.qty == 3, "문자열 '3' → int 3"
    assert row.list_price == 59000
    assert row.discount == 0.3
    assert row.supply_price is None, "빈값은 None"
    assert row.key == ("JD0817", "M")
    assert row.row_number == 3
    print("[OK] 합성 dict → ProductRow 기본 파싱")

    # 공급가 자동 계산
    계산 = row.compute_supply_price()
    assert 계산 == int(round(59000 * 0.7)), f"기대 41300, 실제 {계산}"
    print(f"[OK] 공급가 계산: 59000×(1-0.3)={계산}")

    # is_active
    assert row.is_active_for_kream is True
    assert row.is_active_for_poizon is True
    print("[OK] is_active_for_* : kream+poizon 모두 True")

    # 보류 처리
    hold_row = models.from_dict({**합성, "크림상태": "보류"}, row_number=4)
    assert hold_row.is_active_for_kream is False, "보류면 KREAM off"
    assert hold_row.is_active_for_poizon is True, "포이즌상태는 안 건드렸으니 유지"
    print("[OK] 크림상태=보류 → KREAM off")

    # 수량 0
    qty0 = models.from_dict({**합성, "수량": 0}, row_number=5)
    assert qty0.is_active_for_kream is False
    assert qty0.is_active_for_poizon is False
    print("[OK] 수량=0 → 양 마켓 off")

    # V 없음
    no_flag = models.from_dict({**합성, "크림": "", "포이즌": ""}, row_number=6)
    assert no_flag.is_active_for_kream is False
    assert no_flag.is_active_for_poizon is False
    print("[OK] 플래그 빈값 → 양 마켓 off")

    # 엉뚱한 할인율
    bad = models.from_dict({**합성, "할인율": "abc"}, row_number=7)
    assert bad.discount is None
    assert bad.compute_supply_price() is None, "할인율 파싱 실패 → 공급가 None"
    print("[OK] 할인율 이상치 → supply_price None")


def part_a_index():
    구분선("Part A. 고유키 인덱스")

    rows = [
        models.from_dict({"CODE": "A", "SIZE": "S"}, row_number=3),
        models.from_dict({"CODE": "A", "SIZE": "M"}, row_number=4),
        models.from_dict({"CODE": "B", "SIZE": "L"}, row_number=5),
        models.from_dict({"CODE": "", "SIZE": ""}, row_number=6),   # 빈 키 → 스킵
    ]
    idx = models.build_index(rows)
    assert len(idx) == 3, f"3건이어야 하는데 {len(idx)}"
    assert ("A", "S") in idx
    assert ("A", "M") in idx
    assert ("B", "L") in idx
    print(f"[OK] 정상 3건 인덱싱 (빈 키 1건 스킵)")

    rows_dupe = [
        models.from_dict({"CODE": "A", "SIZE": "S"}, row_number=3),
        models.from_dict({"CODE": "A", "SIZE": "S"}, row_number=7),  # 중복
    ]
    idx2 = models.build_index(rows_dupe)
    assert idx2[("A", "S")].row_number == 7, "마지막 행 채택"
    print(f"[OK] 중복 키 → 마지막 행 채택 (row_number=7)")


# ─────────────────────────────────────────────────────────────
# Part B — 온라인
# ─────────────────────────────────────────────────────────────
def part_b_online():
    구분선("Part B. 온라인 — 실제 시트 읽고 ProductRow 로 변환")

    from sheets.gsheet import open_worksheet, read_header_and_rows

    ws = open_worksheet()
    _, raw_rows = read_header_and_rows(ws)
    print(f"시트 읽기: {len(raw_rows)} 건")

    rows = models.parse_rows(raw_rows)
    print(f"파싱 성공: {len(rows)} 건")

    for r in rows[:5]:
        공급가_자동 = r.compute_supply_price()
        print(
            f"  row {r.row_number:>3d}  "
            f"{r.brand:6s} {r.code:10s} {r.size:4s}  "
            f"qty={r.qty}  정상가={r.list_price}  "
            f"할인={r.discount}  자동공급가={공급가_자동}  "
            f"kream={r.is_active_for_kream} poizon={r.is_active_for_poizon}"
        )

    idx = models.build_index(rows)
    print(f"\n고유키 인덱스: {len(idx)} 건")
    for key in list(idx.keys())[:5]:
        print(f"  {key} → row {idx[key].row_number}")


def main():
    part_a_offline()
    part_a_index()
    part_b_online()
    구분선("전체 통과")


if __name__ == "__main__":
    main()
