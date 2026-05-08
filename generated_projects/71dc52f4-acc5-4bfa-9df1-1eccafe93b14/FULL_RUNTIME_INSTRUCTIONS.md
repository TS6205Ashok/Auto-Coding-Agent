# Full Runtime Instructions

## 1. PROJECT OVERVIEW
- Project: Create Todo App
- Generated version: Project Agent Generated Starter v1
- What this project does: Create Todo App is a 100% runnable starter project built around React + Spring Boot. Fast Mode uses backend templates for all standard project structure so output quality stays complete while generation remains fast.
- Tech stack used:
- Language: Java
- Frontend: React
- Backend: Spring Boot
- Database: MySQL
- AI / Tools: None
- Deployment: Render
- What should happen when it runs successfully: The backend server starts, the frontend opens or becomes available locally, and the UI can talk to the API.

## 2. RECOMMENDED IDE
- Primary IDE: IntelliJ IDEA
- Alternative IDE: VS Code

## Generated Project Identity
- Project name: Create Todo App
- Generated version: Project Agent Generated Starter v1
- Main file: `backend/src/main/java/com/example/app/Application.java`
- Run command: `cd backend && mvn spring-boot:run`
- Selected Stack:
- Language: Java
- Frontend: React
- Backend: Spring Boot
- Database: MySQL
- AI / Tools: None
- Deployment: Render

## 3. REQUIRED EXTENSIONS / PLUGINS
- IntelliJ IDEA: Java support (built in)
- IntelliJ IDEA: Spring Boot plugin
- VS Code alternative: Extension Pack for Java

## 4. SYSTEM REQUIREMENTS
- Git and a terminal available inside your IDE.
- Node.js 18+ (20+ recommended).
- Java 17+ and Maven 3.9+.
- Runtime tools used by this stack: JDK 17+, Maven.

## 5. STEP-BY-STEP SETUP INSTRUCTIONS
1. Open the unzipped project folder in your IDE.
2. Open the integrated terminal in the IDE.
3. Review `.env.example` and `REQUIRED_INPUTS.md` before starting.
4. Install Java dependencies with Maven.
   - Example: `mvn install`
   - Alternate command: `cd backend`
   - Alternate command: `mvn clean install`
5. Save your changes and keep the terminal open for the run step.

## 6. REQUIRED INPUTS (API KEYS / CONFIG)
- `APP_ENV` (optional): Application environment name.
- `PORT` (optional): Local port used when the backend starts from the generated run scripts.
- `DATABASE_URL` (required): MySQL connection string for the backend database.
- `VITE_API_BASE_URL` (optional): Frontend base URL for backend API calls.

| Input Name | Required | Example | Where To Enter | Purpose |
|---|---|---|---|---|
| APP_ENV | No | development | .env | Application environment name. |
| PORT | No | 8000 | .env | Local port used when the backend starts from the generated run scripts. |
| DATABASE_URL | Yes | mysql://root:password@localhost:3306/app_db | Terminal prompt or .env | MySQL connection string for the backend database. |
| VITE_API_BASE_URL | No | http://localhost:8000 | .env | Frontend base URL for backend API calls. |

## 7. HOW RUNTIME INPUT WORKS
- Use `.env.example` to create a `.env` file if the project expects configuration values.
- If a runtime prompt is implemented for this stack, enter the requested value in the terminal and execution will continue.

## 8. HOW TO RUN THE PROJECT
- Open main file: `backend/src/main/java/com/example/app/Application.java`
- Run method: `Click IDE Play button or run mvn spring-boot:run`
- Primary run command: `cd backend && mvn spring-boot:run`
- Local URL: `http://localhost:8080`
- IDE Play button: open `.vscode/launch.json`, choose the generated run configuration, and click Run/Play.
- VS Code Run Task: press Ctrl+Shift+P, choose `Tasks: Run Task`, then select `Run Project`.
- Windows: `run.bat`
- Mac/Linux: `chmod +x run.sh` then `./run.sh`
- Manual backend run: `mvn spring-boot:run`
- Additional run command: `cd backend`
- Additional run command: `mvn spring-boot:run`

## 9. EXPECTED OUTPUT
- Success looks like this: The backend server starts, the frontend opens or becomes available locally, and the UI can talk to the API.
- Problem statement handled by this starter: create todo app

## 10. TROUBLESHOOTING
- If the project does not start, confirm the required dependencies were installed successfully.
- Verify the required language/runtime versions from the System Requirements section.
- Restart the IDE terminal and run the setup and run steps again.
- If an API or configuration error occurs, check the values in `.env` or re-enter them when prompted.
- Ensure your internet connection is available for any external API integrations.
- Confirm these runtime tools are installed and available: JDK 17+, Maven.
- If an unknown error occurs: stop the program, return to the setup steps, rerun them from the beginning, then start the project again.

## 11. RESET INSTRUCTIONS
- Delete the `.env` file if you want the project to prompt for values again.
- Reinstall dependencies using the setup instructions if the environment became inconsistent.
- Run the project again after the reset steps complete.
- If needed, delete `node_modules` and reinstall with `npm install`.
- If needed, run `mvn clean` before starting again.

## 12. MIGRATION NOTES
- This project was not migrated from another stack.

- Package manager: Maven
