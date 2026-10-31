"""Vòng bản đồ sao (SVG) vẽ bằng ChartDrawer của Kerykeion, nhãn tiếng Việt."""

from __future__ import annotations

import copy
import re
from datetime import datetime, timedelta

from kerykeion import AstrologicalSubjectFactory, ChartDataFactory, ChartDrawer
from kerykeion.settings.translation_strings import LANGUAGE_SETTINGS

WHEEL_POINTS = [
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
    "True_North_Lunar_Node",
    "Chiron",
    "Mean_Lilith",
    "Ascendant",
    "Medium_Coeli",
]

_VI_OVERRIDES: dict = {
    "info": "Thông tin",
    "cusp": "Đỉnh nhà",
    "longitude": "Kinh độ",
    "latitude": "Vĩ độ",
    "north": "Bắc",
    "east": "Đông",
    "south": "Nam",
    "west": "Tây",
    "fire": "Lửa",
    "earth": "Đất",
    "air": "Khí",
    "water": "Nước",
    "and_word": "và",
    "transits": "Quá cảnh của",
    "type": "Loại",
    "couple_aspects": "Góc chiếu cặp đôi",
    "synastry_aspects": "Góc chiếu tương hợp",
    "transit_aspects": "Góc chiếu quá cảnh",
    "planets_and_house": "Các điểm của",
    "transit_name": "Thời điểm quá cảnh",
    "lunar_phase": "Pha Mặt Trăng",
    "day": "Ngày",
    "houses": "Hệ nhà",
    "houses_system_P": "Placidus",
    "Natal": "Bản đồ sao cá nhân",
    "Synastry": "Bản đồ sao cặp đôi",
    "Transit": "Quá cảnh",
    "Composite": "Bản đồ hợp nhất",
    "natal": "Cá nhân",
    "transit": "Quá cảnh",
    "house": "Nhà",
    "location": "Nơi sinh",
    "elements": "Nguyên tố",
    "qualities": "Tính chất",
    "cardinal": "Tiên phong",
    "fixed": "Kiên định",
    "mutable": "Linh hoạt",
    "birth_chart": "Bản đồ sao",
    "diurnality": "Ngày/đêm",
    "diurnal": "Sinh ban ngày",
    "nocturnal": "Sinh ban đêm",
    "domification": "Hệ nhà",
    "perspective_type": "Góc nhìn",
    "apparent_geocentric": "Địa tâm",
    "new_moon": "Trăng non",
    "waxing_crescent": "Trăng lưỡi liềm đầu tháng",
    "first_quarter": "Bán nguyệt đầu tháng",
    "waxing_gibbous": "Trăng khuyết đầu tháng",
    "full_moon": "Trăng tròn",
    "waning_gibbous": "Trăng khuyết cuối tháng",
    "last_quarter": "Bán nguyệt cuối tháng",
    "waning_crescent": "Trăng lưỡi liềm cuối tháng",
    "tropical": "Nhiệt đới",
    "zodiac": "Hoàng đạo",
    "day_of_week": "Thứ",
    "weekdays": {
        "Monday": "Thứ Hai",
        "Tuesday": "Thứ Ba",
        "Wednesday": "Thứ Tư",
        "Thursday": "Thứ Năm",
        "Friday": "Thứ Sáu",
        "Saturday": "Thứ Bảy",
        "Sunday": "Chủ Nhật",
    },
    "celestial_points": {
        "Sun": "Mặt Trời",
        "Moon": "Mặt Trăng",
        "Mercury": "Sao Thủy",
        "Venus": "Sao Kim",
        "Mars": "Sao Hỏa",
        "Jupiter": "Sao Mộc",
        "Saturn": "Sao Thổ",
        "Uranus": "Thiên Vương",
        "Neptune": "Hải Vương",
        "Pluto": "Diêm Vương",
        "Ascendant": "Cung Mọc",
        "Medium_Coeli": "Thiên Đỉnh",
        "Descendant": "Cung Lặn",
        "Imum_Coeli": "Thiên Để",
        "True_North_Lunar_Node": "La Hầu",
        "Chiron": "Chiron",
        "Mean_Lilith": "Lilith",
    },
}


