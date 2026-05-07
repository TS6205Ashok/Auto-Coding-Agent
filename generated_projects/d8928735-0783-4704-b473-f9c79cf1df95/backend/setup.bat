@echo off
setlocal
pushd "%~dp0"
where mvn >nul 2>nul && call mvn install || echo Maven not found. Skipping install.
popd
