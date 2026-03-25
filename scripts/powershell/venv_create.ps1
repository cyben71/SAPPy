<#
    .SYNOPSIS
    Intializing project

    .DESCRIPTION
    Create a Python virtualenv with dependencies stored to 'conf/requirements.txt'. Python package 'jupyter' is loaded by default to allow you to start to dev and run.

    .INPUTS
    List of Python packages stored in 'conf/requirements.txt'

    .OUTPUTS
    A new folder 'rt/' is created in this tree and contains all executables files for dev and run Python program

    .EXAMPLE
    ./scripts/powershell/venv_create.ps1
#>

#################
### FUNCTIONS ###
#################
function LogMessage {
    param (
        [string]$Message
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "$timestamp - $Message"
    Write-Output $logEntry | Tee-Object -FilePath $LOG_FILE -Append
}

################
### SETTINGS ###
################

# Trouver APPLICATION_HOME
$currentDir = Split-Path -Path $MyInvocation.MyCommand.Definition -Parent
while ($true) {
    $candidate = Join-Path $currentDir "lib/bootstrap/bootstrap.py"
    if (Test-Path $candidate) {
        $env:APPLICATION_HOME = $currentDir
        Write-Host "APPLICATION_HOME: $env:APPLICATION_HOME"
        break
    }

    $parentDir = Split-Path $currentDir -Parent
    if ($parentDir -eq $currentDir) {
        Write-Host "[ERROR] : Fail to find bootstrap.py"
        exit 1
    }
    $currentDir = $parentDir
}

$CONF_DIR = Join-Path $env:APPLICATION_HOME "conf"
$CONF_FILE = Join-Path $CONF_DIR "env.conf"
$LOG_DIR = Join-Path $env:APPLICATION_HOME "log"
$CUR_DATE = $timestamp = Get-Date -Format "yyyy-MM-dd"
$LOG_FILE = Join-Path $LOG_DIR "win_setup_env_$CUR_DATE.log"

# ------------------------------------------------------------------------ #

LogMessage "# ==================================== #"
LogMessage "# === CREATING PYTHON VIRTUAL ENV ===  #"
LogMessage "# ==================================== #"
LogMessage ""

# create log folder if not exists and log file
if (!(Test-Path -Path $LOG_DIR -PathType Container)) {
    New-Item -Path $LOG_DIR -ItemType Directory
}
New-Item -ItemType Directory -Path (Split-Path $LOG_FILE) -Force | Out-Null

# Check config file "env.conf" exists
if (!(Test-Path -Path $CONF_FILE -PathType Leaf)){
    LogMessage "Error !!! File conf/env.conf not found."
    exit 1
}
else {
    LogMessage "Config file location is: $CONF_FILE"
}
LogMessage ""

# Loading config file "env.conf"
Get-Content $CONF_FILE | ForEach-Object {
    # Check line starting with "WIN_"
    if ($_ -match "^WIN_") {
        # Get variable name only without prefix "WIN_"
        $variableName = $_ -replace "^WIN_", "" -split "=" | Select-Object -First 1
        # Get variable values
        $value = $_ -split "=" | Select-Object -Last 1
        # Create variable with name and value (deleting "" caracters and trim)
        Set-Variable -Name $variableName -Value $value.Trim('"').Trim()
    }
    $VENV_PYTHON_DIR = Join-Path $env:APPLICATION_HOME "rt"
}
Set-Variable -Name "VENV_PYTHON_DIR" -Value $VENV_PYTHON_DIR
Set-Variable -Name "VENV_PYTHON_EXE" -Value $PARENT_PYTHON_EXE

# Checking variables
$variableNames = @("PARENT_PYTHON_HOME", "PARENT_PYTHON_EXE", "VENV_PYTHON_DIR", "VENV_PYTHON_EXE")

# Display variables 
foreach ($name in $variableNames) {
    $var = Get-Variable -Name $name -ValueOnly
    LogMessage "$name : $var"
}
LogMessage ""

# ======================================================================== #
# ======================================================================== #

# Checking parent python exec
$python = Join-Path $PARENT_PYTHON_HOME $PARENT_PYTHON_EXE
if (!(Test-Path -Path $python -PathType Leaf)){
    LogMessage "Error !!! Python exec not found"
}
else {
    LogMessage "Python exec: $python"
}
LogMessage

# creating python virtual env and enabling (after end of creating)
LogMessage "-----------------------------------------------"
LogMessage "---- Creating of virtual python environment ---"
LogMessage "-----------------------------------------------"

# launch command directly with args and get back return code
& $python -m venv $VENV_PYTHON_DIR      
$status = $LASTEXITCODE
if ($status -eq 0){
    Invoke-Expression $VENV_PYTHON_DIR\Scripts\Activate.ps1
    $python_venv = Join-Path $VENV_PYTHON_DIR "Scripts\python.exe"
    LogMessage "Python virtual env successfully created and enabled"
}
else {
    LogMessage "Error !!! Python virtual env fail to created and enabled"
    exit 1
}

# pip update
LogMessage "Updating PIP..."
& $python_venv -m pip install --upgrade pip
$status = $LASTEXITCODE
if ($status -eq 0){
    LogMessage "PIP update successfully done"
}
else {
    LogMessage "Error !!! Fail to update PIP"
}

# install dependencies
LogMessage "Python dependencies installation"
if (!(Test-Path -Path $CONF_DIR\requirements.txt -PathType Leaf)){
    LogMessage "No requirement.txt file found"
}
else {
    & $python_venv -m pip install -r $CONF_DIR\requirements.txt
    $status = $LASTEXITCODE
}

# checking result of installation
if ($status -eq 0){
    LogMessage "Python dependencies successully installed"
    LogMessage ""
}
else {
    LogMessage "Error !!! Fail to install Python dependencies"
    exit 1
}

# # testing
# LogMessage "Checking Jupyter..."
# $jupyter = Join-Path $VENV_PYTHON_DIR "Scripts\jupyter.exe"
# if ((Test-Path -Path $jupyter -PathType Leaf)){
#     & $jupyter --version
#     $status = $LASTEXITCODE
#     if ($status -eq 0){
#         LogMessage "Jupyter successfully installed"
#         LogMessage "Python virtual env is ready!"
#     }
#     else {
#         LogMessage "Error !!! Jupyter fail to be installed"
#     }
# }
# else {
#     LogMessage "Error !!! Jupyter exec not found"
#     exit 1
# }

LogMessage "Python virtual environment is ready !"

LogMessage ""
LogMessage "# === END OF PROCESS === #"
LogMessage ""