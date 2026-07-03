__version__ = "1.1.1"

import requests
import json
from lib.bootstrap.appenv import AppEnv
from lib.bip import BIPlatform
from lib.bootstrap.logger import Logger
from typing import Any, Optional, Dict, List
import time

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

    def set_purge_doc(self, doc_id: int, retries: int = 3) -> tuple[bool, bool, bool]:
        """
        Purge les données contenu dans le document WebI
        Args:
            doc_id (int): Identifiant numérique du document WebI
            retries (int): Nombre de tentatives en cas d'échec de l'instruction
        Returns:
            tuple[bool, bool]: Valeur de retour de l'opération de purge, d'enregistrement et de déchargement du document
        """
        url: str = f"{self.bip.get_bip_url}/raylight/v1/documents/{doc_id}"
        param = {"purge": "true"}
        unload_body = {"document": {"state": "Unused"}}
        header = self._set_header(type="json")

        for attempt in range(1, retries + 1):
            purge = save = unload = False
            try:
                response = requests.put(url, headers=header, params=param)
                response.raise_for_status()
                purge = "success" in response.json()

                response = requests.put(url, headers=header)
                response.raise_for_status()
                save = "success" in response.json()

                response = requests.put(url, headers=header, json=unload_body)
                response.raise_for_status()
                unload = "success" in response.json()

                return purge, save, unload

            except Exception as err:
                wait = 2 ** attempt  # 2s, 4s, 8s
                self.log.warning(f"Tentative {attempt}/{retries} échouée sur ({doc_id}): {err} — attente {wait}s")
                if attempt < retries:
                    time.sleep(wait)

        self.log.error(f"Echec définitif sur ({doc_id}) après {retries} tentatives")
        return False, False, False
    
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
    
    def set_repoint_universe(
        self,
        doc_id: int,
        target_universe_id: int,
        dp_ids: Optional[List[str]] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Repointe le(s) fournisseur(s) de données d'un document Webi vers un nouvel univers
        (typiquement : migration UNV → UNX).

        Workflow API :
            1. GET  /documents/{docId}/dataproviders/mappings
                    ?originDataproviderIds={dp_id}&targetDatasourceId={target_universe_id}
               → BO calcule le mapping automatique objet par objet
            2. Vérification que tous les mappings sont status="Ok"
            3. POST /documents/{docId}/dataproviders/mappings
                    ?originDataproviderIds={dp_id}&targetDatasourceId={target_universe_id}
               body = XML retourné par le GET  → commit du repointage
            4. PUT  /documents/{docId}  (sans body)  → sauvegarde CMS

        Args:
            doc_id (int)              : Identifiant du document WebI
            target_universe_id (int)  : ID (SI_ID) de l'univers cible (UNX)
            dp_ids (List[str], opt.)  : Liste des IDs de DP à repointer (ex: ['DP0']).
                                        Si None, tous les DP du document sont traités.
            force (bool, défaut=False): Si True, commite même si certains mappings
                                        sont en statut "Unresolved" (à utiliser avec précaution)
        Returns:
            result (Dict): Rapport d'exécution avec les clés :
                • success   (bool)       : True si l'opération s'est terminée sans erreur bloquante
                • committed (List[str])  : DP effectivement repointés
                • skipped   (List[str])  : DP ignorés (mapping incomplet sans force=True)
                • errors    (List[str])  : DP en erreur
                • mapping_details (dict) : Détail du mapping par DP
        """
        import xml.etree.ElementTree as ET

        result: Dict[str, Any] = {
            "success":        False,
            "committed":      [],
            "skipped":        [],
            "errors":         [],
            "mapping_details": {}
        }

        base_url   = self.bip.get_bip_url
        header_xml = self._set_header(type="xml")

        # -------------------------------------------------------
        # 0. Récupération des DP si dp_ids non fourni
        # -------------------------------------------------------
        if dp_ids is None:
            all_dp = self.get_doc_dp(doc_id, simplified=True)
            if not all_dp:
                self.log.error(f"[repoint] Aucun dataprovider trouvé sur le document {doc_id}")
                return result
            # On traite uniquement les DP de type unv (la cible est unx)
            dp_ids = [
                dp["id"] for dp in all_dp
                if dp.get("dataSourceType", "").lower() in ("unv", "unx")
            ]
            if not dp_ids:
                self.log.warning(
                    f"[repoint] Aucun DP de type unv/unx sur le document {doc_id}. "
                    f"Types trouvés : {[dp.get('dataSourceType') for dp in all_dp]}"
                )
                return result

        self.log.info(f"[repoint] Document {doc_id} — DP à traiter : {dp_ids}")

        # -------------------------------------------------------
        # 1+2+3. Pour chaque DP : GET mapping → vérif → POST commit
        # -------------------------------------------------------
        mapping_url = f"{base_url}/raylight/v1/documents/{doc_id}/dataproviders/mappings"

        for dp_id in dp_ids:
            params = {
                "originDataproviderIds": dp_id,
                "targetDatasourceId":    target_universe_id
            }

            # --- GET : calcul du mapping automatique ---
            try:
                self.log.info(f"[repoint] GET mapping — DP={dp_id} → univers cible={target_universe_id}")
                resp_get = requests.get(mapping_url, headers=header_xml, params=params)
                resp_get.raise_for_status()
                mapping_xml = resp_get.text
            except Exception as err:
                self.log.error(f"[repoint] Echec GET mapping DP={dp_id} : {err}")
                result["errors"].append(dp_id)
                continue

            # --- Vérification des statuts de mapping ---
            mapping_status, unresolved = self._parse_mapping_status(mapping_xml)
            result["mapping_details"][dp_id] = {
                "total":      len(mapping_status),
                "ok":         sum(1 for s in mapping_status.values() if s == "Ok"),
                "unresolved": unresolved
            }

            if unresolved and not force:
                self.log.warning(
                    f"[repoint] DP={dp_id} — {len(unresolved)} objet(s) non mappé(s) : {unresolved}. "
                    f"Utilisez force=True pour forcer le commit."
                )
                result["skipped"].append(dp_id)
                continue

            if unresolved and force:
                self.log.warning(
                    f"[repoint] DP={dp_id} — force=True : commit malgré {len(unresolved)} objet(s) non mappé(s)."
                )

            # --- POST : commit du repointage ---
            try:
                self.log.info(f"[repoint] POST commit mapping — DP={dp_id}")
                resp_post = requests.post(
                    mapping_url,
                    headers=header_xml,
                    params=params,
                    data=mapping_xml.encode("utf-8")
                )
                resp_post.raise_for_status()
                self.log.info(f"[repoint] DP={dp_id} — repointage commité avec succès.")
                result["committed"].append(dp_id)
            except Exception as err:
                self.log.error(f"[repoint] Echec POST commit DP={dp_id} : {err} — réponse : {getattr(err, 'response', {})}")
                result["errors"].append(dp_id)
                continue
        # -------------------------------------------------------
        # 4. Sauvegarde CMS (si au moins 1 DP commité)
        # -------------------------------------------------------
        if result["committed"]:
            doc_url = f"{base_url}/raylight/v1/documents/{doc_id}"
            try:
                self.log.info(f"[repoint] Sauvegarde CMS du document {doc_id}")
                resp_save = requests.put(doc_url, headers=header_xml)
                resp_save.raise_for_status()
                self.log.info(f"[repoint] Document {doc_id} sauvegardé (HTTP {resp_save.status_code}).")
            except Exception as err:
                self.log.error(f"[repoint] Echec sauvegarde document {doc_id} : {err}")
                result["errors"].append(f"save_doc_{doc_id}")

        result["success"] = len(result["errors"]) == 0
        self.log.info(
            f"[repoint] Résultat — committed={result['committed']} | "
            f"skipped={result['skipped']} | errors={result['errors']}"
        )
        self.log.log("")

        return result
    
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


    def _parse_mapping_status(self, mapping_xml: str):
        """
        Parse le XML de mapping retourné par GET /dataproviders/mappings.
        Retourne :
            mapping_status (dict) : {source_id: status}
            unresolved     (list) : liste des source_id non mappés
        """
        import xml.etree.ElementTree as ET

        mapping_status: Dict[str, str] = {}
        unresolved: List[str] = []

        try:
            root = ET.fromstring(mapping_xml)
            for mapping in root.iter("mapping"):
                status    = mapping.get("status", "Unknown")
                src_node  = mapping.find("source")
                src_id    = ""
                if src_node is not None:
                    id_node = src_node.find("id")
                    src_id  = id_node.text.strip() if id_node is not None and id_node.text else "?"

                mapping_status[src_id] = status
                if status != "Ok":
                    unresolved.append(src_id)
        except ET.ParseError as e:
            self.log.error(f"[repoint] Erreur de parsing XML mapping : {e}")

        return mapping_status, unresolved