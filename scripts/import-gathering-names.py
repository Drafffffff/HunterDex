#!/usr/bin/env python3
"""Match item names by unique per-area harvesting distributions in both databases."""
import json,sqlite3,re,collections
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];RES=ROOT/'Sources/HunterDex/Resources';CACHE=ROOT/'.cache/data-sources'
db=sqlite3.connect(RES/'mhgu.db');db.row_factory=sqlite3.Row
out=json.loads((RES/'linked-localization.json').read_text());evidence=json.loads((ROOT/'LINKED-LOCALIZATION-SOURCES.json').read_text())
source=sqlite3.connect(CACHE/'jestar-mhgu.db')
locs={v:r['_id'] for r in db.execute('select _id,name from locations') if (v:=out['locations'].get(r['name']))}
proposals=collections.defaultdict(list)
for name,url in source.execute('select name,url from IndexBean where type=7 and url is not null'):
 if name not in locs:continue
 p=CACHE/'jestar'/url
 if not p.exists():continue
 s=BeautifulSoup(p.read_text(),'html.parser');loc=locs[name];groups=collections.defaultdict(lambda:collections.defaultdict(list));names={}
 for table in s.select('table'):
  heading=table.find_previous('h3');rank=table.find_previous('h4')
  if not heading or not rank:continue
  area=heading.get_text(strip=True).replace('区域','Area ')
  if area=='Area 秘境':area='Secret'
  if not (area.startswith('Area ') or area=='Secret'):continue
  rank={'下位':'LR','上位':'HR','G级':'G'}.get(rank.get_text(strip=True))
  if not rank:continue
  for tr in table.select('tr'):
   cells=tr.find_all('td',recursive=False)
   if len(cells)<2:continue
   a=cells[-2].select_one('a[href*="ida/"]')
   if not a:continue
   pct=re.search(r'(\d+)%',cells[-1].get_text());qty=re.search(r'[x×]\s*(\d+)',cells[-2].get_text())
   if not pct:continue
   itemurl=a['href'];names[itemurl]=a.get_text(strip=True)
   groups[(rank,area)][itemurl].append((int(qty[1]) if qty else 1,int(pct[1])))
 for (rank,area),items in groups.items():
  native=collections.defaultdict(list)
  for r in db.execute('select * from gathering where location_id=? and rank=? and area=?',(loc,rank,area)):native[r['item_id']].append((r['quantity'],r['percentage']))
  sr=collections.defaultdict(list);nr=collections.defaultdict(list)
  for key,v in items.items():sr[tuple(sorted(v))].append(key)
  for key,v in native.items():nr[tuple(sorted(v))].append(key)
  for sig,keys in sr.items():
   if len(keys)!=1 or len(nr[sig])!=1 or len(sig)<2:continue
   cn=names[keys[0]]
   if re.search('[\u3040-\u30ff]',cn) or not re.search('[\u3400-\u9fff]',cn):continue
   proposals[nr[sig][0]].append({'name':cn,'source':'jestar719/mhgu:app/src/main/assets/mhxx/'+keys[0].replace('../',''),'method':'unique per-area complete quantity/probability distribution, >=2 observations','location':name,'rank':rank,'area':area,'evidence':sig})
count=0
for iid,ps in proposals.items():
 if len(set(p['name'] for p in ps))!=1:continue
 key=str(iid)
 if key in out['items_by_id'] and out['items_by_id'][key]!=ps[0]['name']:continue
 out['items_by_id'][key]=ps[0]['name'];evidence['items'].setdefault(key,[]).extend(ps);count+=1
(RES/'linked-localization.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');(ROOT/'LINKED-LOCALIZATION-SOURCES.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
print('Gathering mappings',count)
print([(r['name'],out['items_by_id'].get(str(r['_id']))) for r in db.execute("select _id,name from items where name in ('Silverfish','Water Lily Root','Powderstone','Sootstone Ore','Gold Gargwa Egg','Secret Stash','Fossilized Bone')")])
