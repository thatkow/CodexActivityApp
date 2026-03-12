from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get('/', response_class=HTMLResponse)
def read_root() -> str:
    return """
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>CodexActivityApp</title>
        <style>
          body {
            font-family: Arial, sans-serif;
            min-height: 100vh;
            display: grid;
            place-items: center;
            margin: 0;
            background: #0f172a;
            color: #e2e8f0;
          }
          h1 {
            font-size: clamp(2rem, 5vw, 3.5rem);
            margin: 0;
          }
        </style>
      </head>
      <body>
        <h1>Codex built this!</h1>
      </body>
    </html>
    """
