__version__ = "1.0.1"

from pathlib import Path
import sys, os
from lib.bootstrap.context import context, Context
from lib.bootstrap import init_code

# Alias explicite pour les autres modules (IDE-friendly)
# Typage pour l'autocomplétion dans VSCode/Jupyter
epy: Context = context

def init_env() -> Context:
    """
    Wrapping function to init application environment with classes from EssencePy. 
    Bootstrap will be launched and return EPY context.

    Returns:
        Context: Including global vars like APP_HOME/APP_NAME and EssencePy Classes.
    """
    bootstrap()
    init_code.summarize_context()
    
    return epy

def bootstrap() -> Context:
    """
    Bootstrap function used to set EssencePy context called "epy".

    Returns:
        epy (Context): EssencePy context
    """

    # Set global vars
    app_name: str = _find_application_name()
    app_home: Path = _find_application_home()

    # Add APPLICATION_HOME (as str) to OS Path if str(app_home) not in sys.path:
    if f"{app_home}" not in sys.path:
        sys.path.insert(0, str(app_home))

    # set APPLICATION_HOME for OS and PYTHON paths
    os.environ["APPLICATION_HOME"] = f"{app_home}"
    os.environ["APPLICATION_NAME"] = app_name

    # Load app_home and app_name values in Context
    epy.APPLICATION_HOME = f"{app_home}"
    epy.APPLICATION_NAME = app_name

    # Load all modules from lib/bootstrap
    init_code.init()
    init_code.load_epy_cls(epy, app_home, app_name)

    # Expose a specific function to epy context
    epy.load_class = init_code.load_class
        
    return epy


    ######################################
    ##### PRIVATE METHOD & FUNCTIONS #####
    ######################################

def _find_application_home(sentinel: str = "lib/bootstrap/bootstrap.py") -> Path:
    """
    Founding and setting APPLICATION_HOME function.

    Args:
        sentinel (str, optional): Sentinel file used to set APPLICATION_HOME. Defaults to "lib/bootstrap/bootstrap.py".

    Raises:
        FileNotFoundError: Exit if sentinel file is not found.
        
    Returns:
        current (Path): Path of APPLICATION_HOME
    """
    current: Path = Path.cwd().resolve()
    root: str = current.root
    while f"{current}" != root:
        if (current / sentinel).is_file():
            return current
        current = current.parent
    raise FileNotFoundError(f"Fichier sentinelle non trouvé : {sentinel}")


def _find_application_name() -> str:
    """
    Founding and setting APPLICATION_NAME.

    Returns:
        app_name (str): APPLICATION_NAME. Default to "Default".
    """
    # 0. Default value
    app_name: str = "Default"

    # 1. Try to get APP_NAME from main module (__main__) used by notebook (for example)
    main_module = sys.modules.get("__main__")
    if main_module and hasattr(main_module, "APPLICATION_NAME"):
        app_name = getattr(main_module, "APPLICATION_NAME")
    else:
        # 2. Try to get APP_NAME from os environment
        if "APPLICATION_NAME" in os.environ:
            app_name =  os.environ["APPLICATION_NAME"]

    # 3. Default
    return app_name