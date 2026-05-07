@echo off
setlocal
where mvn >nul 2>nul && (
  pushd backend
  call mvn install
  popd
) || echo Maven not found. Skipping backend install.
if exist frontend\package.json (
  pushd frontend
  call npm install
  popd
)
echo Setup complete.
