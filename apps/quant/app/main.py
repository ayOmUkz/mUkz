from fastapi import FastAPI

app = FastAPI(title="Greeks Cockpit Quant Service", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
