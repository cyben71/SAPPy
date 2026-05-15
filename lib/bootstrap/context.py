__version__ = "1.0.1"

# Use real name of Class (not filename !)
from types import SimpleNamespace
from lib.bootstrap.cfgyaml import ConfigYaml        
from lib.bootstrap.cfgproperties import ConfigProperties
from lib.bootstrap.appenv import AppEnv
from lib.bootstrap.logger import Logger
from lib.bootstrap.docgenerator import DocGenerator
from typing import Any

class Context(SimpleNamespace):
    """
    Allow to display properly modules or main variables into a context called 'epy'.
    Usefull for IDE like Vscode.
    """

    # Add here all classes needed
    APPLICATION_HOME: str
    APPLICATION_NAME: str
    cfgyaml: ConfigYaml  
    cfgprops: ConfigProperties
    appenv: AppEnv
    log: Logger
    doc: DocGenerator
    CFGYAML_FILE: str
    CFGENV_FILE: str
    CFGPROPS_FILE: str


    # it's just function signature to help IDE to display args... etc
    def load_class(self, module_name: str, class_name: str, args: list[Any] = []) -> Any:
        """
        Allow to load and instanciate your own python class (outside of lib/bootstrap).

        Args:
            module_name (str): Module name (without extension) to load. Ex: module_name = 'my_dummy_class'
            class_name (str, optional): Class name to load. Defaults to None.
            args (list, optional): List of arguments required by module. Defaults to [].
            
        Returns:
            cls (object): a properly loaded module with its class

        Example:
            # Load my custom class
            cls = epy.load_class(module_name='my_dummy_class', args=[epy, APPLICATION_NAME])
        """
        ...


# Unique instance of global context
context = Context()