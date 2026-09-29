#!/usr/bin/env python3
import collections,concurrent.futures,json,sqlite3,urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'.cache/data-sources';RES=ROOT/'Sources/HunterDex/Resources'
cn=sqlite3.connect(CACHE/'jestar-mhgu.db');db=sqlite3.connect(RES/'mhgu.db')
names=json.loads((ROOT/'scripts/monster-names.json').read_text())
# Wiki spelling aliases, not aliases between different species.
aliases={'紫毒姬雌火龙':'紫毒姫雌火龙','天彗龙':'天慧龙'}
lookup=collections.defaultdict(list)
for name,path in cn.execute('SELECT name,url FROM IndexBean WHERE type=6 AND url IS NOT NULL'):lookup[name].append(path)
monsterlinks=[]
for mid,en,jp in db.execute('SELECT _id,name,name_ja FROM monsters'):
 title=aliases.get(names[en],names[en]); paths=lookup[title]
 if len(paths)==1:monsterlinks.append((mid,en,paths[0]))
def fetch(url,path):
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():return path.read_bytes()
 for attempt in range(3):
  try:data=urllib.request.urlopen(url,timeout=25).read();path.write_bytes(data);return data
  except Exception:
   if attempt==2:raise

def work(record):
 mid,en,path=record
 try:
  html=fetch('https://raw.githubusercontent.com/jestar719/mhgu/master/app/src/main/assets/mhxx/'+path,CACHE/'jestar'/path)
  soup=BeautifulSoup(html,'html.parser'); img=soup.select_one('img[src*="images/monster/"]')
  if not img:return None
  relative=img['src'].replace('../','')
  name='portrait_'+str(mid)+'.png'
  fetch('https://raw.githubusercontent.com/AngryChocobo/monster-hunter-web-data/master/'+relative,RES/'Artwork'/name)
  return str(mid),{'file':name,'source':f'https://github.com/AngryChocobo/monster-hunter-web-data/blob/master/{relative}','reference':'https://github.com/jestar719/mhgu/blob/master/app/src/main/assets/mhxx/'+path,'english':en}
 except Exception as e:return str(mid),{'error':str(e)}
manifest={}
with concurrent.futures.ThreadPoolExecutor(8) as pool:
 for i,res in enumerate(pool.map(work,monsterlinks)):
  if res:manifest[res[0]]=res[1]
  if i%15==0:print('Portraits processed',i,flush=True)
(RES/'artwork.json').write_text(json.dumps({'portraits':{k:v['file'] for k,v in manifest.items() if 'file' in v}},ensure_ascii=False,indent=2)+'\n')
(ROOT/'ARTWORK-SOURCES.json').write_text(json.dumps({'icons':'https://github.com/gatheringhallstudios/MHGenDatabase/tree/develop/app/src/main/icon-res/drawable','portraits':manifest},ensure_ascii=False,indent=2)+'\n')
print('Portrait coverage:',len([v for v in manifest.values() if 'file' in v]),flush=True)
