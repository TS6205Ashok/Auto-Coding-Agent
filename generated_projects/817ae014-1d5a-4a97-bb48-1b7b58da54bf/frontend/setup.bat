@echo off
setlocal
pushd "%~dp0"
call npm install
popd
echo Frontend setup complete.
