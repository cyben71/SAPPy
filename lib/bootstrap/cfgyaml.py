__version__ = "1.0.1"

import os, sys
import yaml
import re
from typing import Dict, List, Any, Optional

class ConfigYaml:
    """
    Class for handling config files application.yaml.

    Config files used by this class: 
    - conf/application.yaml : contains properties used by application
    """
    alias = "cfgyaml"

    def __init__(self, app_home: str):
        """
        Set this class with location of yaml config file and load it.

        Args:
            app_home (str): Parent location for this app
        """
        self._application_home = app_home
        self._file_path: str = f"{self._application_home}/conf/application.yaml"
        self._config: Dict[str, Any] = {}
        
        # Automatic loading config
        self._load()

        # Update EPY context 
        # Get indirect context (to avoid circular error)
        context = sys.modules.get("lib.bootstrap.context")
        if context and hasattr(context, "context"):
            context.context.CFGYAML_FILE = self._file_path

    #######################################
    ##### PUBLIC FONCTIONS & METHODES #####
    #######################################

    @property
    def get_yaml_file(self):
        """
        Return application.yaml location.
        """
        return self._file_path

    def get(self, key: str, 
            default: Optional[str] = None, 
            root: Optional[Dict[str, Any]] = None, 
            strip_values: Optional[bool] = None
            ) -> Any:
        """
        Get value from a specified key coming from a yaml file. 
        Can handled: 
        - imbricated path (ex: customer.given)
        - string stripping

        Args:
            key (str): Path of key to look for (ex: 'customer.given')
            default (str, optional): Default value if key is not found (by default = None)
            root (dict, optional): Data root for internal solving (by default: self._config)
            strip_values (bool, optional): Enabling string stripping (True by default)

        Returns: 
            Associated value from a key
        """
        if root is None:
            root = self._config

        if strip_values is None:
            strip_values = True

        try:
            # walk throught nested paths
            keys = key.split('.')
            value = root
            for k in keys:
                value = value[k]    # get nested key

            # enabling stripping
            #return self._strip_value(value) if strip_values else value
            if strip_values:
                return self._strip_value(value)
            else:
                return value
        except (KeyError, TypeError):
            return default
    

    ######################################
    ##### PRIVATE METHOD & FUNCTIONS #####
    ######################################

    def _strip_value(self, value: Any) -> Any:
        """
        Deleting empty caracters from a value. 
        Value can be string, List, Dict so function can be called recursively.

        Args:
            value (Any): value to strip
            
        Returns:
            str: Stripped value
        """
        if isinstance(value, str):
            return value.strip()
        elif isinstance(value, Dict):
            # use recursive call for all dictionary values
            values: Any = value.items()
            return {k: self._strip_value(v) for k, v in values}
        elif isinstance(value, List):
            # use recursive call for all list values
            values: Any = value
            return [self._strip_value(item) for item in values]
        return value

    def _resolve_env_vars(self, value: Any) -> Any:
        """
        Replacing placeholders ${VARIABLES} found in a value by its real value coming from OS env. variables.

        Args:
            value (Any): Value which can contain placeholders in format ${VARIABLES}.

        Returns:
            str: Final value with solved OS env. variable.
        """
        if isinstance(value, str):
            resolved = re.sub(r"\$\{(\w+)\}", lambda match: os.getenv(match.group(1), match.group(0)), value)
            return resolved
        return value

    def _resolve_nested_vars(self, data: Any, root: Optional[Any]=None) -> Any:
        """
        Solving internal references from yaml file like ${customer.given}.

        Args:
            data (Any): load yaml data
            root (Any, optional): Reference to data root (by default: itself) 
            
        Returns: 
            data (Any): value with solved internal references
        """
        if root is None:
            root = data

        if isinstance(data, dict):
            return {k: self._resolve_nested_vars(v, root) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_nested_vars(item, root) for item in data]
        elif isinstance(data, str):
            # Replacing internal references (ex: ${key.path})
            resolved = re.sub(
                r"\$\{([a-zA-Z0-9_.]+)\}",
                lambda match: str(self.get(match.group(1), root=root, strip_values=False) or match.group(0)),
                data
            )
            return resolved
        return data

    def _load(self):
        """
        Loading yaml file with replacement of OS env. variables and solving internal references.
        """
        if not os.path.isfile(self._file_path):
            raise FileNotFoundError(f"Le fichier de configuration '{self._file_path}' est introuvable.")
        
        with open(self._file_path, 'r', encoding='utf-8') as file:
            # raw loading yaml file 
            raw_config = yaml.safe_load(file)
            
            # Replacing OS env. variables found in raw_config
            resolved_config = self._resolve_nested_vars(
                {k: self._resolve_env_vars(v) for k, v in raw_config.items()}
            )

            # solving internal references
            self._config = self._resolve_nested_vars(resolved_config)

