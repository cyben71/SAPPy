__version__= "1.0.0"

import requests
import json
from typing import Optional, Dict, Any
from lib.bootstrap.logger import Logger


class BIPlatform:
    """
    Classe utilitaire pour gérer les objets de la plateforme SAP Business Objects.
    """

    def __init__(self, app_home: str, app_name: str, url: str):
        """
        Constructor
        Args:
            app_home (str): Emplacement parent de l'application
            app_name (str): Nom de l'application. Valeur par defaut: Default
        """
        
        self.log = Logger(app_home, app_name)

        # variables d'instances (masqué pour plus de clareté dans IDE)
        self._application_home = app_home
        self._application_name = app_name
        self.BIP_URL = url

        # Jeton d'identification sur la plateforme BI
        self.token: str = None
        
    
    ########################################
    ##### FONCTIONS & METHODES PUBLICS #####
    ########################################
    """
    @property => a utiliser quand on veut retourner un objet issue du constructor (self)
    @staticmethod => a utiliser quand on veut retourner un objet utilisant une lib importée dans cette classe. Pas besoin d'instancier
    """
    
    @property
    def get_bip_url(self) -> Any:
        """
        Retourne l'URL d'accès au service RestFul de la plateforme BI contenu dans le contexte de variables partagées
        """
        # return self._context.get("url")
        return self.BIP_URL
    
    @property
    def get_token(self) -> Any:
        """
        Retourne le jeton d'identification de la session utilisateur contenu dans le contexte de variables partagées
        """
        # return self._context.get("token")
        return self.token

    def set_token(self, base_url: str, username: str, password: str, auth_type: Optional[str] = None) -> str:
        """
        Retourne un jeton d'identification de sessions de l'utilisateur. 
        Les informations d'authentification sont lues depuis conf/application.properties
        Args:
            base_url (str): URL du service RestFul de la plateforme BI
            username (str): Identifiant de l'utilisateur
            password (str): Mot de passe de l'utilisateur
            auth_type (str, facultatif): Type d'authentificaton (secEnterprise, secSAPR3, secWinAD, secLDAP). Par default 'secEnterprise'
        Return:
            token (str): Jeton d'identification lié à la session de l'utilsateur
        """
        if auth_type is None:
            default_auth = 'secEnterprise'
            auth_type = default_auth
        
        url = f"{base_url}/logon/long"
        header = {'Content-Type': 'application/json'}
        credentials = self._get_credentials(username, password, auth_type)

        try:
            response = requests.post(url, headers=header, data=json.dumps(credentials))
            response.raise_for_status()
        except Exception as err:
            self.log.error(f"Echec API - {url} - {err}")
            raise err
        else:
            # mise à jour du jeton d'identification
            self.token = response.headers['X-SAP-LogonToken']
          
        return self.token
    
    def unset_token(self) -> None:
        """
        Ferme la session lié au jeton d'identification de l'utilsateur contenu dans le contexte de variables partagées
        """
        url: str = f"{self.get_bip_url}/logoff"
        token: str = self.get_token
        header: Dict[str, str] = {
            'Content-Type': 'application/json',
            'X-SAP-LogonToken': token
            }
        try:
            response = requests.post(url, headers=header)
            response.raise_for_status()
        except BaseException as err:
            self.log.error(f"Echec API - {url} - {err}")
            raise err
        else:
            # print("Fermeture de session réussie")
            return response.raise_for_status()
        
    
    ########################################
    ##### FONCTIONS & METHODES PRIVEES #####
    ########################################

    def _get_credentials(self, username: str, password: str, auth_type: str) -> Dict[str, str]:
        """
        Retourne un dictionnaire contenant les paramètres d'identification à plateforme BI
        Args:
            username (str): Identifiant de l'utilisateur
            password (str): Mot de passe de l'utilisateur
            auth_type (str, facultatif): Type d'authentificaton (secEnterprise, secSAPR3, secWinAD, secLDAP). Par défaut: 'secEnterprise'
        Return:
            credentials (dict): Dictionnaire de paramètre
        """
        credentials: Dict[str, str] = {}
        try:
            sap_user = username
            sap_pwd = password
            sap_auth = auth_type
        except ValueError as err:
            raise err

        credentials = {
                'userName': sap_user,
                'password': sap_pwd,
                'auth': sap_auth
            }
        return credentials