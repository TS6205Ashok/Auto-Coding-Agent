# File Structure

## Final Generated Tree
```text
.env.example
.vscode
  launch.json
  tasks.json
FILE_STRUCTURE.md
FULL_RUNTIME_INSTRUCTIONS.md
MIGRATION_SUMMARY.md
PACKAGE_REQUIREMENTS.md
PROJECT_EXPLANATION.md
README.md
REQUIRED_INPUTS.md
SETUP_INSTRUCTIONS.md
backend
  app
    __init__.py
    config.py
    database.py
    main.py
    models
      __init__.py
      base.py
      item.py
    routers
      __init__.py
      health.py
      inventory.py
      items.py
    schemas
      __init__.py
      health.py
      item.py
    services
      __init__.py
      app_service.py
      domain_service.py
      inventory_service.py
      item_service.py
  requirements.txt
  run.bat
  run.sh
  setup.bat
  setup.sh
frontend
  index.html
  package.json
  run.bat
  run.sh
  setup.bat
  setup.sh
  src
    App.jsx
    components
      AppShell.jsx
    main.jsx
    pages
      DashboardPage.jsx
      HomePage.jsx
      InventoryPage.jsx
    services
      api.js
    styles.css
  vite.config.js
run.bat
run.sh
setup.bat
setup.sh
```

## Included Modules
- Frontend Experience: Provides the main user interface, starter pages, and client-side state or API hooks.
  Key files: frontend/src/App.jsx, frontend/src/pages/HomePage.jsx, frontend/src/services/api.js
- Backend API: Provides the routes, services, and integration-ready backend surface.
  Key files: backend/app/main.py, backend/app/routers/items.py, backend/app/services/item_service.py
- Persistence Layer: Supplies data models, configuration, and starter persistence wiring.
  Key files: backend/app/database.py
- Inventory Module: Inventory workflow and APIs.
  Key files: backend/app/routers/inventory.py, backend/app/services/inventory_service.py, frontend/src/pages/InventoryPage.jsx
