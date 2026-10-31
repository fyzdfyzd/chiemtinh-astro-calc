"""Vị trí thiên thể từ Kerykeion (không sửa thư viện), trả về đúng bố cục mà swetest cung cấp cho code PHP cũ.

Lệnh PHP cũ: ``swetest -p0123456789DAttt -eswe -house<lng>,<lat>,P -flsj``
  → Mặt Trời..Diêm Vương, Chiron (D), Lilith trung bình (A), La Hầu thật (t),
    12 đỉnh nhà Placidus, rồi Asc, MC, ARMC, Vertex.
Lệnh cosmodyne: ``-fPldj`` thêm xích vĩ cho 10 hành tinh và các đỉnh nhà.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time as dtime, timedelta
import math
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from kerykeion import AstrologicalSubjectFactory
from kerykeion.ephemeris_backend.backend import ephe

BODIES = [
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
    "chiron",
    "mean_lilith",
    "true_north_lunar_node",
]
PLANET_NAMES_EN = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "Chiron",
    "Lilith",
    "North Node",
]
PLANET_NAMES_VI = [
    "Mặt Trời",
    "Mặt Trăng",
    "Thủy Tinh",
    "Kim Tinh",
    "Hỏa Tinh",
    "Mộc Tinh",
    "Thổ Tinh",
    "Thiên Vương",
    "Hải Vương",
    "Diêm Vương",
    "Chiron",
    "Lilith",
    "La Hầu",
]
SIGN_NAMES_VI = [
    "Bạch Dương",
    "Kim Ngưu",
    "Song Tử",
    "Cự Giải",
    "Sư Tử",
    "Xử Nữ",
    "Thiên Bình",
    "Bọ Cạp",
    "Nhân Mã",
    "Ma Kết",
    "Bảo Bình",
    "Song Ngư",
]
SIGN_NAMES_EN = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]
_ACTIVE_POINTS = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "Chiron",
    "Mean_Lilith",
    "True_North_Lunar_Node",
    "Vertex",
    "Ascendant",
    "Medium_Coeli",
]
_HOUSE_ATTRS = [
    "first_house",
    "second_house",
    "third_house",
    "fourth_house",
    "fifth_house",
    "sixth_house",
    "seventh_house",
    "eighth_house",
    "ninth_house",
    "tenth_house",
    "eleventh_house",
    "twelfth_house",
]

# Vĩ tuyến 17: miền Bắc Việt Nam giữ UTC+7 suốt 1960–1975, trong khi tzdata
# Asia/Ho_Chi_Minh ghi UTC+8 cho giai đoạn đó (giờ Sài Gòn).
_VN_DMZ_LAT = 17.0
_POLAR_CIRCLE_LAT = 66.56
_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")


def parse_birth_date(raw: str | date) -> date:
    """Kiểm tra và phân tích ngày sinh YYYY-MM-DD (bao gồm kiểm tra năm nhuận)."""
    if isinstance(raw, date) and not isinstance(raw, datetime):
        parsed = raw
    elif isinstance(raw, str):
        text = raw.strip()
        m = _DATE_RE.match(text)
        if not m:
            raise ValueError("Ngày sinh không đúng định dạng YYYY-MM-DD")
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            parsed = date(y, mo, d)
        except ValueError as exc:
            raise ValueError(f"Ngày sinh '{text}' không hợp lệ trên lịch (kiểm tra tháng và năm nhuận)") from exc
    else:
        raise ValueError("Ngày sinh không hợp lệ")

    if not (1850 <= parsed.year <= 2150):
        raise ValueError("Năm sinh phải nằm trong khoảng từ 1850 đến 2150")
    return parsed


def parse_birth_time(raw: str | dtime | None) -> tuple[dtime, bool]:
    """Phân tích giờ sinh HH:MM (hoặc HH:MM:SS). Trả về (time, unknown_time)."""
    if raw is None:
        return dtime(12, 0), True
    if isinstance(raw, dtime):
        return raw, False
    if not isinstance(raw, str):
        raise ValueError("Giờ sinh không đúng định dạng HH:MM")
    text = raw.strip()
    if not text:
        return dtime(12, 0), True
    m = _TIME_RE.match(text)
    if not m:
        raise ValueError("Giờ sinh không hợp lệ, cần theo định dạng HH:MM (00:00–23:59)")
    hh = int(m.group(1))
    mm = int(m.group(2))
    ss = int(m.group(3) or 0)
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
        raise ValueError("Giờ sinh không hợp lệ, giờ phải từ 00 đến 23 và phút từ 00 đến 59")
    return dtime(hh, mm, ss), False


def validate_coordinates(lat: float, lon: float) -> tuple[float, float]:
    """Kiểm tra vĩ độ (-90..90) và kinh độ (-180..180)."""
    if isinstance(lat, bool) or not isinstance(lat, (int, float)) or math.isnan(lat) or math.isinf(lat):
        raise ValueError("Vĩ độ (lat) phải là số thực hợp lệ")
    if isinstance(lon, bool) or not isinstance(lon, (int, float)) or math.isnan(lon) or math.isinf(lon):
        raise ValueError("Kinh độ (lon) phải là số thực hợp lệ")
    lat_f = float(lat)
    lon_f = float(lon)
    if not (-90.0 <= lat_f <= 90.0):
        raise ValueError("Vĩ độ (lat) phải nằm trong khoảng từ -90 đến 90 độ")
    if not (-180.0 <= lon_f <= 180.0):
        raise ValueError("Kinh độ (lon) phải nằm trong khoảng từ -180 đến 180 độ")
    return lat_f, lon_f


def utc_offset_hours(tz_name: str, local: datetime, lat: float | None = None) -> float:
    """Tính độ lệch giờ UTC theo múi giờ IANA lịch sử (có xét vĩ tuyến 17 Việt Nam giai đoạn 1960–1975)."""
    if not isinstance(tz_name, str) or not tz_name.strip():
        raise ValueError("Múi giờ (tz) không được để trống")
    clean_tz = tz_name.strip()
    try:
        ZoneInfo(clean_tz)
    except (ZoneInfoNotFoundError, KeyError, ValueError) as exc:
        raise ValueError(f"Múi giờ '{clean_tz}' không hợp lệ theo chuẩn IANA") from exc

    effective_tz = clean_tz
    if clean_tz in ("Asia/Ho_Chi_Minh", "Asia/Saigon") and lat is not None and lat > _VN_DMZ_LAT:
        effective_tz = "Asia/Bangkok"

    offset = local.replace(tzinfo=ZoneInfo(effective_tz)).utcoffset()
    if offset is None:
        raise ValueError(f"Không xác định được độ lệch giờ cho múi giờ '{clean_tz}'")
    return offset.total_seconds() / 3600.0


def local_to_utc(local: datetime, offset_hours: float) -> datetime:
    """Giờ địa phương (naive) + độ lệch giờ → datetime UTC (aware)."""
    return (local - timedelta(hours=offset_hours)).replace(tzinfo=UTC)


def true_obliquity(utc: datetime) -> float:
    """Độ nghiêng hoàng đạo thật (có chương động), như swetest dùng để đổi đỉnh nhà sang xích vĩ."""
    jd = ephe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60 + utc.second / 3600)
    values, _ = ephe.calc_ut(jd, ephe.ECL_NUT, 0)
    return float(values[0])


def ecliptic_declination(lon: float, obliquity: float) -> float:
    return math.degrees(math.asin(math.sin(math.radians(obliquity)) * math.sin(math.radians(lon))))


def compute_positions(utc: datetime, lat: float, lng: float, *, unknown_time: bool = False) -> dict:
    """Tính vị trí cho một thời điểm UT tại toạ độ cho trước (hệ nhà Placidus, hoàng đạo nhiệt đới)."""
    lat_f, lng_f = validate_coordinates(lat, lng)
    subject = AstrologicalSubjectFactory.from_birth_data(
        "chart",
        utc.year,
        utc.month,
        utc.day,
        utc.hour,
        utc.minute,
        seconds=utc.second,
        lng=lng_f,
        lat=lat_f,
        tz_str="UTC",
        online=False,
        houses_system_identifier="P",
        zodiac_type="Tropical",
        active_points=_ACTIVE_POINTS,
        calculate_lunar_phase=False,
        suppress_geonames_warning=True,
    )
    points = [getattr(subject, name) for name in BODIES]
    raw_cusps = [0.0] + [float(getattr(subject, attr).abs_pos) for attr in _HOUSE_ATTRS]
    asc_point = subject.ascendant
    mc_point = subject.medium_coeli

    eps = true_obliquity(utc)

    def decl_of(point, lon: float) -> float:
        value = getattr(point, "declination", None)
        return float(value) if value is not None else ecliptic_declination(lon, eps)

    cusps = [0.0] + [30.0 * i for i in range(12)] if unknown_time else raw_cusps
    houses = [] if unknown_time else [float(c) for c in raw_cusps[1:13]]

    return {
        "lon": [float(p.abs_pos) for p in points],
        "speed": [float(p.speed or 0.0) for p in points],
        "decl": [decl_of(p, p.abs_pos) for p in points],
        "cusps": [float(c) for c in cusps],
        "houses": houses,
        "asc": float(asc_point.abs_pos),
        "mc": float(mc_point.abs_pos),
        "vertex": float(subject.vertex.abs_pos),
        # Đỉnh nhà nằm trên hoàng đạo (vĩ độ 0) nên xích vĩ suy thẳng từ kinh độ, như swetest.
        "asc_decl": ecliptic_declination(asc_point.abs_pos, eps),
        "mc_decl": ecliptic_declination(mc_point.abs_pos, eps),
        "unknown_time": bool(unknown_time),
        "high_latitude": abs(lat_f) >= _POLAR_CIRCLE_LAT,
        "house_system_used": "O" if abs(lat_f) >= _POLAR_CIRCLE_LAT else "P",
    }


def compute_birth_chart(
    ngay_sinh: str | date,
    gio_sinh: str | dtime | None = None,
    lat: float = 21.03,
    lon: float = 105.85,
    tz: str = "Asia/Ho_Chi_Minh",
    *,
    gio_khong_ro: bool = False,
) -> dict:
    """Tính lá số từ thông tin sinh địa phương (kiểm tra hợp lệ, đổi múi giờ lịch sử sang UTC, xử lý giờ không rõ)."""
    b_date = parse_birth_date(ngay_sinh)
    b_time, time_missing = parse_birth_time(gio_sinh)
    unknown = bool(gio_khong_ro or time_missing)
    if unknown:
        b_time = dtime(12, 0)
    lat_f, lon_f = validate_coordinates(lat, lon)
    local_dt = datetime.combine(b_date, b_time)
    offset = utc_offset_hours(tz, local_dt, lat_f)
    utc_dt = local_to_utc(local_dt, offset).replace(tzinfo=None)
    raw = compute_positions(utc_dt, lat_f, lon_f, unknown_time=unknown)

    planets = []
    for idx, key in enumerate(BODIES):
        lon_deg = float(raw["lon"][idx]) % 360.0
        sign_idx = int(lon_deg // 30) % 12
        planets.append(
            {
                "key": key,
                "ten": PLANET_NAMES_EN[idx],
                "ten_vi": PLANET_NAMES_VI[idx],
                "kinh_do": round(lon_deg, 6),
                "cung": SIGN_NAMES_VI[sign_idx],
                "cung_en": SIGN_NAMES_EN[sign_idx],
                "do_trong_cung": round(lon_deg % 30.0, 4),
                "toc_do": round(float(raw["speed"][idx]), 6),
                "nghich_hanh": float(raw["speed"][idx]) < 0.0,
                "xich_vi": round(float(raw["decl"][idx]), 6),
            }
        )

    houses = []
    if not unknown:
        for h_idx, cusp_deg in enumerate(raw["houses"], start=1):
            c_deg = float(cusp_deg) % 360.0
            s_idx = int(c_deg // 30) % 12
            houses.append(
                {
                    "nha": h_idx,
                    "kinh_do": round(c_deg, 6),
                    "cung": SIGN_NAMES_VI[s_idx],
                    "cung_en": SIGN_NAMES_EN[s_idx],
                }
            )

    return {
        "schema_version": "1.0",
        "planets": planets,
        "houses": houses,
        "asc": None if unknown else round(float(raw["asc"]) % 360.0, 6),
        "mc": None if unknown else round(float(raw["mc"]) % 360.0, 6),
        "utc_offset": offset,
        "utc_datetime": utc_dt.isoformat(timespec="seconds"),
        "local_datetime": local_dt.isoformat(timespec="seconds"),
        "gio_khong_ro": unknown,
        "high_latitude": raw["high_latitude"],
        "house_system_used": None if unknown else raw["house_system_used"],
        "raw": raw,
    }
