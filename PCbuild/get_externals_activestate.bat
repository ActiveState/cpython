@echo off
setlocal
rem Simple script to fetch source for external libraries

if not exist "%~dp0..\externals" mkdir "%~dp0..\externals"
pushd "%~dp0..\externals"

echo.Fetching external libraries...

rem *** IMPORTANT ***
rem If updating bzip2, db, nasm, openssl, or sqlite you must also edit their directory names in python.props.
rem If updating tcl/tk/tix you must also update their versions/directories in tcltk.props.

set libraries=
set libraries=%libraries%                                    bzip2-1.0.8
if NOT "%IncludeBsddb%"=="false" set libraries=%libraries%   bsddb-4.7.25.0
set libraries=%libraries%                                    sqlite-3.34.1.0
if NOT "%IncludeTkinter%"=="false" set libraries=%libraries% tcl-8.5.19.0
if NOT "%IncludeTkinter%"=="false" set libraries=%libraries% tk-8.5.19.0
if NOT "%IncludeTkinter%"=="false" set libraries=%libraries% tix-8.4.3.5

rem CAMEL_GIT_SHA contains the commit SHA used for the current build.
rem Note that the branch 'master' in the below URL is ignored by the server because sha is present.

for %%e in (%libraries%) do (
    if exist %%e (
        echo.%%e already exists, skipping.
    ) else (
        echo.Fetching %%e...
        call lwp-download https://s3.amazonaws.com/camel-sources/src/vendor-sources/python-core/%%e-pysvn.tar.gz ..\externals\%%e.tar.gz
        cd ..\externals
        call tar zxf %%e.tar.gz
        del %%e.tar.gz
        if exist cpython-source-deps-%%e (
            move cpython-source-deps-%%e %%e
        )
        cd ..\PCbuild
    )
)

echo Finished.

goto end

:usage
echo.invalid argument: %1
echo.usage: %~n0 [[ -c ^| --clean ] ^| --clean-only ]
echo.
echo.Pull all sources necessary for compiling optional extension modules
echo.that rely on external libraries.  Requires svn.exe to be on your PATH
echo.and pulls sources from %SVNROOT%.
echo.
echo.Use the -c or --clean option to clean up all external library sources
echo.before pulling in the current versions.
echo.
echo.Use the --clean-only option to do the same cleaning, without pulling in
echo.anything new.
echo.
echo.Only the first argument is checked, all others are ignored.
echo.
echo.**WARNING**: the cleaning options unconditionally remove any directory
echo.that is a child of
echo.   %CD%
echo.and matches wildcard patterns beginning with bzip2-, db-, nasm-, openssl-,
echo.tcl-, tcltk, tk-, tix-, sqlite-, or xz-, and as such has the potential
echo.to be very destructive if you are not aware of what it is doing.  Use with
echo.caution!
popd
exit /b -1


:end
echo Finished.
popd
