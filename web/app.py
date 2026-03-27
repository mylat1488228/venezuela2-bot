from fastapi import FastAPI
import os

app = FastAPI(title="Venezuela2 Dashboard")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Venezuela2 Bot Dashboard", "bot": "online"}

@app.get("/health")
async def health():
    return {"status": "alive", "timestamp": str(datetime.datetime.now())}

if __name__ == "__main__":
    import uvicorn
    import datetime
    port = int(os.getenv("PORT", 8000))
    print(f"🌐 Запуск веб-сервера на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
