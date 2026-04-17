#!/usr/bin/env python
# coding: utf-8

# # Purge WebI - Documents privés 
# 
# Nettoyage des données contenues dans les documents WebI privés d'une plateforme SAP BI 4.3

# ## Etapes
# 
# 1. Authentification
# 2. Récupération du patrimoine (documents WebI de la plateforme)
# 3. Récupération des documents à exclure de la purge (via fichier de configuration)
# 4. Contrôle des CUID (dans la cas ou un CUID à exclure n'est pas présent)
# 5. Génération du listing de purge final (patrimoine - exclusion - rejet)
# 6. Boucle de traitement (pause de 60 sec tous les 100 documents traités)
#    1. purge
#    2. enregistrement
#    3. déchargement
# 7. Déconnexion

# In[ ]:


APPLICATION_NAME = "BIP43_Purge_Private_Documents"


# In[ ]:


import sys
from pathlib import Path

# Remonter les dossiers jusqu'à trouver lib/init/init_code.py
def find_app_home(sentinel: str ="lib/bootstrap/bootstrap.py"):
    current = Path.cwd().resolve()
    root = current.root
    while current != root:
        if (current / sentinel).is_file():
            return current
        current = current.parent
    raise FileNotFoundError(f"Impossible de trouver le fichier sentinelle : {sentinel}")

# Trouver et ajouter APPLICATION_HOME au sys.path
APPLICATION_HOME = find_app_home()
sys.path.insert(0, str(APPLICATION_HOME))
#print(f"APPLICATION_HOME set to: {APPLICATION_HOME}")

from lib.bootstrap.bootstrap import init_env
epy = init_env()


# ## Chargement des classes et variables

# In[ ]:


from concurrent.futures import ThreadPoolExecutor, as_completed
import time
props = epy.cfgprops
yml = epy.cfgyaml
log = epy.log


# In[ ]:


# information d'identification BIP 4.3
url = props.get("bo_url")
account = props.get("bo_account")
password = props.get("bo_password")
type_auth = props.get("bo_authentication")


# In[ ]:


# chargement des classes BIP
bip = epy.load_class(module_name='bip', args=[APPLICATION_HOME, APPLICATION_NAME, url])
webi = epy.load_class(module_name='webi', args=[APPLICATION_HOME, APPLICATION_NAME, bip])


# In[ ]:


batch_size = int(props.get("batch_size"))
sleep = int(props.get("sleep"))
workers = int(props.get("max_workers"))
exclude_private = yml.get("exclude_private_docs") is True


# In[ ]:


start = time.time()


# In[ ]:


log.log("#######################################")
log.log("### PURGE DES DOCUMENTS PRIVES WEBI ###")
log.log("#######################################")
log.log("")


# ## Authentification & Accès

# In[ ]:


log.info(f"## authentification sur la plateforme '{url}' ##")


# In[ ]:


# Connexion
token = bip.set_token(base_url=url, username=account, password=password, auth_type=type_auth)
if token:
    log.info("Authentification réussie")
else:
    log.error("Echec d'authentication")
log.log("")  


# ## Liste des documents & dossiers

# In[ ]:


log.info(f"## récupération du patrimoine de documents WebI ##")

sql_all_docs = props.get("list_all_documents")
sql_all_folders = props.get("list_all_folders")

documents = webi.request_cms(sql_all_docs)
folders = webi.request_cms(sql_all_folders)


# In[ ]:


# les FavoritesFolder sont les racines personnelles — pas besoin de SI_PATH
favorites_ids = {f["SI_ID"] for f in folders if f["SI_KIND"] == "FavoritesFolder"}
personal_folder_ids = webi.get_all_personal_folder_ids(folders, favorites_ids)
docs_in_private_folder = [d for d in documents if d["SI_PARENT_FOLDER"] in personal_folder_ids]


# In[ ]:


#log.info(f"-- nombre de documents total: {len(documents)}")
log.info(f"-- nombre de documents 'privés': {len(docs_in_private_folder)}")
log.log("")


# ## Construction des exclusions

# In[ ]:


log.info(f"## construction des exclusions ##")


# In[ ]:


# liste des CUID à exclure
exclude_cuid = yml.get("exclude_list")
log.info(f"-- nombre prévisionnel de documents à exclure (via CUID): {len(exclude_cuid)} ")

# vérification que les CUID à exclure sont bien listés (warning dans le cas contraire)
log.log("")
log.info(f"contrôle des CUID à exclure...")
cuids_in_documents = {doc["SI_CUID"] for doc in docs_in_private_folder}
missing_cuid = [cuid for cuid in exclude_cuid if cuid not in cuids_in_documents]
if missing_cuid:
    for cuid in missing_cuid:
        log.warning(f"CUID introuvable dans le patrimoine des documents: {cuid}")



# In[ ]:


# liste des documents exclus (par CUID et/ou  Favoris utilisateurs )
excluding_list = [d for d in docs_in_private_folder if d["SI_CUID"] in exclude_cuid]
excluding_list_cuid = {x["SI_CUID"] for x in excluding_list}


# In[ ]:


# affichage
log.log("")
log.info(f"-- nombre réel de documents à exclure de la purge: {len(excluding_list)}")
for x in excluding_list:
    log.log(f"-> {x['SI_ID']} - {x['SI_CUID']} - {x['SI_NAME']}")
log.log("")


# ## Lancement de la purge

# In[ ]:


# liste finale des documents à purger
log.info(f"## lancement du traitement de purge des documents ##")
purge_list = [d for d in docs_in_private_folder if d["SI_CUID"] not in excluding_list_cuid]
log.info(f"-- nombre total de documents à purger: {len(purge_list)}")
log.log("")


# In[ ]:


# liste des idenfitants pour boucle de purge
ids_purge = sorted(doc["SI_ID"] for doc in purge_list)


# In[ ]:


compteur = 0
erreurs = 0
results = []

with ThreadPoolExecutor(max_workers=workers) as executor:
    futures = {executor.submit(webi.set_purge_doc, id): id for id in ids_purge}

    for i, future in enumerate(as_completed(futures), start=1):
        id = futures[future]
        try:
            purged, saved, unloaded = future.result()
            if purged and saved and unloaded:
                log.info(f"Purge ({id}): OK")
                compteur += 1
            else:
                log.warning(f"Purge ({id}): partielle -> purge={purged} save={saved} unload={unloaded}")
                erreurs += 1
        except Exception as err:
            log.error(f"Erreur purge ({id}): {err}")
            erreurs += 1

        # Pause adaptative pour stabilisation du WIPS
        if i % batch_size == 0:
            pause = sleep / workers
            log.info(f"** {compteur}/{len(purge_list)} documents traités - pause adaptative de {pause:.0f}s **")
            time.sleep(pause)
log.log("")


# In[ ]:


# log.info(f"-- nombre d'itérations produites / nombre documents à purger: {compteur}/{len(purge_list)}")
log.info(f"-- documents à purger   : {len(purge_list)}")
log.info(f"-- documents exclus     : {len(excluding_list)}")
log.info(f"-- CUID manquants       : {len(missing_cuid)}")
log.info(f"-- documents traités    : {compteur}")
log.info(f"-- documents en erreur  : {erreurs}")
log.log("")


# ## Deconnexion

# In[ ]:


# Deconnexion
log.info("## Deconnexion ##")
bip.unset_token()
log.log("")
log.info(f"### Traitement terminée en {time.time() - start:.1f} secondes ###")

