#!/usr/bin/env python
# coding: utf-8

# # Purge des documents WebI
# 
# Nettoyage des données contenues dans les documents WebI (publics et privés) d'une plateforme SAP BI 4.3

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

# In[1]:


APPLICATION_NAME = "BIP43_Purge_Documents"


# In[2]:


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

# In[3]:


import time
props = epy.cfgprops
yml = epy.cfgyaml
log = epy.log


# In[4]:


# information d'identification BIP 4.3
url = props.get("bo_url")
account = props.get("bo_account")
password = props.get("bo_password")
type_auth = props.get("bo_authentication")


# In[5]:


# chargement des classes BIP
bip = epy.load_class(module_name='bip', args=[APPLICATION_HOME, APPLICATION_NAME, url])
webi = epy.load_class(module_name='webi', args=[APPLICATION_HOME, APPLICATION_NAME, bip])


# In[6]:


batch_size = int(props.get("batch_size"))
sleep = int(props.get("sleep"))
# exclude_private = bool(yml.get("exclude_private_docs"))
exclude_private = yml.get("exclude_private_docs") is True


# In[7]:


log.log("################################")
log.log("### PURGE DES DOCUMENTS WEBI ###")
log.log("################################")
log.log("")


# ## Authentification & Accès

# In[8]:


log.info(f"## authentification sur la plateforme '{url}' ##")


# In[9]:


# Connexion
token = bip.set_token(base_url=url, username=account, password=password, auth_type=type_auth)
if token:
    log.info("Authentification réussie")
else:
    log.error("Echec d'authentication")
log.log("")  


# ## Liste des documents
# - liste exportée dans APPLICATION_HOME/tmp

# In[10]:


log.info(f"## récupération du patrimoine de documents WebI ##")
documents = webi.get_doc_list(store=True)
log.info(f"-- nombre de documents total: {len(documents)}")
log.log("")


# ## Gestion des exclusions

# In[11]:


log.info(f"## gestion des exclusions ##")


# In[12]:


# liste des CUID à exclure
exclude_cuid = yml.get("exclude_list")
log.info(f"-- nombre prévisionnel de documents à exclure (via CUID): {len(exclude_cuid)} ")

# vérification que les CUID à exclure sont bien listés (warning dans le cas contraire)
log.log("")
log.info(f"contrôle des CUID à exclure...")
cuids_in_documents = {doc["cuid"] for doc in documents}
missing_cuid = [cuid for cuid in exclude_cuid if cuid not in cuids_in_documents]
if missing_cuid:
    for cuid in missing_cuid:
        log.warning(f"CUID introuvable dans le patrimoine des documents: {cuid}")


# In[13]:


# liste des documents privés (si exclusion activée)
if exclude_private:
    docs_details = []
    # for d in documents:
    #     doc_info = webi.get_doc_info(doc_id=d["id"])
    #     docs_details.append(doc_info)

    # concurrent.futures pour paralléliser
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=10) as executor:
        docs_details = list(executor.map(lambda d: webi.get_doc_info(d["id"]), documents))

    private_docs = [d for d in docs_details if d["path"] == "Personal Folders"]
    private_cuid = [doc["cuid"] for doc in private_docs]
    log.info(f"-- nombre prévisionnel de documents à exclure (via Favoris): {len(private_cuid)} ")
else:
    private_cuid= []
log.log("")


# In[14]:


# liste des documents exclus (par CUID et/ou  Favoris utilisateurs )
excluding_list = [d for d in documents if d["cuid"] in exclude_cuid or d["cuid"] in private_cuid]
excluding_list_cuid = {x["cuid"] for x in excluding_list}


# In[15]:


# affichage
log.log("")
log.info(f"-- nombre réel de documents à exclure de la purge: {len(excluding_list)}")
for x in excluding_list:
    log.log(f"-> {x['id']} - {x['cuid']} - {x['name']}")
log.log("")


# ## Gestion de la purge

# In[16]:


# liste finale des documents à purger
log.info(f"## début du traitement de purge des documents ##")
purge_list = [d for d in documents if d["cuid"] not in excluding_list_cuid]
log.info(f"-- nombre total de documents à purger: {len(purge_list)}")
log.log("")


# In[17]:


# liste des idenfitants pour boucle de purge
# ids_purge = {doc["id"] for doc in purge_list}
ids_purge = sorted(doc["id"] for doc in purge_list)
# len(ids_purge)


# In[18]:


compteur: int = 0
erreurs: int = 0
for id in ids_purge:
    try:
        purged, saved, unloaded = webi.set_purge_doc(id)
        if purged and saved and unloaded:
            log.info(f"Purge du document ({id}): purge -> {purged} - enregistrement -> {saved} -> déchargement -> {unloaded}")
            compteur += 1
        else:
            log.warning(f"Purge du document ({id}): purge -> {purged} - enregistrement -> {saved} -> déchargement -> {unloaded}")
            erreurs += 1

        if compteur % batch_size == 0:
            log.info(f"** {compteur} documents traités — pause de stabilisation ({sleep} sec)... **")
            time.sleep(sleep)
    except Exception as err:
        log.error(f"Erreur de purge sur le document ({id}): {err}")
        erreurs += 1
        continue  # on continue malgré l'erreur
log.log("")


# In[19]:


# log.info(f"-- nombre d'itérations produites / nombre documents à purger: {compteur}/{len(purge_list)}")
log.info(f"-- documents à purger   : {len(purge_list)}")
log.info(f"-- documents exclus     : {len(excluding_list)}")
log.info(f"-- CUID manquants       : {len(missing_cuid)}")
log.info(f"-- documents traités    : {compteur}")
log.info(f"-- documents en erreur  : {erreurs}")
log.log("")


# ## Deconnexion

# In[20]:


# Deconnexion
log.info("## Deconnexion ##")
bip.unset_token()

