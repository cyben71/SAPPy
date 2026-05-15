__version__ = "1.0.2"

import os, sys
import re
import subprocess
from typing import Optional, Dict, Any

class ConfigProperties:
    """
    Class for handling config files application.properties and env.conf.
    Allow to load config files, replace placeholders behind ${VAR} by OS env vars values or from other config keys included in config files.
    A recurse method is set to solve all crossed references from ${VAR}.
    
    Config files used by this class: 
    - conf/env.conf : mainly storing python environment variables like python executer location.
    - conf/application.properties : contains properties used par application.
    """
    alias = "cfgprops"

    def __init__(self, app_home: str):
        """
        Constructor.

        Args:
            app_home (str): Parent location for this app
        """
        self._application_home = app_home
        self._config: Dict[str, Any] = {}
        
        self._properties_file = os.path.join(self._application_home, "conf", "application.properties")
        self._env_file = os.path.join(self._application_home, "conf", "env.conf")
        
        self._load_file(self._env_file)         # Loading and store variables from env.conf
        self._load_file(self._properties_file)  # Loading and store variables from application.properties.
        
        # Solve crossed references from env vars and config files
        self._resolve_all_placeholders()

        # Update EPY context 
        # Get indirect context (to avoid circular error)
        context = sys.modules.get("lib.bootstrap.context")
        if context and hasattr(context, "context"):
            context.context.CFGENV_FILE = self._env_file
            context.context.CFGPROPS_FILE = self._properties_file

    #######################################
    ##### PUBLIC FONCTIONS & METHODES #####
    #######################################
    
    @property
    def get_env_file(self) -> str:
        """      
        Return location for config file: env.conf.
        """
        return self._env_file
    
    @property
    def get_properties_file(self) -> str:
        """
        Return location for config file: application.properties.
        """
        return self._properties_file
    
    @property
    def get_parent_python_home(self) -> str:
        """
        Return location for parent python.
        """
        return self.get("PARENT_PYTHON_HOME")
    
    @property
    def get_venv_python_home(self) -> str:
        """
        Return location for python virtual environment.
        """
        return self.get("VENV_PYTHON_DIR")
    
    
    def get(self, key: str, default: Optional[str] = None, strip_values: bool = True) -> Any:
        """
        Getting value from a specified key with handling of environment variables and empty string stripping.

        Args:
            key (str): Key to find in current config context
            default (str, optionnal): Default string to return if searched key is not found
            strip_values (bool, optionnal): Enabling string stripping (True by default)

        Returns:
            str: Value associated to searched key. Default value if key is not found.
        """
        value: Any = self._config.get(key, default)

        if value is not None:
            value = self._resolve_env_vars(value)
        
        if strip_values:
            return self._strip_value(value)
        else:
            return value
    
    #####################################
    ##### PRIVATE METHOD & FUNCTIONS ####
    #####################################

    def _load_file(self, file_path: str) -> None:
        """
        Loading a config file (.properties or .conf). 
        keys-values are stored in a hidden object "_config".

        Args:
            file_path (str): Location of config file to load.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Configuration file '{file_path}' is not found")

        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("!"):
                    continue
                if "=" in line:
                    key, value = map(str.strip, line.split("=", 1))
                    if value.startswith(("'", '"')) and value.endswith(("'", '"')):
                        value = value[1:-1]
                    self._config[key] = value

    def _resolve_all_placeholders(self) -> None:
        """
        Recurse solving all crossed references between config keys.
        This method is looking for all values stored in _config object and replace placeholders (${VAR}) by value from config until all values are set.
        """
        unresolved = True
        while unresolved:
            unresolved = False
            for key, value in self._config.items():
                new_value = re.sub(r"\$\{(\w+)\}", lambda match: self._config.get(match.group(1), match.group(0)), value)
                if new_value != value:
                    self._config[key] = new_value
                    unresolved = True

    def _resolve_env_vars(self, value: Any) -> Any:
        """
        Replacing placeholders ${VAR} found in a string by its value from  _config.

        Args:
            value (str): String which can contain placeholders in format ${VAR}.

        Returns:
            str: String with solved value of environment variables.
        """
        if isinstance(value, str):
            return re.sub(r"\$\{(\w+)\}", lambda match: os.getenv(match.group(1), match.group(0)), value)
        return value

    def _strip_value(self, value: Any) -> Any:
        """
        Deleting empty caracters from a string.

        Args:
            value (Any): String to strip.

        Returns:
            str: Stripped value.
        """
        if isinstance(value, str):
            return value.strip()
        else:
            return value
