from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def read_root() -> str:
    return """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Codex Activity App</title>
  <style>
    html, body {
      margin: 0;
      height: 100%;
      font-family: Arial, sans-serif;
      background: #f7fafc;
    }

    .banner {
      width: 100%;
      background: linear-gradient(90deg, #2563eb, #7c3aed);
      color: #ffffff;
      text-align: center;
      font-size: clamp(1.5rem, 4vw, 2.5rem);
      font-weight: 700;
      letter-spacing: 0.02em;
      padding: 2rem 1rem;
      box-sizing: border-box;
    }

    .page {
      min-height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
    }
  </style>
</head>
<body>
  <div class=\"page\">
    <div class=\"banner\">Let's start building with Codex</div>
  </div>
</body>
</html>
"""
