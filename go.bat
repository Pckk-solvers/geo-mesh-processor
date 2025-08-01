@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION
chcp 65001 >nul

rem === 設定 ===
set "ROOT=%~dp0"
pushd "%ROOT%"
set "VENV_DIR=.venv"
set "REQ=requirements.txt"
set "REQ_HASH_FILE=%VENV_DIR%\requirements.sha256"
set "MODULE=src.app2"
set "PIP_NO_INPUT=1"

rem オプション
set "FORCE_REINSTALL=0"
set "PAUSE_ON_ERROR=1"
if /I "%~1"=="--reinstall" ( set "FORCE_REINSTALL=1" & shift )

echo [INFO] 作業ディレクトリ: %CD%

rem === Python 選択: py -3 優先 / QGIS・OSGeo4W・WindowsApps を除外 / ensurepip ありのみ ===
set "PY_CMD="

where py >nul 2>&1
if not errorlevel 1 (
  py -3 -m ensurepip --version >nul 2>&1
  if not errorlevel 1 (
    set "PY_CMD=py -3"
  )
)

if not defined PY_CMD (
  for /f "delims=" %%I in ('where python 2^>nul') do (
    echo "%%I" | find /i "WindowsApps" >nul && (rem skip) || (
      echo "%%I" | find /i "qgis" >nul && (rem skip) || (
        echo "%%I" | find /i "osgeo4w" >nul && (rem skip) || (
          "%%I" -m ensurepip --version >nul 2>&1
          if not errorlevel 1 (
            set "PY_CMD="%%I""
            goto :PY_OK
          )
        )
      )
    )
  )
  if not defined PY_CMD goto :ERR_NO_PY
) else (
  goto :PY_OK
)

:ERR_NO_PY
echo [ERROR] ensurepip を備えた通常の Python が見つかりませんでした。
echo         QGIS/OSGeo4W 付属の Python では venv 作成に失敗します。
set "RC=1"
goto :FINALLY

:PY_OK
echo [INFO] 使用する Python: %PY_CMD%

rem === venv 作成（存在すればスキップ）===
if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [INFO] 仮想環境を作成: %VENV_DIR%
  %PY_CMD% -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [ERROR] venv 作成に失敗しました（ensurepip 未搭載の Python の可能性）。
    set "RC=1"
    goto :FINALLY
  )
) else (
  echo [INFO] 既存の仮想環境を使用: %VENV_DIR%
)

rem === venv 有効化 ===
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] 仮想環境の有効化に失敗しました。
  set "RC=1"
  goto :FINALLY
)

rem === pip 更新（控えめ）===
python -m pip install --upgrade pip wheel --disable-pip-version-check -q

rem === requirements の変更検知（なければ pip install スキップ）===
set "NEED_INSTALL=%FORCE_REINSTALL%"

if exist "%REQ%" (
  rem --- ハッシュ計算: PowerShell 優先、だめなら certutil ---
  set "NEW_HASH="
  for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -Path '%REQ%').Hash.ToUpper()"`) do set "NEW_HASH=%%H"
  if not defined NEW_HASH (
    where certutil >nul 2>&1
    if not errorlevel 1 (
      for /f "tokens=* delims=" %%H in ('certutil -hashfile "%REQ%" SHA256 ^| findstr /R /V "SHA256 CertUtil"') do set "NEW_HASH=%%H"
      if defined NEW_HASH set "NEW_HASH=!NEW_HASH: =!"
    )
  )

  if not defined NEW_HASH (
    echo [WARN] requirements.txt のハッシュ計算に失敗。pip install を実行します。
    set "NEED_INSTALL=1"
  ) else (
    if exist "%REQ_HASH_FILE%" (
      set /p OLD_HASH=<"%REQ_HASH_FILE%"
      if /I "!OLD_HASH!"=="!NEW_HASH!" (
        if "!NEED_INSTALL!"=="0" echo [INFO] requirements.txt に変更なし → pip install をスキップします。
      ) else (
        set "NEED_INSTALL=1"
      )
    ) else (
      set "NEED_INSTALL=1"
    )
  )

  if "!NEED_INSTALL!"=="1" (
    echo [INFO] 依存関係をインストール/更新中...
    python -m pip install -r "%REQ%" --disable-pip-version-check
    if errorlevel 1 (
      echo [ERROR] 依存インストールに失敗しました。
      set "RC=1"
      goto :FINALLY
    )
    if defined NEW_HASH (>"%REQ_HASH_FILE%" echo !NEW_HASH!)
  )
) else (
  echo [INFO] requirements.txt が見つからないため依存インストールをスキップします。
)

rem === モジュール実行 ===
echo [INFO] 実行: python -m %MODULE% %*
python -m %MODULE% %*
set "RC=%ERRORLEVEL%"

:FINALLY
rem === 後片付け & ウィンドウ保持 ===
if exist "%VENV_DIR%\Scripts\deactivate.bat" call "%VENV_DIR%\Scripts\deactivate.bat" >nul 2>&1
popd
echo.
echo [INFO] 終了コード: %RC%
if "%PAUSE_ON_ERROR%"=="1" if not "%RC%"=="0" (
  echo [INFO] エラー内容を確認してください。何かキーで閉じます...
  pause >nul
)
exit /b %RC%
