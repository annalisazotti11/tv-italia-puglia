import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('--check-only',action='store_true')
args=p.parse_args()
if sys.version_info[:2] not in {(3,10),(3,11),(3,12)}:
    print('Usa Python 3.12: https://www.python.org/downloads/windows/')
    raise SystemExit(2)
if args.check_only:
    print('Python compatibile. Non aperti file video e non installato nulla.')
    raise SystemExit(0)
env=root/'.venv-analisi'
python=env/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
ready=python.is_file() and subprocess.run([str(python),'-c','from PIL import Image; from nudenet import NudeDetector'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
if not ready:
    print('Pillow e NudeNet verranno installati in una cartella locale, senza privilegi amministrativi.')
    if input('Autorizzi l’installazione da PyPI? [s/N] ').strip().lower() not in {'s','si','sì'}:
        raise SystemExit(1)
    if not python.is_file():
        subprocess.run([sys.executable,'-m','venv',str(env)],check=True)
    subprocess.run([str(python),'-m','pip','install','--requirement',str(root/'requirements.txt')],check=True)
out=root/'reports'/f"campione-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
subprocess.run([str(python), str(root/'local_content_compare.py'),'--output',str(out)],check=True)
print('Invia il file JSON a ChatGPT per interpretare il risultato. Nessun media è stato salvato nel report.')
