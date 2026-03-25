__version__ = "1.0.1"

import os
from lib.bootstrap.appenv import AppEnv
from typing import Optional

class Logger:
    """
    Class for handling actions in log files
    """
    alias = "log"

    
    def __init__(self, app_home: str, app_name: str):
        """
        Constructor.

        Args:
            app_home (str): Parent location for this app
            app_name (str): Application name
        """
        self._application_home = app_home
        self._application_name = app_name

        self._log_folder = f"{self._application_home}/log"
        self._log_file = f"{self._application_home}/log/{self._application_name}_{AppEnv.get_current_date()}.log"
    
    
    #######################################
    ##### PUBLIC FONCTIONS & METHODES #####
    #######################################
    
    @property
    def get_log_folder(self) -> str:
        """
        Return log folder.
        """
        return self._log_folder
    
    @property
    def get_log_file(self) -> str:
        """
        Return log file.
        """
        return self._log_file
    
    
    def log(self, message: str) -> None:
        """
        Output a message in a log file without prefix and current date & timestamp.

        Args:
            message (str): Message to output
        
        Example:
            # Write a simple message into log file
            epy.log.log("Testing SIMPLE message. No prefix added")
        """
        try:
            self._log(msg=message)
        except Exception as err:
            raise err
        print(f"{AppEnv.get_current_date()} {AppEnv.get_current_time()} : {message}")


    def info(self, message: str) -> None:
        """
        Output a message in a log file with 'INFO' as prefix and current date & timestamp.

        Args:
            message (str): Message to output.

        Example:
            # Write an INFO message into log file
            epy.log.info("Testing INFO message")
        """
        prefix = 'INFO'
        try:
            self._log(prefix=prefix, msg=message)
        except Exception as err:
            raise err
        print(f"{AppEnv.get_current_date()} {AppEnv.get_current_time()} - {prefix} : {message}")
        
        
    def warning(self, message: str) -> None:
        """
        Output a message in a log file with 'WARN' as prefix and current date & timestamp.
        
        Args:
            message (str): Message to output.
        
        Example:
            # Write a WARNING message into log file
            epy.log.warning("Testing WARNING message")
        """
        prefix = 'WARN'
        try:
            self._log(prefix=prefix, msg=message)
        except Exception as err:
            raise err
        print(f"{AppEnv.get_current_date()} {AppEnv.get_current_time()} - {prefix} : {message}")
    
    
    def error(self, message: str) -> None:
        """
        Output a message in a log file with 'ERROR' as prefix and current date & timestamp.

        Args:
            message (str): Message to output.

        Example:
            # Write a ERROR message into log file
            epy.log.error("Testing ERROR message")
        """
        prefix = 'ERROR'
        try:
            self._log(prefix = prefix, msg=message)
        except Exception as err:
            raise err
        print(f"{AppEnv.get_current_date()} {AppEnv.get_current_time()} - {prefix} : {message}")


    ######################################
    ##### PRIVATE METHOD & FUNCTIONS #####
    ######################################
                
    def _log(self, 
             prefix: Optional[str] = None, 
             msg: Optional[str] = None
             ) -> None:
        """
        Common method to write a message in a log file with current date & timestamp and a prefix (like INFO, WARN...).
        If log folder doesn't exists, it will be created.
        
        Args:
            prefix (str, optional): Prefix for line
            msg (str, optional): Message to write into log file
        """
        
        if AppEnv.is_folder_exists(self._log_folder) == False:
            try:
                os.mkdir(self._log_folder)
            except Exception as err:
                print(f"!!! FAIL !!! Log folder not created")
                raise err
        
        if prefix is None:
            log_format = f"{AppEnv.get_current_date()} {AppEnv.get_current_time()} : {msg}"
        else:
            log_format = f"{AppEnv.get_current_date()} {AppEnv.get_current_time()} - {prefix} : {msg}"
    
        try:
            with open(self._log_file, 'a', encoding='utf-8') as file:
                file.write(f"{log_format}\n")
        except Exception as err:
            print(f"!!! FAIL !!! {self._log_file} not updated")
            raise err
        else:
            file.close()
