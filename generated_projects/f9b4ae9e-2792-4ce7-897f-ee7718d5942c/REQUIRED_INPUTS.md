# Required Inputs

Fill these values in `.env` before running the project.

| Name | Required | Example | Where To Enter | Purpose |
|---|---|---|---|---|
| APP_ENV | No | development | .env | Application environment name. |
| PORT | No | 8000 | .env | Local port used when the backend starts from the generated run scripts. |
| DATABASE_URL | Yes | mysql://root:password@localhost:3306/app_db | Terminal prompt or .env | MySQL connection string for the backend database. |
| VITE_API_BASE_URL | No | http://localhost:8000 | .env | Frontend base URL for backend API calls. |
