#!/usr/bin/env python3
from pathlib import Path
import sqlite3,concurrent.futures,subprocess,json
import re
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];cache=ROOT/'.cache/data-sources';db=sqlite3.connect(cache/'jestar-mhgu.db')
# Include weapon category, weapon-tree, and final-upgrade pages. These carry
# the Chinese names and complete ordered weapon statistics used by the
# conservative exact-signature and upgrade-chain importers.
paths=[r[0] for r in db.execute('select distinct url from IndexBean where type in (1,3,4,6,7,8) and url is not null')]
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

# Item index/detail pages contain Chinese names and rarity/carry/sale data.
# Fetch linked records to support conservative, stat-based matching.
item_indexes=['data/2100.html','data/2112.html','data/2113.html','data/2114.html',
              'data/2115.html','data/2116.html','data/2118.html','data/2119.html',
              'data/2984.html','data/2985.html']
detail_paths=set()
quest_indexes=[r[0] for r in db.execute('select distinct url from IndexBean where type=8 and url is not null')]
for relative in sorted(set(item_indexes+quest_indexes)):
 page=cache/'jestar'/relative
 if not page.exists():continue
 soup=BeautifulSoup(page.read_text(),'html.parser')
 for anchor in soup.select('a[href*="ida/"]'):
  match=re.search(r'(?:^|/)ida/(\d+)\.html(?:$|[#?])',anchor.get('href',''))
  if match:detail_paths.add(f'ida/{match[1]}.html')
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 for status,path in pool.map(fetch,sorted(detail_paths)):
  if status!='cached':print(status,path,flush=True)
print('linked detail pages',len(detail_paths),flush=True)