def _merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


# Gói ngôn ngữ phải đủ mọi khoá: lấy gói tiếng Anh làm nền rồi ghi đè phần tiếng Việt.
VI_PACK = _merge(LANGUAGE_SETTINGS["EN"], _VI_OVERRIDES)
VI_PACK["chart_info_natal_label"] = "Cá nhân"
VI_PACK["chart_info_transit_label"] = "Quá cảnh"


def fixed_tz_name(offset_hours: float) -> str:
    """Tên múi giờ cố định IANA (Etc/GMT-7 = UTC+7) để Kerykeion không tự áp giờ mùa hè khác ta."""
    if float(offset_hours).is_integer():
        n = int(offset_hours)
        return "UTC" if n == 0 else f"Etc/GMT{-n:+d}"
    return "UTC"


def _subject(name: str, local: datetime, offset_hours: float, lat: float, lng: float, city: str = ""):
    tz = fixed_tz_name(offset_hours)
    when = local if tz != "UTC" or offset_hours == 0 else local - timedelta(hours=offset_hours)
    return AstrologicalSubjectFactory.from_birth_data(
        name or "Bản đồ sao",
        when.year,
        when.month,
        when.day,
        when.hour,
        when.minute,
        lng=lng,
        lat=lat,
        tz_str=tz,
        city=city or "—",
        nation="VN",
        online=False,
        houses_system_identifier="P",
        active_points=WHEEL_POINTS,
        suppress_geonames_warning=True,
    )


def _clean(svg: str) -> str:
    # Bỏ khai báo XML để nhúng thẳng vào HTML.
    return re.sub(r"^<\?xml[^>]*>\s*", "", svg.strip())


def _drawer(data, title: str | None) -> ChartDrawer:
    return ChartDrawer(
        data,
        theme="classic",
        chart_language="VI",
        language_pack=VI_PACK,
        custom_title=title,
        style="modern",
        transparent_background=True,
    )


def natal_wheel(
    name: str, local: datetime, offset_hours: float, lat: float, lng: float, *, city: str = "", full: bool = False
) -> str:
    subject = _subject(name, local, offset_hours, lat, lng, city)
    data = ChartDataFactory.create_natal_chart_data(subject, active_points=WHEEL_POINTS)
    drawer = _drawer(data, None)
    return _clean(drawer.generate_svg_string() if full else drawer.generate_wheel_only_svg_string())


def synastry_wheel(a: dict, b: dict, *, full: bool = False) -> str:
    """a, b: dict(name, local, offset, lat, lng)."""
    sa = _subject(a["name"], a["local"], a["offset"], a["lat"], a["lng"], a.get("city", ""))
    sb = _subject(b["name"], b["local"], b["offset"], b["lat"], b["lng"], b.get("city", ""))
    data = ChartDataFactory.create_synastry_chart_data(sa, sb, active_points=WHEEL_POINTS)
    drawer = _drawer(data, None)
    return _clean(drawer.generate_svg_string() if full else drawer.generate_wheel_only_svg_string())


def transit_wheel(natal: dict, when: datetime, offset_hours: float, *, full: bool = False) -> str:
    sn = _subject(natal["name"], natal["local"], natal["offset"], natal["lat"], natal["lng"], natal.get("city", ""))
    st = _subject("Quá cảnh", when, offset_hours, natal["lat"], natal["lng"], natal.get("city", ""))
    data = ChartDataFactory.create_transit_chart_data(sn, st, active_points=WHEEL_POINTS)
    drawer = _drawer(data, None)
    return _clean(drawer.generate_svg_string() if full else drawer.generate_wheel_only_svg_string())
