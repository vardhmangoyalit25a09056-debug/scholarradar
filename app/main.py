from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

load_dotenv()

from . import pipeline  # noqa: E402
from .matcher import Profile, rank  # noqa: E402

app = FastAPI(title="ScholarRadar")
STATIC = Path(__file__).resolve().parent.parent / "static"


class ProfileIn(BaseModel):
    state: str = ""
    category: str = ""
    annual_income: int | None = None
    course: str = ""
    percentage: float | None = None
    gender: str = ""


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.post("/api/match")
def match(body: ProfileIn):
    p = Profile(**body.model_dump())
    out = pipeline.run(p)
    ranked = rank(out["schemes"], p)
    return {
        "matches": [{**r.scheme, "days_left": r.days_left, "to_verify": r.to_verify}
                    for r in ranked],
        "stats": out["stats"],
    }
