@echo off
chcp 65001 >nul
cd /d "%~dp0"
where java >nul 2>nul
if errorlevel 1 (
  echo 未找到 java，请安装 JDK 17 或更高版本。
  pause
  exit /b 1
)
java FindMushroomIslands.java
if errorlevel 1 pause
