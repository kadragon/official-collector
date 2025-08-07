@echo off

:: CMD 창 제목을 설정하여 pywinauto가 찾을 수 있도록 함
title DocumentAutoClassifier

:: 프로젝트 디렉토리로 이동
cd C:\Dev\knue_rpa\official-collector

:: 메인 프로그램 실행
uv run ./src/main.py

pause