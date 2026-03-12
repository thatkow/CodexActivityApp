from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def read_root() -> str:
    return """
    <!DOCTYPE html>
    <html lang=\"en\">
      <head>
        <meta charset=\"UTF-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>Codex Activity App</title>
        <style>
          body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #0f172a;
            font-family: Arial, sans-serif;
          }
          .banner {
            width: 100%;
            text-align: center;
            background: linear-gradient(90deg, #2563eb, #7c3aed);
            color: #fff;
            font-size: clamp(1.5rem, 4vw, 3rem);
            font-weight: 700;
            padding: 1.5rem 1rem;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
          }
        </style>
      </head>
      <body>
        <div class=\"banner\">Let's start building with Codex</div>
      </body>
    </html>
    """
