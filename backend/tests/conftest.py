import os
import tempfile
os.environ['DATA_DIR']=tempfile.mkdtemp(prefix='ew-tests-')
os.environ['DATABASE_URL']=''
os.environ['OLLAMA_CACHE']='false'
