from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.classifier import classify
from app.schemas import Classification, EnrichedPosition, ForceScores
from app.scoring import compute_force_scores

app = FastAPI(title="Greeks Cockpit Quant Service", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClassifyResponse(BaseModel):
    scores: ForceScores
    classification: Classification


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/classify", response_model=ClassifyResponse)
async def classify_position(position: EnrichedPosition) -> ClassifyResponse:
    scores = compute_force_scores(position)
    classification = classify(position, scores)
    return ClassifyResponse(scores=scores, classification=classification)
