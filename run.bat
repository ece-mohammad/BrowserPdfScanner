@SETLOCAL

@SET FFOX_BIN=F:\Programs\Mozilla Firefox\firefox.exe
@SET GECKO_BIN=geckodriver.exe
@SET PAGE_WAIT=1
@CALL venv\Scripts\activate
@CALL python main.py "%FFOX_BIN%" "%GECKO_BIN%" -w %PAGE_WAIT%
