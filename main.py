from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
    <!DOCTYPE html>
    <html lang=\"en\">
      <head>
        <meta charset=\"UTF-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>Codex Activity App</title>
        <style>
          * {
            box-sizing: border-box;
          }

          body {
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            background: #0f172a;
            font-family: Arial, Helvetica, sans-serif;
          }

          .banner {
            width: 100%;
            max-width: 960px;
            padding: 2rem;
            text-align: center;
            color: #f8fafc;
            background: linear-gradient(90deg, #2563eb, #7c3aed);
            border-radius: 0.75rem;
            font-size: clamp(1.5rem, 3vw, 2.25rem);
            font-weight: 700;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
          }
        </style>
      </head>
      <body>
        <div class=\"banner\">Let's start building with Codex</div>
      </body>
    </html>
    """
