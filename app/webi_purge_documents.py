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
# 6. Boucle de traitement avec parallélisation (traitement de plusieurs documents en même temps)
#    1. purge webi
#    2. enregistrement webi
#    3. déchargement wips
#    4. pause adaptative de x secondes en fonction de la pile de documents traités
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


from concurrent.futures import ThreadPoolExecutor, as_completed
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
workers = int(props.get("max_workers"))
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


# ## Liste des documents & dossiers

# In[10]:


# # propager aux sous-dossiers via SI_PARENT_FOLDER
# def get_all_personal_folder_ids(folders: list[dict], root_ids: set) -> set:
#     all_ids = set(root_ids)
#     changed = True
#     while changed:
#         changed = False
#         for f in folders:
#             if f["SI_ID"] not in all_ids and f.get("SI_PARENT_FOLDER") in all_ids:
#                 all_ids.add(f["SI_ID"])
#                 changed = True
#     return all_ids


# In[11]:


log.info(f"## récupération du patrimoine de documents WebI ##")

sql_all_docs = props.get("list_all_documents")
sql_all_folders = props.get("list_all_folders")

documents = webi.request_cms(sql_all_docs)
folders = webi.request_cms(sql_all_folders)


# ### DEBUG On - Listing et contenu des Dossiers utilisateurs (Favoris)

# In[12]:


# # répartition par SI_KIND
# from collections import Counter

# kinds_count = Counter(f["SI_KIND"] for f in folders)
# print("Répartition par SI_KIND :")
# for kind, count in kinds_count.items():
#     print(f"  {kind} : {count}")

# print(f"\nTotal dossiers récupérés : {len(folders)}")

# # dossiers avec OBTYPE 18 quelque part dans le PATH
# personal = [f for f in folders if any(
#     f["SI_PATH"].get(f"SI_FOLDER_OBTYPE{i}") == 18
#     for i in range(1, f["SI_PATH"].get("SI_NUM_FOLDERS", 0) + 1)
# )]
# print(f"Dossiers avec OBTYPE 18 dans PATH : {len(personal)}")

# # dossiers racines utilisateur (OBTYPE1 == 18) — attendu ~42
# roots = [f for f in folders if f["SI_PATH"].get("SI_FOLDER_OBTYPE1") == 18]
# print(f"Dossiers racines utilisateur (OBTYPE1==18) : {len(roots)}")

# # dossiers sans SI_PATH ou SI_PATH vide
# no_path = [f for f in folders if not f.get("SI_PATH")]
# print(f"Dossiers sans SI_PATH : {len(no_path)}")
# for f in no_path:
#     print(f"  SI_ID={f['SI_ID']} | SI_KIND={f['SI_KIND']} | SI_NAME={f['SI_NAME']}")

# # afficher le SI_PATH de tous les FavoritesFolder
# favorites = [f for f in folders if f["SI_KIND"] == "FavoritesFolder"]
# print(f"Nombre de FavoritesFolder : {len(favorites)}")

# for f in favorites:
#     print(f"  SI_ID={f['SI_ID']} | SI_NAME={f['SI_NAME']} | SI_PATH={f['SI_PATH']}")


# ### DEBUG Off

# In[13]:


# les FavoritesFolder sont les racines personnelles — pas besoin de SI_PATH
favorites_ids = {f["SI_ID"] for f in folders if f["SI_KIND"] == "FavoritesFolder"}

personal_folder_ids = webi.get_all_personal_folder_ids(folders, favorites_ids)
public_folder_ids   = {f["SI_ID"] for f in folders if f["SI_ID"] not in personal_folder_ids}

docs_in_private_folder = [d for d in documents if d["SI_PARENT_FOLDER"] in personal_folder_ids]
docs_in_public_folder  = [d for d in documents if d["SI_PARENT_FOLDER"] not in personal_folder_ids]


# In[14]:


log.info(f"-- nombre de documents total: {len(documents)}")
log.info(f"-- nombre de documents 'privés': {len(docs_in_private_folder)}")
log.info(f"-- nombre de documents 'publics': {len(docs_in_public_folder)}")

