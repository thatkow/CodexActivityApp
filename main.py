from fastapi import FastAPI

app = FastAPI(title="CodexActivityApp")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Codex built this!"}
