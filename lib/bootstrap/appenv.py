__version__ = "1.0.1"

import os
import platform
from datetime import datetime
from typing import Optional

class AppEnv:
    """
    A tool class to get simple information about environnement.
    """    
    alias = "appenv"

    #def __init__(self, app_home: str, app_name: str):
    def __init__(self):

        """
        Constructor
        """
        
        # instance variables (hidden for more clarety in IDE)
        # self._application_home = app_home
        # self._application_name = app_name
        
        
        # # Loading config files (conf, yaml or properties)
        # self._config = ConfigProperties(self._application_home)
        # self._yaml = ConfigYaml(self._application_home)
        # self.test = epy.cfg_yaml()
                
        # # Getting env variables and display
        # env_config = self._setup_environment()
        # print(">> Configuration actuelle : <<")
        # for k, v in env_config.items():
        #     print(f"{k}: {v}")


    #####################################
    ##### PUBLIC METHOD & FUNCTIONS #####
    #####################################
    
    # @property => use @property for getting an object from constructor (self)
    # @staticmethod => use @property for getting an objecty from an imported lib. no instance needed
 

    @staticmethod
    def get_system() -> str:
        """
        Return type of system.
        """
        return f"{platform.system()} ({platform.platform()})"

    @staticmethod
    def get_hostname() -> str:
        """
        Return hostname.
        """
        #return socket.gethostname()
        return platform.node()
    
    
    @staticmethod
    def get_current_date(pattern: Optional[str] = None) -> str:
        """
        Return current date (default format: %Y-%m-%d).
        
        Args:
            pattern (str, optional): Pattern for diplaying date.

        Returns:
            current_date (str): Current date displaying with chosen pattern.

        Example:
            # pattern for date formating
            date1 = epy.appenv.get_current_date(pattern='%Y-%m-%d')
            date2 = epy.appenv.get_current_date(pattern='%d/%m/%Y')
        """
        today = datetime.now()
        if pattern is None:
            pattern = "%Y-%m-%d"
        
        current_date = today.strftime(pattern)
        
        return current_date
    
    @staticmethod
    def get_current_time(pattern:  Optional[str] = None) -> str:
        """
        Return current time (default format: %H:%M:%S).

        Args:
            pattern (str, optional): Pattern for diplaying time.

        Returns:
           current_time (str): Current time displaying with chosen pattern.
        """
        today = datetime.now()
        if pattern is None:
            pattern = "%H:%M:%S"
            
        current_time = today.strftime(pattern)
        
        return current_time

    @staticmethod
    def is_folder_exists(location: str) -> bool:
        """
        Checking folder exists from specified location.

        Args:
            location (str): Folder location.

        Returns:
            exists (bool): True / False if folder exists
        """
        if not os.path.exists(location):
            exists = False
        else:
            exists = True
        return exists
    
    @staticmethod
    def is_file_exists(location: str) -> bool:
        """
        Checking file exists from specified location.

        Args:
            file (str): File location.

        Returns:
            exists (bool): True / False if file exists
        """
        if os.path.isfile(location):
            exists = True
        else:
            exists = False
        return exists
    
    @staticmethod
    def rm_file(location: str) -> bool:
        """
        Delete a file if exists in location.

        Args:
            location (str): File location.

        Returns:
            deleted (bool): True / False if file is sucessfully deleted
        """
        if os.path.isfile(location):
            try: os.remove(location)
            except Exception: 
                print(f"File ({location}) not deleted")
                deleted = False
            else: deleted = True
        else:
            print(f"File {location} is not found or is not available")
            deleted = False
        return deleted
    
    @staticmethod
    def mkdir(location: str) -> bool:
        """
        Create a folder from a location.

        Args:
            location (str): Folder location to create.

        Returns:
            created (bool): True / False if folder is successfully created
        """
        try:
            os.makedirs(location)
        except Exception:
            print(f"Folder {location} not created")
            created = False
        else:
            print(f"Folder {location} successfully created")
            created = True
        return created
        
    
    ######################################
    ##### PRIVATE METHOD & FUNCTIONS #####
    ######################################  