log.log("")


# ## Construction des exclusions

# In[15]:


log.info(f"## construction des exclusions ##")


# In[16]:


# liste des CUID à exclure
exclude_cuid = yml.get("exclude_list")
log.info(f"-- nombre prévisionnel de documents à exclure (via CUID): {len(exclude_cuid)} ")

# vérification que les CUID à exclure sont bien listés (warning dans le cas contraire)
log.log("")
log.info(f"contrôle des CUID à exclure...")
cuids_in_documents = {doc["SI_CUID"] for doc in documents}
missing_cuid = [cuid for cuid in exclude_cuid if cuid not in cuids_in_documents]
if missing_cuid:
    for cuid in missing_cuid:
        log.warning(f"CUID introuvable dans le patrimoine des documents: {cuid}")


# In[17]:


# liste des documents privés (si exclusion activée)
if exclude_private:
    private_cuid = [doc["SI_CUID"] for doc in docs_in_private_folder]
    log.info(f"-- nombre prévisionnel de documents personnel à exclure : {len(private_cuid)} ")
else:
    private_cuid= []
log.log("")


# In[18]:


# liste des documents exclus (par CUID et/ou  Favoris utilisateurs )
excluding_list = [d for d in documents if d["SI_CUID"] in exclude_cuid or d["SI_CUID"] in private_cuid]
excluding_list_cuid = {x["SI_CUID"] for x in excluding_list}


# In[19]:


# affichage
log.log("")
log.info(f"-- nombre réel de documents à exclure de la purge: {len(excluding_list)}")
for x in excluding_list:
    log.log(f"-> {x['SI_ID']} - {x['SI_CUID']} - {x['SI_NAME']}")
log.log("")


# ## Lancement de la purge

# In[20]:


# liste finale des documents à purger
log.info(f"## lancement du traitement de purge des documents ##")
purge_list = [d for d in documents if d["SI_CUID"] not in excluding_list_cuid]
log.info(f"-- nombre total de documents à purger: {len(purge_list)}")
log.log("")


# In[21]:


# liste des idenfitants pour boucle de purge
ids_purge = sorted(doc["SI_ID"] for doc in purge_list)


# In[22]:


# compteur: int = 0
# erreurs: int = 0
# for id in ids_purge:
#     try:
#         purged, saved, unloaded = webi.set_purge_doc(id)
#         if purged and saved and unloaded:
#             log.info(f"Purge du document ({id}): purge -> {purged} - enregistrement -> {saved} -> déchargement -> {unloaded}")
#             compteur += 1
#         else:
#             log.warning(f"Purge du document ({id}): purge -> {purged} - enregistrement -> {saved} -> déchargement -> {unloaded}")
#             erreurs += 1

#         if compteur % batch_size == 0:
#             log.info(f"** {compteur} documents traités — pause de stabilisation ({sleep} sec)... **")
#             time.sleep(sleep)
#     except Exception as err:
#         log.error(f"Erreur de purge sur le document ({id}): {err}")
#         erreurs += 1
#         continue  # on continue malgré l'erreur
# log.log("")


# In[23]:


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
        # if i % batch_size == 0:
        #     log.info(f"** {i} documents traités — pause ({sleep} sec)... **")
        #     time.sleep(sleep)
        if i % batch_size == 0:
            pause = sleep / workers
            log.info(f"** pause adaptative de {pause:.0f}s **")
            time.sleep(pause)
log.log("")


# In[24]:


# log.info(f"-- nombre d'itérations produites / nombre documents à purger: {compteur}/{len(purge_list)}")
log.info(f"-- documents à purger   : {len(purge_list)}")
log.info(f"-- documents exclus     : {len(excluding_list)}")
log.info(f"-- CUID manquants       : {len(missing_cuid)}")
log.info(f"-- documents traités    : {compteur}")
log.info(f"-- documents en erreur  : {erreurs}")
log.log("")


# ## Deconnexion

# In[25]:


# Deconnexion
log.info("## Deconnexion ##")
bip.unset_token()

