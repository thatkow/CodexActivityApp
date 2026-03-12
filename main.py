from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>Codex Prototype</title>
        <style>
          body {
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f5f8ff;
            font-family: Arial, sans-serif;
          }

          .banner {
            width: 100%;
            text-align: center;
            background: #1f3b95;
            color: #ffffff;
            padding: 1.25rem 1rem;
            font-size: clamp(1.25rem, 3vw, 2rem);
            font-weight: 700;
            letter-spacing: 0.02em;
            box-shadow: 0 6px 20px rgba(31, 59, 149, 0.25);
          }
        </style>
      </head>
      <body>
        <div class=\"banner\">Let's prototype with Codex!</div>
      </body>
    </html>
    """
