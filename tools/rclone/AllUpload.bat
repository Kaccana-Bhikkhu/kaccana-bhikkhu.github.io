@echo off
setlocal enabledelayedexpansion

call :getPassword RCLONE_CONFIG_PASS "Password: "

rclone -v -P sync --s3-acl=public-read --no-update-modtime audio/excerpts abhayagiri:abhayagiri/media/discs/questions/audio/excerpts
rclone -v -P sync --s3-acl=public-read --no-update-modtime audio/sessions abhayagiri:abhayagiri/media/discs/questions/audio/sessions
rclone -v -P sync --s3-acl=public-read --no-update-modtime references abhayagiri:abhayagiri/media/discs/questions/references
rclone -v -P copyto --s3-acl=public-read --no-update-modtime index.html abhayagiri:abhayagiri/media/discs/questions/index.html
rclone -v -P sync --s3-acl=public-read --no-update-modtime pages abhayagiri:abhayagiri/media/discs/questions/pages
rclone -v -P sync --s3-acl=public-read --no-update-modtime csv abhayagiri:abhayagiri/media/discs/questions/csv

exit /b

::------------------------------------------------------------------------------
:: Masks user input and returns the input as a variable.
:: Password-masking code based on http://www.dostips.com/forum/viewtopic.php?p=33538#p33538
::
:: Arguments: %1 - the variable to store the password in
::            %2 - the prompt to display when receiving input
::------------------------------------------------------------------------------
:getPassword
set "_password="

:: We need a backspace to handle character removal
for /f %%a in ('"prompt;$H&for %%b in (0) do rem"') do set "BS=%%a"

:: Prompt the user 
set /p "=%~2" <nul 

:keyLoop
:: Retrieve a keypress
set "key="
for /f "delims=" %%a in ('xcopy /l /w "%~f0" "%~f0" 2^>nul') do if not defined key set "key=%%a"
set "key=%key:~-1%"

:: If No keypress (enter), then exit
:: If backspace, remove character from password and console
:: Otherwise, add a character to password and go ask for next one
if defined key (
    if "%key%"=="%BS%" (
        if defined _password (
            set "_password=%_password:~0,-1%"
            set /p "=!BS! !BS!"<nul
        )
    ) else (
        set "_password=%_password%%key%"
        set /p "="<nul
    )
    goto :keyLoop
)
echo/

:: Return password to caller
set "%~1=%_password%"
goto :eof