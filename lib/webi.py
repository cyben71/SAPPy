__version__ = "1.1.0"

import requests
import json
from lib.bootstrap.appenv import AppEnv
from lib.bip import BIPlatform
from lib.bootstrap.logger import Logger
from typing import Any, Optional, Dict, List

class WebIntelligence:
    """
    Classe utilitaire pour gérer les objets de type Web Intelligence de la plateforme SAP Business Objects.
    """
    # caracteres de remplacement pour les XML de planification respectant l'encodage attendu par l'API BO dans le cas de la langue fr-FR (accents)
    REPLACED_CARACTERS = {'é':'Ã©', 'à':'Ã ', 'ê':'Ãª'}

    def __init__(self, app_home: str, app_name:str, bip: BIPlatform):
        """
        Constructor
        Args:
            app_home (str): Emplacement parent de l'application
            app_name (str): Nom de l'application. Valeur par defaut: Default
        """

        self.log = Logger(app_home, app_name)

        # variables d'instances (masqué pour plus de clareté dans IDE)
        self._application_home: str = app_home
        self._application_name: str = app_name

        self.bip: BIPlatform = bip
    
    ########################################
    ##### FONCTIONS & METHODES PUBLICS #####
    ########################################

    ################
    ### DOCUMENT ###
    ################

    def get_doc_info(self, doc_id: int) -> Dict[str, Any]:
        """
        Retourne les informations du document à partir de son ID sous la forme d'un dictionnaire.
                Le dictionnaire JSON est aplati pour permettre son parcours via la fonction data.get(key)
        Args:
            doc_id (int): Identifiant numérique du document WebI
        Return:
            data (dict): Dictionnaire (aplati) de détails du document
        Structure du dictionnaire: 
        • <id> (Integer) The document ID
        • <cuid> (String) The unique document ID
        • <name> (String) The document name
        • <description> (String) The document description
        • <folderId> (Integer) The identifier of the folder of the CMS repository that contains the document
        • <path> (String) The path to the document in the CMS repository directory
        • <updated> (DateTime) The date and the time of the last update
        • <scheduled> (Boolean) true if the document has been scheduled
        • <createdBy> (String) The name of the document creator
        • <lastAuthor> (String) The name of the last person who modified the document
        • <size> (Integer) The size of the document in bytes
        """
        
        url: str = f"{self.bip.get_bip_url}/raylight/v1/documents/{doc_id}"
        raw_data: Dict[str, Any] = {}

        header: Dict[str, str] = self._set_header(type="json")

        try:
            response = requests.get(url, headers=header)
            response.raise_for_status()
        except Exception as err:
            self.log.error(f"Echec API - {url} - {err}")
        else:
            # print(f"Récupération des informations du document ({doc_id}) terminée avec succès")
            raw_data = json.loads(response.text).get('document', {})

        return raw_data

    def get_doc_prompts(self, 
                        doc_id: int, 
                        saved: Optional[bool] = None,
                        ) -> Any:
        """
        Retourne les paramètres d'actualisation (prompts) d'un document Web Intelligence sous la forme d'un arbre XML.
        L'arbre peut être enregistré dans un fichier.
        Args:
            doc_id (int): Identifiant numérique du document WebI
            saved (bool, facultatif): Enregistre l'arbre XML si True. Nom par defaut = prompt_{doc_id}.xml
            temporay_name (bool, défaut=False): Enregistre temporairement l'arbre XML si True. Nom par defaut = tmp_prompt_{doc_id}.xml
        Return:
            data (str): Chaine représentant l'arbre XML des paramètres d'actualisation du document
        """
        header = self._set_header(type="xml")
        url: str = f"{self.bip.get_bip_url}/raylight/v1/documents/{doc_id}/parameters"

        
        try:
            response = requests.get(url, headers=header)
            response.raise_for_status()
        except Exception as err:
            print(f"Echec de récupération des invites d'actualisation du document ({doc_id}) - {err}")
        else:
            print(f"Récupération des invites d'actualisation du document ({doc_id}) terminée avec succès")  
            print()          
            if saved:
                xml_file = f"{self._application_home}/tmp/prompt_{doc_id}.xml"
                if AppEnv.is_folder_exists(f"{self._application_home}/tmp") == False:
                    AppEnv.mkdir(f"{self._application_home}/tmp")

                try:
                    with open (xml_file, 'w', encoding='utf-8') as file:
                        file.write(response.text)
                        file.close
                except BaseException as err:
                    self.log.error(f"Echec API - {url} - {err}")

            return response.text
    
    ### ATTENTION : Fonction désactivée car inadaptée à la production - Problème de perfs sur très gros volume
    # def get_doc_list(self, store: Optional[bool] = None) -> List[Dict[str, Any]]:
    #     """
    #     Retourne la liste des documents WebI de la plateforme sous la forme d'une liste de dictionnaire.
    #     Le dictionnaire JSON est aplati pour permettre son parcours via la fonction data.get(key)
    #     Args:
    #         store (Boolean, Optional): Active l'enregistrement du listing des documents. Désactivé par defaut
    #     Return:
    #         data (list): Liste de dictionnaire (aplati) des documents
    #     Structure du dictionnaire: 
    #     • <id> (Integer) The document ID
    #     • <cuid> (String) The unique document ID
    #     • <name> (String) The document name
    #     • <description> (String) The document description
    #     • <folderId> (Integer) The identifier of the folder of the CMS repository that contains the document
    #     • <scheduled> (Boolean) true if the document has been scheduled
    #     """
        
    #     offset: int = 0
    #     limit: int = 50          # valeur maximale autorisée par l'API
    #     raw_data: Dict[str, Any] = {}
    #     documents: List = []
    #     header: Dict[str, str] = self._set_header(type="json")

    #     while True:
    #         param = {"offset": offset, "limit": limit}
    #         url: str = f"{self.bip.get_bip_url}/raylight/v1/documents"
    #         try:
    #             response = requests.get(url, headers=header, params=param)
    #             response.raise_for_status()
    #         except Exception as err:
    #             self.log.error(f"Echec API - {url} - {err}")
    #         else:
    #             print(f"Récupération de la liste des documents (50) terminée avec succès (offset: {offset})")
    #             raw_data = json.loads(response.text).get("documents", {}).get("document", {})
                
    #         batch = raw_data

    #         # L'API peut renvoyer un dict (1 résultat) ou une liste (n résultats)
    #         if isinstance(batch, dict):
    #             batch = [batch]

    #         # si plus rien dans batch, plus aucun document à récupérer
    #         if not batch:
    #             break                      

    #         # empilement des données récupérées
    #         documents.extend(batch)

    #         # dernière page atteinte
    #         if len(batch) < limit:
    #             break

    #         # incrément d'offset pour avoir les 50 prochains documents
    #         offset += limit

    #     # enregistrement du listing de documents
    #     if store is None: store = False
    #     else: store = store
        
    #     if store:
    #         if AppEnv.is_folder_exists(f"{self._application_home}/tmp") == False:
    #             AppEnv.mkdir(f"{self._application_home}/tmp")

    #         try:
    #             docs_list = f"{self._application_home}/tmp/documents_list_{AppEnv.get_current_date()}.txt"
    #             with open (docs_list, 'w', encoding='utf-8') as file:
    #                 for l in documents:
    #                     file.write(f"{l}\n")
    #                 file.close
    #         except BaseException as err:
    #             self.log.error(f"Echec de sauvegarde de la liste des documents - {err}")
    #         else:
    #             self.log.info(f"Liste des documents enregistrée dans '{docs_list}'")

    #     return documents

    def request_cms(self, query: str) -> List[Dict]:
        """
        Récupère les résultats de la requête transmise au CMS via l'API cmsquery. (équivalent à AdminTools)
        Avantage : interroge directement le CMS, aucune session ouverte sur le WIPS.
        Args:
            query (str): Requête SQL d'interrogation du CMS
        Return:
            data (List): Liste de dictionnaire correspondant au retour du CMS
        """
        url      = f"{self.bip.get_bip_url}/v1/cmsquery"
        page     = 1
        pagesize = 500
        data = []

        header: Dict[str, str] = self._set_header(type="json")

        while True:
            payload = {
                "query": (query)
            }
            params = {"page": page, "pagesize": pagesize}

            try:
                response = requests.post(url, headers=header, json=payload, params=params)
                response.raise_for_status()
            except Exception as err:
                self.log.error(f"Echec cmsquery page {page} - {err}")
                break

            raw_data    = response.json()
            entries = raw_data.get("entries", [])
            # print(entries)

            data.extend(entries)
            
            if not entries:
                break

            if len(entries) < pagesize:
                break   # dernière page

            page += 1

        return data

    def set_purge_doc(self, doc_id: int) -> tuple[bool, bool, bool]:
        """
        Purge les données contenu dans le document WebI
        Args:
            doc_id (int): Identifiant numérique du document WebI
        Returns:
            tuple[bool, bool]: Valeur de retour de l'opération de purge, d'enregistrement et de déchargement du document
        """
        url: str = f"{self.bip.get_bip_url}/raylight/v1/documents/{doc_id}"
        param = {"purge": "true"}
        unload_body = {"document": {"state": "Unused"}}

        header: Dict[str, str] = self._set_header(type="json")
        purge: bool = False
        save: bool = False
        unload: bool = False

        try:
            # purge du document
            response = requests.put(url, headers=header, params=param)
            response.raise_for_status()
            purge = "success" in response.json()

            # enregistrement
            response = requests.put(url, headers=header)
            response.raise_for_status()
            save = "success" in response.json()

            # dechargement (evite surcharge de session du WIPS)
            response = requests.put(url, headers=header, json=unload_body)
            response.raise_for_status()
            unload = "success" in response.json()
        except Exception as err:
            self.log.error(f"Echec API - {url} - {err}")
   
        return purge, save, unload

    def get_all_personal_folder_ids(self, folders: List[Dict], root_ids: set) -> set:
        """
        Recherche la liste des dossiers contenus dans les dossiers utilisateurs (Favoris / Personal Folders)
        Args:
            folders (List[Dict]): Liste (de dictionnaires )des dossiers présents sur la plateforme
            root_ids (set): Set des identifiants des dossiers utilisateurs 
        Returns:
            set: Set des identifiants des dossiers contenus dans les dossiers utilisateurs
        """
        all_ids = set(root_ids)
        changed = True
        while changed:
            changed = False
            for f in folders:
                if f["SI_ID"] not in all_ids and f.get("SI_PARENT_FOLDER") in all_ids:
                    all_ids.add(f["SI_ID"])
                    changed = True
        return all_ids

    ######################
    ### DATA PROVIDERS ###
    ######################

    def get_doc_dp(self, doc_id: int, simplified: Optional[bool] = None) -> List[Dict[str,Any]]:
        """
        Retourne la liste des fournisseurs de données d'un document sous la forme d'un dictionnaire.
        Args:
            doc_id (int): Identifiant numérique du document.
            simplified (bool, Facultatif)
        Return:
            data (dict): Dictionnaire (aplati) des fournisseurs de données du document.
        Structure du dictionnaire:
        • <id>
        • <name>
        • <dataSourceId> is the data source identifier
        • <dataSourceType> is the type of data source (unx, unv, bex, excel, fhsql, webi)
        • <updated> is the date of the last update
        """
        url = f"{self.bip.get_bip_url}/raylight/v1/documents/{doc_id}/dataproviders"
        header = self._set_header(type="json")
        data: List[Dict[str, Any]] = []
        raw_data: List[Dict[str, Any]] = []
        keys_to_keep: List[str] = ["id", "name", "dataSourceId", "dataSourceType", "updated", "isPartial", "rowCount"]

        if simplified is None:
            simplified = True

        try:
            response = requests.get(url, headers=header)
            response.raise_for_status()
        except Exception as err:
            # print(f"Echec de récupération des fournisseurs de données du document ({doc_id}) - {err}")
            self.log.error(f"Echec API - {url} - {err}")
        else:
            # print(f"Récupération des founisseurs de données du document ({doc_id}) terminée avec succès") 
            raw_data = json.loads(response.text).get("dataproviders", {}).get("dataprovider",{})
        
        if simplified:
            filtered_list: List[Dict[str, Any]] = []
            filtered_item: Dict[str, Any]
            for item in raw_data:
                filtered_item = {k: item.get(k) for k in keys_to_keep}
                filtered_list.append(filtered_item)
            data = filtered_list
        else:
            data = raw_data
        return data
    
    def get_dp_details(self, doc_id: int, simplified: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        Retourne le detail des fournisseurs de données d'un document sous la forme d'une liste de dictionnaire.
        Args:
            doc_id (int): Identifiant numérique du document.
            simplified (bool, Facultatif): Simplification des résultats en limitant les valeurs renvoyées par l'API
        Return:
            data (list): Liste de dictionnaire de détails des fournisseurs de données du document.
        """

        lst_dp_id: List[Any] = []
        list_dataproviders: List[Dict[str, Any]] = []
        data: List[Dict[str, Any]] = []
        raw_data: List[Dict[str, Any]] = []
        

        url = f"{self.bip.get_bip_url}/raylight/v1/documents/{doc_id}/dataproviders"
        header = self._set_header(type="json")
        
        if simplified is None:
            simplified = True

        # Récupération de la liste des fournisseurs du document (identifiant uniquement)
        try:
            response = requests.get(url, headers=header)
            response.raise_for_status()
        except Exception as err:
            # print(f"Echec de récupération des identifiants des fournisseurs de données du document ({doc_id}) - {err}")
            self.log.error(f"Echec API - {url} - {err}")
            raise err

        self.log.info(f"Récupération des identifiants des fournisseurs de données du document ({doc_id}) terminée avec succès") 
        raw_data = json.loads(response.text).get("dataproviders", {}).get("dataprovider",{})    
        for dp in raw_data:
            lst_dp_id.append(dp.get("id"))

        #Récupération des détails de chaque fournisseurs
        for dp_id in lst_dp_id:
            url = f"{self.bip.get_bip_url}/raylight/v1/documents/{doc_id}/dataproviders/{dp_id}"
            try:
                response = requests.get(url, headers=header)
                response.raise_for_status()
            except Exception as err:
                # print(f"Echec de récupération du détail du fournisseur de données ({dp_id}) du document ({doc_id}) - {err}")
                self.log.error(f"Echec API - {url} - {err}")
                raise err
            
            # print(f"Récupération du détail du fournisseurs de données ({dp_id}) du document ({doc_id}) terminée avec succès")
            dataprovider = json.loads(response.text).get("dataprovider")

            # Alimentation de la liste de dictionnaire des fournisseurs (restitution complete)
            list_dataproviders.append(dataprovider)

        if simplified:
            filtered_list: List[Any] = []
            keys_to_keep: List[str] = ['@dataType', '@qualification', 'name', 'description' ]
            details: Dict[str, Any] = {}

            for dp in list_dataproviders:
                # Parcours des objets composant chaque fournisseurs (beaucoup de clé/valeur inutile pour le besoin)
                expressions = dp.get("dictionary",{}).get("expression", [])
                # Filtre sur les clés des objets à conserver dans chaque dictionnaire d'objet
                for item in expressions:
                    filtered_item: Dict[str, Any] = {key: item.get(key) for key in keys_to_keep}
                    #print(filtered_item)
                    filtered_list.append(filtered_item)

                # construction de la liste de dictionnaire finale
                details = {
                    "id": dp.get("id"),
                    "name": dp.get("name"),
                    "dataSourceId": dp.get("dataSourceId"),
                    "dataSourceCuid": dp.get("dataSourceCuid"),
                    "dataSourceName": dp.get("dataSourceName"),
                    "dataSourceType": dp.get("dataSourceType"),
                    "objets": filtered_list
                }
                data.append(details)     
        else:
            data = list_dataproviders

        return data
    
    
    ########################################
    ##### FONCTIONS & METHODES PRIVEES #####
    ######################################## 

     
    def _set_header(self, type: Optional[str] = None  ) -> Dict[str, str]:
        """
        Renvoi le dictionnaire d'entête pour les requêtes API
        Args:
            type (str, facultatif): Format accepté et renvoyé dans l'entête de requête. Par défaut: 'json'
        Return: 
            data (dict): Dictionnaire d'entête
        """
        data: Dict[str, str] = {}
        # token = self._context.get("token")
        token = self.bip.get_token
        available_format = ['json', 'xml']

        if type is None:
            type = "json"
        else:
            if type not in available_format: 
                raise ValueError(f"Type de destination non disponible ({type}). Format disponible: {available_format}")
        
        data = {
            "Content-Type": f"application/{type}",
            "Accept": f"application/{type}",
            "X-SAP-LogonToken": token,
            'X-SAP-PVL': 'fr-FR'
        }
        return data
    