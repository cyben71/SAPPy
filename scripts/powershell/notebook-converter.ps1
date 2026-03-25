<#
    .SYNOPSIS
    Convert a Jupyter notebook to Python program

    .DESCRIPTION
    Convert a Jupyter notebook file to a Python program. Python program is automatically stored in 'app/' folder

    .PARAMETER <notebook_filename>
    Name of Notebook file stored in 'notebooks/' folder

    .PARAMETER <notebook_extension>
    Jupyter notebook extension is: '.ipynb'

    .INPUTS
    Python package 'jupyter' must be installed and available

    .OUTPUTS
    Python program file saved in 'app/' folder

    .EXAMPLE
    ./scripts/powershell/notebook-converter.ps1 notebook.ipynb

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
$LOG_FILE = Join-Path $LOG_DIR "win_convert_$CUR_DATE.log"
$NOTEBOOK_DIR = Join-Path $env:APPLICATION_HOME "Notebooks"
$APP_DIR = Join-Path $env:APPLICATION_HOME "app"

# ------------------------------------------------------------------------ #

LogMessage "# =========================== #"
LogMessage "# === CONVERTING NOTEBOOK === #"
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

LogMessage "------------------------------------------------------"
LogMessage "---- Converting Jupyter notebook to Python program ---"
LogMessage "------------------------------------------------------"

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
    LogMessage "Error !!! Usage: .\notebook-converter.ps1 <notebook.ipynb>"
    exit 1
}

# Get notebook file path
$Notebook = $args[0]

# Checking notebook file exists in 
$NotebookPath = Join-Path $NOTEBOOK_DIR $Notebook
if (-not (Test-Path -Path $NotebookPath -PathType Leaf)) {
    LogMessage "Error !!! Notebook file to convert is missing : $NotebookPath"
    exit 1
}
LogMessage "Notebook to convert : $NotebookPath"

# create APP_DIR if not exists
if (-not (Test-Path -Path $APP_DIR -PathType Container)) {
    New-Item -ItemType Directory -Path $APP_DIR | Out-Null
}

# Checking Jupyter package is available
LogMessage "Checking if Jupyter package is available..."
$jupyter = Join-Path $python_folder "Scripts\jupyter.exe"

if ((Test-Path -Path $jupyter -PathType Leaf)){
    & $jupyter --version
    $status = $LASTEXITCODE
    if ($status -eq 0){
        LogMessage "Jupyter package is available"
    }
    else {
        LogMessage "Error !!! Jupyter package is not available"
        LogMessage ""
        exit 1
    }
}
else {
    LogMessage "Error !!! Jupyter exec not found"
    LogMessage ""
    exit 1
}

# Converting notebook
LogMessage "Converting notebook..."
& $python -m jupyter nbconvert "$NotebookPath" --to script --output-dir "$APP_DIR"

# Checking converting
$notebookName = [System.IO.Path]::GetFileNameWithoutExtension($NotebookPath)
$convertedFile = Join-Path $APP_DIR "$notebookName.py"

if (Test-Path -Path $convertedFile -PathType Leaf) {
    LogMessage "Notebook successfully converted to python. File available : $convertedFile"
} else {
    LogMessage "Error !!! Notebook converting failed. $notebookName.py not found in: $APP_DIR"
    exit 1
}
LogMessage ""
LogMessage "# === END OF PROCESS === #"
LogMessage ""