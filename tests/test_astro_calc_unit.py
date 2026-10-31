"""Unit test riêng cho dịch vụ services/astro-calc:
- Năm nhuận (2000-02-29, 2024-02-29 hợp lệ; 1900-02-29, 1999-02-29, 1990-02-30 báo lỗi tiếng Việt)
- Giờ không rõ (gio_sinh=None, gio_sinh="", gio_khong_ro=True -> houses rỗng, tính tại 12:00 địa phương)
- Vĩ độ cao (vòng Bắc Cực / Nam Cực lat=64.14, 70.0, -70.0 tự chuyển Porphyry, trả đủ 12 đỉnh nhà hợp lệ)
- Đổi múi giờ lịch sử (Sài Gòn 1970 UTC+8, Sài Gòn 1945 UTC+9, Sài Gòn 1985 UTC+7, Hà Nội 1970 vĩ tuyến > 17 UTC+7, London GMT/BST)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from astro_calc.app import app
from astro_calc.positions import (
    compute_birth_chart,
    compute_positions,
    parse_birth_date,
    parse_birth_time,
    utc_offset_hours,
    validate_coordinates,
)


def _ang_diff(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


# ---------------------------------------------------------------------------
# 1. Năm nhuận (Leap years)
# ---------------------------------------------------------------------------
def test_leap_year_valid_dates_and_continuity():
    """Năm nhuận thế kỷ 2000 (chia hết cho 400) và 2024 (chia hết cho 4) tính đúng và liên tục."""
    d_2000 = parse_birth_date("2000-02-29")
    assert (d_2000.year, d_2000.month, d_2000.day) == (2000, 2, 29)

    d_2024 = parse_birth_date("2024-02-29")
    assert (d_2024.year, d_2024.month, d_2024.day) == (2024, 2, 29)

    c_feb28 = compute_birth_chart("2000-02-28", "00:10", 16.05, 108.2, "Asia/Ho_Chi_Minh")
    c_feb29 = compute_birth_chart("2000-02-29", "00:10", 16.05, 108.2, "Asia/Ho_Chi_Minh")
    c_mar01 = compute_birth_chart("2000-03-01", "00:10", 16.05, 108.2, "Asia/Ho_Chi_Minh")

    sun_28 = next(p["kinh_do"] for p in c_feb28["planets"] if p["ten"] == "Sun")
    sun_29 = next(p["kinh_do"] for p in c_feb29["planets"] if p["ten"] == "Sun")
    sun_01 = next(p["kinh_do"] for p in c_mar01["planets"] if p["ten"] == "Sun")
    moon_29 = next(p["kinh_do"] for p in c_feb29["planets"] if p["ten"] == "Moon")

    # Khớp mốc chuẩn 2000-02-29 00:10 Đà Nẵng
    assert _ang_diff(sun_29, 339.418) < 0.05
    assert _ang_diff(moon_29, 266.269) < 0.05
    # Mặt Trời tiến ~1 độ mỗi ngày qua ngày nhuận 29/02
    assert 0.95 < (sun_29 - sun_28) < 1.05
    assert 0.95 < (sun_01 - sun_29) < 1.05


@pytest.mark.parametrize(
    "bad_date",
    [
        "1900-02-29",  # năm tròn thế kỷ không chia hết cho 400 -> không nhuận
        "2100-02-29",  # năm tròn thế kỷ không chia hết cho 400 -> không nhuận
        "1999-02-29",  # năm thường không nhuận
        "1990-02-30",  # ngày 30/02 không tồn tại
        "2024-04-31",  # tháng 4 chỉ có 30 ngày
    ],
)
def test_non_leap_year_feb_29_rejected_in_vietnamese(bad_date: str):
    """Ngày 29/02 ở năm không nhuận (kể cả 1900, 2100) phải bị từ chối với thông báo tiếng Việt."""
    with pytest.raises(ValueError) as exc_info:
        parse_birth_date(bad_date)
    assert any(c in str(exc_info.value) for c in "àáảãạăâđèéêìíòóôơùúưỳý")


# ---------------------------------------------------------------------------
# 2. Giờ không rõ (Unknown birth time)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("gio_sinh", "gio_khong_ro"),
    [
        (None, False),
        ("", False),
        ("   ", False),
        ("08:30", True),
    ],
)
def test_unknown_birth_time_returns_empty_houses(gio_sinh, gio_khong_ro):
    """Khi không rõ giờ sinh, danh sách houses phải rỗng, asc/mc là None, và tính vị trí tại 12:00 trưa."""
    chart = compute_birth_chart(
        "1990-01-01",
        gio_sinh,
        lat=21.03,
        lon=105.85,
        tz="Asia/Ho_Chi_Minh",
        gio_khong_ro=gio_khong_ro,
    )
    assert chart["gio_khong_ro"] is True
    assert chart["houses"] == []
    assert chart["asc"] is None
    assert chart["mc"] is None
    assert chart["house_system_used"] is None
    assert len(chart["planets"]) == 13

    # Vị trí hành tinh khi không rõ giờ phải khớp với thời điểm 12:00 trưa địa phương
    noon_chart = compute_birth_chart("1990-01-01", "12:00", lat=21.03, lon=105.85, tz="Asia/Ho_Chi_Minh")
    assert chart["planets"] == noon_chart["planets"]


def test_compute_positions_unknown_time_flag():
    """compute_positions với unknown_time=True trả houses=[] nhưng giữ cusps 13 phần tử đều 30° cho tương thích ngược."""
    res = compute_positions(datetime(1990, 1, 1, 5, 0), 21.03, 105.85, unknown_time=True)
    assert res["unknown_time"] is True
    assert res["houses"] == []
    assert len(res["cusps"]) == 13
    assert res["cusps"][1:] == [30.0 * i for i in range(12)]


# ---------------------------------------------------------------------------
# 3. Vĩ độ cao (High latitudes & polar circle)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("lat", "lon", "tz", "expect_high_lat", "expect_system"),
    [
        (64.1466, -21.9426, "Atlantic/Reykjavik", False, "P"),  # Reykjavik (sát vòng Bắc Cực)
        (69.6492, 18.9553, "Europe/Oslo", True, "O"),  # Tromso (trong vòng Bắc Cực -> Porphyry)
        (78.2232, 15.6267, "Arctic/Longyearbyen", True, "O"),  # Svalbard (vĩ độ rất cao 78°B)
        (-67.5667, -68.1333, "Antarctica/Rothera", True, "O"),  # Nam Cực (trong vòng Nam Cực)
    ],
)
def test_high_latitude_charts_valid_houses_and_angles(
    lat: float, lon: float, tz: str, expect_high_lat: bool, expect_system: str
):
    """Ở vĩ độ cao (kể cả trong vòng cực nơi Placidus suy biến), dịch vụ vẫn trả đủ 12 nhà hợp lệ và ASC/MC chuẩn."""
    chart = compute_birth_chart("2000-06-21", "12:00", lat=lat, lon=lon, tz=tz)
    assert chart["high_latitude"] is expect_high_lat
    assert chart["house_system_used"] == expect_system
    assert len(chart["houses"]) == 12
    for idx, h in enumerate(chart["houses"], start=1):
        assert h["nha"] == idx
        assert 0.0 <= h["kinh_do"] < 360.0
        assert h["cung"]
    assert 0.0 <= chart["asc"] < 360.0
    assert 0.0 <= chart["mc"] < 360.0
    assert _ang_diff(chart["houses"][0]["kinh_do"], chart["asc"]) < 0.1
    assert _ang_diff(chart["houses"][9]["kinh_do"], chart["mc"]) < 0.1


@pytest.mark.parametrize(
    ("bad_lat", "bad_lon"),
    [
        (90.001, 105.85),
        (-95.0, 105.85),
        (21.03, 180.5),
        (21.03, -185.0),
        (float("nan"), 105.85),
    ],
)
def test_invalid_coordinates_rejected_in_vietnamese(bad_lat: float, bad_lon: float):
    with pytest.raises(ValueError) as exc_info:
        validate_coordinates(bad_lat, bad_lon)
    assert any(c in str(exc_info.value) for c in "àáảãạăâđèéêìíòóôơùúưỳý")


# ---------------------------------------------------------------------------
# 4. Đổi múi giờ lịch sử (Historical timezone transitions)
# ---------------------------------------------------------------------------
def test_historical_timezones_saigon_hanoi_and_europe():
    """Kiểm tra chính xác lịch sử đổi múi giờ tại Sài Gòn, Hà Nội (vĩ tuyến 17) và châu Âu (DST)."""
    # 1. Sài Gòn năm 1970 (1960 - 13/06/1975): dùng UTC+8
    sg_1970 = compute_birth_chart("1970-03-21", "23:45", lat=10.78, lon=106.7, tz="Asia/Ho_Chi_Minh")
    assert sg_1970["utc_offset"] == 8.0
    assert sg_1970["utc_datetime"] == "1970-03-21T15:45:00"
    moon_sg_1970 = next(p["kinh_do"] for p in sg_1970["planets"] if p["ten"] == "Moon")
    assert _ang_diff(moon_sg_1970, 164.638) < 0.05

    # 2. Hà Nội cùng ngày giờ 1970-03-21 23:45 (vĩ độ 21.03 > 17.0): giữ UTC+7
    hn_1970 = compute_birth_chart("1970-03-21", "23:45", lat=21.03, lon=105.85, tz="Asia/Ho_Chi_Minh")
    assert hn_1970["utc_offset"] == 7.0
    assert hn_1970["utc_datetime"] == "1970-03-21T16:45:00"
    moon_hn_1970 = next(p["kinh_do"] for p in hn_1970["planets"] if p["ten"] == "Moon")
    # Chênh lệch 1 giờ UT khiến Mặt Trăng dịch chuyển ~0.5 độ
    assert 0.4 < (moon_hn_1970 - moon_sg_1970) < 0.7

    # 3. Sài Gòn năm 1945 (thời kỳ Nhật chiếm đóng 03/1945 - 09/1945): UTC+9
    sg_1945 = compute_birth_chart("1945-05-01", "12:00", lat=10.78, lon=106.7, tz="Asia/Ho_Chi_Minh")
    assert sg_1945["utc_offset"] == 9.0
    assert sg_1945["utc_datetime"] == "1945-05-01T03:00:00"

    # 4. Sài Gòn sau ngày 13/06/1975 (ví dụ 1975-07-01 và 1985-06-15): quay về UTC+7
    sg_1975_after = compute_birth_chart("1975-07-01", "12:00", lat=10.78, lon=106.7, tz="Asia/Ho_Chi_Minh")
    assert sg_1975_after["utc_offset"] == 7.0

    # 5. London: mùa đông GMT (UTC+0) và mùa hè BST (UTC+1)
    lon_winter = compute_birth_chart("1995-12-31", "23:59", lat=51.51, lon=-0.13, tz="Europe/London")
    lon_summer = compute_birth_chart("1995-07-15", "12:00", lat=51.51, lon=-0.13, tz="Europe/London")
    assert lon_winter["utc_offset"] == 0.0
    assert lon_summer["utc_offset"] == 1.0


def test_astro_calc_http_endpoints():
    """Kiểm tra các endpoint HTTP của astro-calc (/v1/health, /source, /v1/positions, /v1/chart)."""
    client = TestClient(app)

    h = client.get("/v1/health")
    assert h.status_code == 200
    assert h.json()["status"] == "ok"
    assert h.json()["service"] == "astro-calc"

    s = client.get("/source")
    assert s.status_code == 200
    assert "AGPL" in s.json()["license"]

    p = client.post(
        "/v1/positions",
        json={"items": [{"utc": "1990-01-01T05:00:00", "lat": 21.03, "lng": 105.85}]},
    )
    assert p.status_code == 200
    item = p.json()["items"][0]
    assert len(item["lon"]) == 13
    assert len(item["cusps"]) == 13
    assert len(item["houses"]) == 12

    c = client.post(
        "/v1/chart",
        json={"ngay_sinh": "1970-03-21", "gio_sinh": "23:45", "lat": 10.78, "lon": 106.7, "tz": "Asia/Ho_Chi_Minh"},
    )
    assert c.status_code == 200
    assert c.json()["schema_version"] == "1.0"
    assert c.json()["utc_offset"] == 8.0

    bad = client.post(
        "/v1/chart",
        json={"ngay_sinh": "1990-02-30", "gio_sinh": "12:00", "lat": 21.03, "lon": 105.85, "tz": "Asia/Ho_Chi_Minh"},
    )
    assert bad.status_code == 422
    assert any(ch in bad.text for ch in "àáảãạăâđèéêìíòóôơùúưỳý")
