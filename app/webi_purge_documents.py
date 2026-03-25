#!/usr/bin/env python
# coding: utf-8

# # Purge des documents WebI

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


bip = epy.load_class(module_name='bip', args=[APPLICATION_HOME, APPLICATION_NAME, url])


# In[6]:


webi = epy.load_class(module_name='webi', args=[APPLICATION_HOME, APPLICATION_NAME, bip])


# In[7]:


batch_size = int(props.get("batch_size"))
# print(type(batch_size))
sleep = int(props.get("sleep"))
# print(type(sleep))


# In[ ]:


log.log("################################")
log.log("### PURGE DES DOCUMENTS WEBI ###")
log.log("################################")
log.log("")


# In[ ]:


log.info(f"## authentification sur la plateforme '{url}' ##")


# ## Authentification & Accès

# In[ ]:


# Connexion
token = bip.set_token(base_url=url, username=account, password=password, auth_type=type_auth)
if token:
    log.info("Authentification réussie")
else:
    log.error("Echec d'authentication")
log.log("")  


# ## Liste des documents

# In[ ]:


log.info(f"## récupération du patrimoine de documents WebI ##")
documents = webi.get_doc_list()
# nb_doc = len(documents)
log.info(f"-- nombre de documents total: {len(documents)}")
log.log("")


# ## Gestion des listes de purge et d'exclusion

# In[ ]:


log.info(f"## génération des listes de traitement ##")

# liste des CUID à exclure
exclude_cuid = yml.get("exclude_list")
log.info(f"-- nombre prévisionnel de documents à exclure de la purge: {len(exclude_cuid)} ")

# controle des cuid
log.log("")
log.info(f"contrôle des CUID à exclure...")
cuids_in_documents = {doc["cuid"] for doc in documents}
missing_cuid = [cuid for cuid in exclude_cuid if cuid not in cuids_in_documents]
if missing_cuid:
    for cuid in missing_cuid:
        log.warning(f"CUID introuvable dans le patrimoine des documents: {cuid}")

# liste des documents exclus
excluding_list = [d for d in documents if d["cuid"] in exclude_cuid]

# affichage en log
log.log("")
log.info(f"-- nombre réel de documents à exclure de la purge: {len(excluding_list)}")
for x in excluding_list:
    log.log(f"-> {x['id']} - {x['cuid']} - {x['name']}")
log.log("")


# ## Gestion de la purge

# In[ ]:


# liste des documents à purger
log.info(f"## début du traitement de purge des documents ##")
purge_list = [d for d in documents if d["cuid"] not in exclude_cuid]
log.info(f"-- nombre total de documents à purger: {len(purge_list)}")
log.log("")


# In[14]:


# liste des idenfitants pour boucle de purge
ids_purge = {doc["id"] for doc in purge_list}


# In[ ]:


compteur: int = 0
for id in ids_purge:
    purged, saved, unloaded = webi.set_purge_doc(id)
    if purged and saved:
        log.info(f"Purge du document ({id}): purge -> {purged} - enregistrement -> {saved} -> déchargement -> {unloaded}")
    else:
        log.warning(f"Purge du document ({id}): purge -> {purged} - enregistrement -> {saved}")
    compteur += 1

    if (compteur + 1) % batch_size == 0:
        log.info(f"** {compteur + 1} documents traités — pause de stabilisation ({sleep} sec)... **")
        time.sleep(sleep)
log.log("")


# In[ ]:


log.info(f"-- nombre d'itérations produites / nombre documents à purger: {compteur}/{len(purge_list)}")
log.log("")


# ## Deconnexion

# In[ ]:


# Deconnexion
log.info("## Deconnexion ##")
bip.unset_token()

