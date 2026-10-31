"""astro-calc: dịch vụ tính vị trí thiên thể bọc Kerykeion (AGPL-3.0).

Đây là phần duy nhất của hệ thống chạy Kerykeion. Engine báo cáo gọi dịch vụ này qua HTTP,
không import Kerykeion. Kerykeion dùng nguyên bản, không sửa.
"""

import logging
import os

__version__ = "1.0.0"

# Kerykeion đọc các biến này lúc import, nên phải đặt trước khi import kerykeion.
if os.environ.get("KERYKEION_BACKEND", "").lower() == "swisseph" and os.environ.get("ASTRO_CALC_EPHE_DIR"):
    os.environ.setdefault("KERYKEION_EPHE_PATH", os.environ["ASTRO_CALC_EPHE_DIR"])

# libephemeris cảnh báo mỗi lần tính Chiron bằng nghiệm Kepler; độ lệch đã được đo (dưới 0,1°).
os.environ.setdefault("LIBEPHEMERIS_LOG_LEVEL", "ERROR")
logging.getLogger("libephemeris").setLevel(logging.ERROR)
