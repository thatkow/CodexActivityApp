from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"UTF-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>Codex Prototype</title>
        <style>
          :root {
            color-scheme: light dark;
          }

          body {
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            font-family: Arial, sans-serif;
            background: #f4f7fb;
          }

          .banner {
            width: 100%;
            text-align: center;
            background: linear-gradient(90deg, #2563eb, #7c3aed);
            color: #ffffff;
            padding: 2rem 1rem;
            font-size: clamp(1.2rem, 4vw, 2.2rem);
            font-weight: 700;
            letter-spacing: 0.02em;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
          }
        </style>
      </head>
      <body>
        <div class=\"banner\">Let's prototype with Codex!</div>
      </body>
    </html>
    """
