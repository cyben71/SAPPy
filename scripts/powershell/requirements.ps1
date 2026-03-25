<#
    .SYNOPSIS
    Install Python packages (dependencies)

    .DESCRIPTION
    Allow to load Python packages (dependencies) listed 'conf/requirements.txt' and needed by your project manually. 
    This script can be used without Python virtualenv.

    .INPUTS
    List of Python packages stored in 'conf/requirements.txt'
    
    .OUTPUTS
    All Python packages are download and stored in user home. 
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
$LOG_FILE = Join-Path $LOG_DIR "win_requirements_$CUR_DATE.log"

# ------------------------------------------------------------------------ #

LogMessage "# =============================== #"
LogMessage "# === INSTALLING REQUIREMENTS === #"
LogMessage "# =============================== #"
LogMessage ""

# create log folder if not exists and log file
if (-not (Test-Path -Path $LOG_DIR -PathType Container)) {
    New-Item -Path $LOG_DIR -ItemType Directory
}
New-Item -ItemType Directory -Path (Split-Path $LOG_FILE) -Force | Out-Null

# Check config file "env.conf" exists
if (-not (Test-Path -Path $CONF_FILE -PathType Leaf)){
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

# Select python from virtual env path or parent path
$python_parent = Join-path $PARENT_PYTHON_HOME $PARENT_PYTHON_EXE 
$python_venv = Join-path -Path "$VENV_PYTHON_DIR\Scripts" $VENV_PYTHON_EXE

# Initialisation
$python = $null

LogMessage "-------------------------------------"
LogMessage "--- Deploying Python dependencies ---"
LogMessage "-------------------------------------"

# checking virtual python exists
# use case: if no venv, dependences must be installed with 'user mode' (pip install --user)
# use case: if venv, dependences can be installed without 'user mode' (pip install). venv will isolate packages
if (-not (Test-Path -Path $python_venv -PathType Leaf)) {
    LogMessage "Virtual python not found in : $env:APPLICATION_HOME"

    # checking Python parent
    if (-not (Test-Path -Path $python_parent -PathType Leaf)) {
        LogMessage "Python parent not found in : $python_parent"
        LogMessage "Error !!! No Python found !!!"
        exit 1
    } else {
        LogMessage "Python parent found : $python_parent"
        $python_folder = $PARENT_PYTHON_HOME
        $python = $python_parent
        $pip_install_opts = "--user"
    }
} else {
    LogMessage "Virtual python environment detected : $python_venv"
    $python_folder = $VENV_PYTHON_DIR
    $python = $python_venv
    $pip_install_opts = ""
}
LogMessage

# install dependencies
LogMessage "Python dependencies installation"
if (!(Test-Path -Path $CONF_DIR\requirements.txt -PathType Leaf)){
    LogMessage "No requirement.txt file found"
}
else {
    & $python -m pip install $pip_install_opts -r $CONF_DIR\requirements.txt
    $status = $LASTEXITCODE
}

# checking result of installation
if ($status -eq 0){
    LogMessage "Python dependencies successfully installed"
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

LogMessage ""
LogMessage "# === END OF PROCESS === #"
LogMessage ""