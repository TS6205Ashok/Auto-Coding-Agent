# Create Todo App

Create Todo App is a 100% runnable starter project built around React + Spring Boot. Fast Mode uses backend templates for all standard project structure so output quality stays complete while generation remains fast.

## What Was Generated
This ZIP contains a 100% runnable starter project from the latest preview, including dependency files, setup scripts, run scripts, starter source code, and required input guidance.

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

## Problem Statement
create todo app

## Selected Stack
- Language: Java
- Frontend: React
- Backend: Spring Boot
- Database: MySQL
- AI / Tools: None
- Deployment: Render

## Recommended IDE And Tools
- Recommended IDE: IntelliJ IDEA
- Alternative IDE: VS Code
- Runtime tools: JDK 17+, Maven
- Package manager: Maven

## Chosen Stack
- Language: Java
- Frontend: React
- Backend: Spring Boot
- Database: MySQL
- AI / Tools: None
- Deployment: Render

## Detected User Choices
- The user did not explicitly specify language, tooling, or framework choices.

## Architecture Highlights
- React handles the user-facing workflows, starter pages, and client-side integration points.
- Spring Boot provides the API surface, routing, services, and configuration layer.
- MySQL is configured as the primary persistence layer through environment-driven settings.
- Setup, run scripts, and dependency manifests are generated server-side for a consistent starter layout.

## Core Modules
- Frontend Experience: Provides the main user interface, starter pages, and client-side state or API hooks.
  Key files: frontend/src/App.jsx, frontend/src/pages/HomePage.jsx, frontend/src/services/api.js
- Backend API: Provides the routes, services, and integration-ready backend surface.
  Key files: backend/pom.xml, backend/src/main/java/com/example/demo/service/AppService.java
- Persistence Layer: Supplies data models, configuration, and starter persistence wiring.
  Key files: backend/src/models/itemModel.js

## Setup
Fill `.env` from `.env.example`, then run the setup script before starting the project.
- Windows: `setup.bat`
- Mac/Linux: `setup.sh`
- Full guided setup: `FULL_RUNTIME_INSTRUCTIONS.md`

## How To Run
- Main file: `backend/src/main/java/com/example/app/Application.java`
- Primary run command: `cd backend && mvn spring-boot:run`
- Run method: `Click IDE Play button or run mvn spring-boot:run`
- Local URL: `http://localhost:8080`
- cd backend
- mvn spring-boot:run

## Required Inputs
Fill these values in `.env` before running the project.

- `APP_ENV` (optional): Application environment name.
- `PORT` (optional): Local port used when the backend starts from the generated run scripts.
- `DATABASE_URL` (required): MySQL connection string for the backend database.
- `VITE_API_BASE_URL` (optional): Frontend base URL for backend API calls.

## Notes
- Fast Mode used backend templates for standard files so project completeness was preserved without waiting for the model to write boilerplate.
- The project is split into frontend and backend folders to keep the full-stack boundary explicit.
- This output is a 100% runnable starter project after `.env` is filled, setup is run, and the run script is started. Business logic can still be customized afterward.
- Project-specific custom files were layered on top of the standard stack templates.
