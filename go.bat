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

rem 任意: --reinstall が先頭引数なら強制で pip install 実行
set "FORCE_REINSTALL=0"
if /I "%~1"=="--reinstall" (
  set "FORCE_REINSTALL=1"
  shift
)

echo [INFO] 作業ディレクトリ: %CD%

rem === Python 検出（WindowsApps 配下は除外）===
set "PYTHON="
for /f "delims=" %%I in ('where python 2^>nul') do (
  echo "%%I" | find /i "WindowsApps" >nul
  if errorlevel 1 (
    set "PYTHON=%%I"
    goto :FOUND_PY
  )
)
for /f "delims=" %%I in ('where py 2^>nul') do (
  set "PYTHON=%%I"
  goto :FOUND_PY
)
echo [ERROR] Python が見つかりませんでした。インストールしてください。
popd
exit /b 1

:FOUND_PY
echo [INFO] 既定の Python: %PYTHON%

rem === venv 作成（存在すればスキップ）===
if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [INFO] 仮想環境を作成: %VENV_DIR%
  "%PYTHON%" -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [ERROR] venv 作成に失敗しました。
    popd
    exit /b 1
  )
) else (
  echo [INFO] 既存の仮想環境を使用: %VENV_DIR%
)

rem === venv 有効化 ===
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] 仮想環境の有効化に失敗しました。
  popd
  exit /b 1
)

rem === pip 更新（控えめ）===
python -m pip install --upgrade pip wheel --disable-pip-version-check -q

rem === requirements の変更検知（変更なければ pip install をスキップ）===
set "NEED_INSTALL=%FORCE_REINSTALL%"

if exist "%REQ%" (
  rem --- ハッシュ計算: PowerShell 優先、だめなら certutil ---
  set "NEW_HASH="

  for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 -Path '%REQ%').Hash.ToUpper()"`) do (
    set "NEW_HASH=%%H"
  )

  if not defined NEW_HASH (
    where certutil >nul 2>&1
    if not errorlevel 1 (
      for /f "tokens=* delims=" %%H in ('certutil -hashfile "%REQ%" SHA256 ^| findstr /R /V "SHA256 CertUtil"') do (
        set "NEW_HASH=%%H"
      )
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
        if "!NEED_INSTALL!"=="0" (
          echo [INFO] requirements.txt に変更なし → pip install をスキップします。
        )
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
      if exist "%VENV_DIR%\Scripts\deactivate.bat" call "%VENV_DIR%\Scripts\deactivate.bat" >nul 2>&1
      popd
      exit /b 1
    )
    if defined NEW_HASH (>"%REQ_HASH_FILE%" echo !NEW_HASH!)
  )
) else (
  echo [INFO] requirements.txt が見つからないため依存インストールをスキップします。
)

rem === モジュール実行（残りの引数はそのまま渡す）===
echo [INFO] 実行: python -m %MODULE% %*
python -m %MODULE% %*
set "RC=%ERRORLEVEL%"

rem === 後片付け ===
if exist "%VENV_DIR%\Scripts\deactivate.bat" call "%VENV_DIR%\Scripts\deactivate.bat" >nul 2>&1
popd
exit /b %RC%
