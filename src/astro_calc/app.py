"""API HTTP của astro-calc.

POST /v1/positions   {"items": [{"utc": "1985-06-15T01:30:00", "lat": 21.03, "lng": 105.85}, ...]}
POST /v1/chart       {"ngay_sinh": "1990-01-01", "gio_sinh": "12:00", "lat": 21.03, "lon": 105.85, "tz": "Asia/Ho_Chi_Minh"}
POST /v1/wheel       vòng bản đồ SVG mặc định của Kerykeion
GET  /v1/health      phiên bản Kerykeion, backend
GET  /source         nơi lấy mã nguồn (AGPL-3.0 §13)
"""

from __future__ import annotations

from datetime import UTC, datetime
import importlib.metadata
import os
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import astro_calc
from astro_calc.positions import compute_birth_chart, compute_positions

SOURCE_URL = os.environ.get("ASTRO_CALC_SOURCE_URL", "")

app = FastAPI(title="astro-calc", version=astro_calc.__version__, license_info={"name": "AGPL-3.0-or-later"})


@app.exception_handler(RequestValidationError)
async def _handle_validation_error(_request: Request, exc: RequestValidationError):
    messages: list[str] = []
    for err in exc.errors():
        msg = str(err.get("msg", ""))
        if msg.startswith("Value error, "):
            messages.append(msg.removeprefix("Value error, "))
        else:
            loc = ".".join(str(part) for part in err.get("loc", []) if part != "body")
            messages.append(f"Trường '{loc}' không đúng định dạng" if loc else "Dữ liệu gửi lên không đúng định dạng")
    return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})


@app.exception_handler(ValueError)
async def _handle_value_error(_request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


class When(BaseModel):
    utc: datetime
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    unknown_time: bool = False


class PositionsRequest(BaseModel):
    items: list[When] = Field(min_length=1, max_length=2000)


class BirthChartRequest(BaseModel):
    ngay_sinh: Any
    gio_sinh: Any = None
    lat: Any = 21.03
    lon: Any = 105.85
    tz: Any = "Asia/Ho_Chi_Minh"
    gio_khong_ro: bool = False


class WheelRequest(BaseModel):
    name: str
    local: datetime
    offset_hours: float
    lat: float
    lng: float
    city: str = ""
    full: bool = True


@app.get("/v1/health")
def health():
    return {
        "status": "ok",
        "service": "astro-calc",
        "version": astro_calc.__version__,
        "kerykeion": importlib.metadata.version("kerykeion"),
        "backend": os.environ.get("KERYKEION_BACKEND", "libephemeris"),
        "license": "AGPL-3.0-or-later",
        "source": SOURCE_URL or "/source",
    }


@app.get("/source")
def source():
    """AGPL §13: người dùng qua mạng phải lấy được mã nguồn của dịch vụ này."""
    return {
        "license": "AGPL-3.0-or-later",
        "source": SOURCE_URL or "Mã nguồn astro-calc gửi kèm theo yêu cầu; liên hệ chiemtinh.vn",
        "kerykeion": "https://github.com/g-battaglia/kerykeion",
    }


@app.post("/v1/positions")
def positions(req: PositionsRequest):
    out = []
    for w in req.items:
        utc = w.utc if w.utc.tzinfo is None else w.utc.astimezone(UTC).replace(tzinfo=None)
        out.append(compute_positions(utc, w.lat, w.lng, unknown_time=w.unknown_time))
    return {"items": out}


@app.post("/v1/chart")
def chart(req: BirthChartRequest):
    return compute_birth_chart(
        ngay_sinh=req.ngay_sinh,
        gio_sinh=req.gio_sinh,
        lat=req.lat,
        lon=req.lon,
        tz=req.tz,
        gio_khong_ro=req.gio_khong_ro,
    )


@app.post("/v1/wheel", response_class=Response)
def wheel(req: WheelRequest):
    from astro_calc.wheel import natal_wheel

    svg = natal_wheel(req.name, req.local, req.offset_hours, req.lat, req.lng, city=req.city, full=req.full)
    return Response(svg, media_type="image/svg+xml")


def main() -> None:
    import argparse

    import uvicorn

    ap = argparse.ArgumentParser(prog="astro-calc")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8027)
    args = ap.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)
