# Required Inputs

Fill these values in `.env` before running the project.

| Name | Required | Example | Where To Enter | Purpose |
|---|---|---|---|---|
| APP_ENV | No | development | .env | Application environment name. |
| PORT | No | 8000 | .env | Local port used when the backend starts from the generated run scripts. |
| DATABASE_URL | Yes | sqlite:///./app.db | Terminal prompt or .env | SQLite connection string for local development. |
| VITE_API_BASE_URL | No | http://localhost:8000 | .env | Frontend base URL for backend API calls. |
