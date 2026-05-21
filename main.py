import uvicorn
from src.config import config
from src.server import app

if __name__ == "__main__":
    uvicorn.run(
        "src.server:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level="info",
    )
