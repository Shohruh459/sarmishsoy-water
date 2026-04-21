from fastapi import FastAPI

app = FastAPI(title="Sarmishsoy Water API")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Sarmishsoy Water API ishlayapti!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}