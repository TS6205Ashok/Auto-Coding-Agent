@echo off
setlocal
pushd "%~dp0"
call mvn spring-boot:run
popd
