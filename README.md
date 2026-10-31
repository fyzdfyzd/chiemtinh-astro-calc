# astro-calc

Chủ sở hữu: Đinh Trần Tuấn Linh. Copyright (C) 2026 Đinh Trần Tuấn Linh.

Dịch vụ HTTP nhỏ tính vị trí thiên thể bằng [Kerykeion](https://github.com/g-battaglia/kerykeion) (dùng nguyên bản, không sửa).
Giấy phép: **AGPL-3.0-or-later** (xem `LICENSE`), giống Kerykeion và libephemeris.

Engine báo cáo `astro-engine` chỉ gọi dịch vụ này qua HTTP và không import Kerykeion.
Thư mục này là phần phải công bố mã nguồn khi cho người khác dùng qua mạng (AGPL §13);
đặt `ASTRO_CALC_SOURCE_URL` trỏ tới nơi công bố, endpoint `/source` và `/v1/health` sẽ trả về địa chỉ đó.

```
pip install -e .            # hoặc: uv pip install -e .
astro-calc --port 8027
curl -X POST localhost:8027/v1/positions -H "content-type: application/json" \
     -d '{"items":[{"utc":"1985-06-15T01:30:00","lat":21.0285,"lng":105.8542}]}'
```

| Endpoint | Trả về |
|---|---|
| `POST /v1/positions` | Mỗi thời điểm: `lon`, `speed`, `decl` của 13 thiên thể (Mặt Trời → Diêm Vương, Chiron, Lilith trung bình, La Hầu thật), `cusps[0..12]` Placidus, `asc`, `mc`, `vertex`, `asc_decl`, `mc_decl`. Tối đa 2000 thời điểm một lần gọi. |
| `POST /v1/wheel` | Vòng bản đồ SVG mặc định của Kerykeion, nhãn tiếng Việt |
| `GET /v1/health` | Phiên bản Kerykeion, backend |
| `GET /source` | Nơi lấy mã nguồn |

Biến môi trường: `KERYKEION_BACKEND=swisseph` + `ASTRO_CALC_EPHE_DIR=<thư mục .se1>` để dùng Swiss Ephemeris.
