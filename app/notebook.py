#!/usr/bin/env python
# coding: utf-8

# In[8]:


APPLICATION_NAME = "Notebook"


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


# ## Methods and functions from class: AppEnv

# In[ ]:


print(epy.appenv.get_current_date())
print(epy.appenv.get_hostname())


# In[ ]:


print(epy.appenv.get_system())


# ## Using your own class (outside of bootstrap)

# In[12]:


cls = epy.load_class(module_name='my_dummy_class', args=[epy, APPLICATION_NAME])


# In[ ]:


cls.dummy_function()


# In[ ]:


cls.app_name

