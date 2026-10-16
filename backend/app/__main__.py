"""Demo command: `python -m app` serves app.main:app on Settings().HOST:PORT."""

import uvicorn

from app.config import Settings

if __name__ == "__main__":
    settings = Settings()
    # app.main configures the 'app' logger on import, so its INFO/ERROR lines show.
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT)
