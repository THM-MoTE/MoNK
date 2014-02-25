@ECHO off
REM turn echo off

for /f "delims=" %%i in ('jruby %0\..\svg2modelica.rb %*') do echo %%i
REM start jruby script
REM TODO: this should be changed to a "java -jar"-call later
REM Note: for some obscure reason inkscape can only read lines that where produced by
REM an explicit "ECHO" command, but not lines from stdout of an external program call like jruby
REM (stderr works fine btw oO)
REM therefore this strange line above is used to read the output like a file and print each single line
REM with echo