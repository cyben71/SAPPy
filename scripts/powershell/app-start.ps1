<#
    .SYNOPSIS
    Launch Python program

    .DESCRIPTION
    Allow to execute Python program stored in 'app/' folder

    .PARAMETER <python_filename>
    Name of Python file

    .PARAMETER <python_extension>
    Python program extension is: '.py'

    .EXAMPLE
    ./scripts/powershell/app-start.ps1 notebook.py
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
$LOG_FILE = Join-Path $LOG_DIR "win_start_app_$CUR_DATE.log"
$APP_DIR = Join-Path $env:APPLICATION_HOME "app"

# ------------------------------------------------------------------------ #

LogMessage "# =========================== #"
LogMessage "# === STARING APPLICATION === #"
LogMessage "# =========================== #"
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

LogMessage "--------------------------------"
LogMessage "--- Executing Python program ---"
LogMessage "--------------------------------"

# checking virtual python exists
if (-not (Test-Path -Path $python_venv -PathType Leaf)) {
    LogMessage "Virtual python not found in : $python_venv"

    # checking Python parent
    if (-not (Test-Path -Path $python_parent -PathType Leaf)) {
        LogMessage "Python parent not found in : $python_parent"
        LogMessage "Error !!! No Python found !!!"
        exit 1
    } else {
        LogMessage "Python parent found : $python_parent"
        $python_folder = $PARENT_PYTHON_HOME
        $python = $python_parent
    }
} else {
    LogMessage "Virtual python environment detected : $python_venv"
    $python_folder = $VENV_PYTHON_DIR
    $python = $python_venv
}
LogMessage


# Checking argument for execution
if ($args.Count -lt 1) {
    LogMessage "Error !!! Usage: .\app-start.ps1 <python.py>"
    exit 1
}

# Get Application file path
$application = $args[0]

# Checking Application file exists
$applicationPath = Join-Path $APP_DIR $application
if (-not (Test-Path -Path $applicationPath -PathType Leaf)) {
    LogMessage "Error !!! Application file is missing : $applicationPath"
    exit 1
}

# Executing Application
LogMessage "Executing application : $applicationPath"
& $python $applicationPath

LogMessage ""
LogMessage "# === END OF PROCESS === #"
LogMessage ""