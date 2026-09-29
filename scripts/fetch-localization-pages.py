#!/usr/bin/env python3
from pathlib import Path
import sqlite3,concurrent.futures,subprocess,json
ROOT=Path(__file__).resolve().parents[1];cache=ROOT/'.cache/data-sources';db=sqlite3.connect(cache/'jestar-mhgu.db')
paths=[r[0] for r in db.execute('select distinct url from IndexBean where type in (3,6,7,8) and url is not null')]
base='https://cdn.jsdelivr.net/gh/jestar719/mhgu@master/app/src/main/assets/mhxx/'
def fetch(path):
 out=cache/'jestar'/path
 if out.exists():return ('cached',path)
 out.parent.mkdir(parents=True,exist_ok=True)
 result=subprocess.run(['curl','-fsSL','--max-time','25','--retry','1',base+path],capture_output=True)
 if result.returncode==0 and b'<html' in result.stdout.lower():out.write_bytes(result.stdout);return ('ok',path)
 return ('failed',path)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 for status,path in pool.map(fetch,paths):
  if status!='cached':print(status,path,flush=True)
