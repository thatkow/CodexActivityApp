from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def read_root() -> str:
    return "<h1>Codex built this!</h1>"
