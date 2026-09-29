#!/usr/bin/env python3
"""Join Chinese community pages using unique drop distributions / quest fingerprints.
No positional or similar-name matches. Conflicts are reported, never silently chosen.
"""
import collections,json,re,sqlite3
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];RES=ROOT/'Sources/HunterDex/Resources'; CACHE=ROOT/'.cache/data-sources'
db=sqlite3.connect(RES/'mhgu.db');db.row_factory=sqlite3.Row
base=json.loads((RES/'zh.json').read_text()); existing=json.loads((RES/'localization.json').read_text()); art=json.loads((ROOT/'ARTWORK-SOURCES.json').read_text())['portraits']
monsters=existing['monsters']; page_mon={r['reference'].split('/')[-1]:int(i) for i,r in art.items()}
conditions={'个体剥ぎ取り':'Body Carve','剥ぎ取り':'Body Carve','尾巴剥ぎ取り':'Tail Carve','落与し物':'Shiny','捕获':'Capture','头部破坏':'Break Head','头破坏':'Break Head','翼破坏':'Break Wings','背中破坏':'Break Back','背破坏':'Break Back','角破坏':'Break Horn','尾巴破坏':'Break Tail','爪破坏':'Break Claws','前脚破坏':'Break Forelegs','脚破坏':'Break Legs','耳破坏':'Break Ears','胸破坏':'Break Chest','颚破坏':'Break Jaw','腕破坏':'Break Arms','后脚破坏':'Break Hindlegs','腹破坏':'Break Belly','眼破坏':'Break Eye','牙破坏':'Break Fang','フリー狩猎':None,'クチバシ破坏':'Break Beak','背ビレ破坏':'Break Fin','翼爪破坏':'Break Wingtalon','鬃毛破坏':'Break Mane','胴体破坏':'Break Body','个体采掘':'Body Gather'}
proposals=collections.defaultdict(list); source_quests={}; missing_conditions=collections.Counter()
def chinese(n):return bool(re.search('[\u3400-\u9fff]',n)) and not re.search('[\u3040-\u30ff]',n)
for filename,mid in page_mon.items():
 p=CACHE/'jestar/data'/filename
 if not p.exists():continue
 html=p.read_text();s=BeautifulSoup(html,'html.parser')
 for cls,content in re.findall(r"\$\('\.([^']+)'\)\.html\('([^']*)'\)",html):
  for el in s.select('.'+cls):el.clear();el.append(BeautifulSoup(content,'html.parser'))
 src=collections.defaultdict(list);names={};used=set()
 for table in s.select('table'):
  if '方法 下位 上位' not in table.get_text(' ',strip=True):continue
  for tr in table.select('tr'):
   td=tr.find_all('td',recursive=False)
   if len(td)!=4:continue
   method=re.sub(r'\s*[\d∞]+回.*','',td[0].get_text(' ',strip=True))
   condition=conditions.get(method)
   if not condition:missing_conditions[method]+=1;continue
   used.add(condition)
   for rank,cell in zip(['LR','HR','G'],td[1:]):
    for a in cell.select('a[href*="ida/"]'):
     name=a.get_text(strip=True);url=a['href'].replace('../','');tail=''
     for sibling in a.next_siblings:
      if getattr(sibling,'name',None) in ('a','br'):break
      tail+=sibling.get_text() if hasattr(sibling,'get_text') else str(sibling)
     pct=re.search(r'(\d+)\s*%',tail);qty=re.search(r'[x×]\s*(\d+)',tail)
     if not pct:continue
     names[url]=name;extra=''
     if a.parent.name=='div':
      label=a.parent.find_previous_sibling('span')
      if label and label.get_text(strip=True).startswith('Lv'):
       level=label.get_text(strip=True).replace('～','-')
       level=level.replace('LvG','G').replace('-G','-')
       extra=' '+level
     src[url].append((rank,condition+extra,int(qty.group(1)) if qty else 1,int(pct.group(1))))
 native=collections.defaultdict(list)
 for row in db.execute('select * from hunting_rewards where monster_id=?',(mid,)):
  if any(row['condition']==c or row['condition'].startswith(c+' ') for c in used):native[row['item_id']].append((row['rank'],row['condition'],row['stack_size'],row['percentage']))
 srcsig=collections.defaultdict(list);dbsig=collections.defaultdict(list)
 for url,values in src.items():srcsig[tuple(sorted(values))].append(url)
 for iid,values in native.items():dbsig[tuple(sorted(values))].append(iid)
 for sig,urls in srcsig.items():
  if len(urls)!=1 or len(dbsig[sig])!=1 or not chinese(names[urls[0]]):continue
  proposals[dbsig[sig][0]].append({'name':names[urls[0]],'source':'jestar719/mhgu:app/src/main/assets/mhxx/'+urls[0],'monster_id':mid,'evidence':sig,'method':'unique complete mapped drop-distribution on both sides'})
 # Quest links carry hub/stars, location and all appearing monster page IDs.
 for tr in s.select('tr'):
  td=tr.find_all('td',recursive=False)
  if len(td)!=5:continue
  kind=td[0].get_text(' ',strip=True);kind=re.sub(r'\s+','',kind)
  m=re.fullmatch(r'(村|集)(下|上|G)(\d+)',kind)
  if not m:continue
  title=td[1].select_one('a[href*="ida/"]')
  if not title:continue
  links=td[4].select('a[href*="data/"]');monids=[];unknown=False
  for a in links:
   f=a['href'].split('/')[-1].split('#')[0]
   if f not in page_mon:unknown=True;break
   monids.append(page_mon[f])
  if unknown or not monids:continue
  img=td[1].select_one('img');qtype=img.get('alt','') if img else ''
  source_quests[title['href']]={'name':title.get_text(strip=True),'hub':'Village' if m[1]=='村' else 'Guild','stars':int(m[3])+(10 if m[2]=='G' and m[1]=='集' else 0),'location':td[2].get_text(strip=True),'monsters':sorted(set(monids)),'type':qtype,'source':title['href'].replace('../','')}
items={};evidence={};conflicts={}
for iid,ps in proposals.items():
 names={p['name'] for p in ps}
 if len(names)==1:items[str(iid)]=ps[0]['name'];evidence[str(iid)]=ps
 else:conflicts[str(iid)]=ps
# Site and DB express day/night variants differently; preserve all other location names.
location_names={'Ancestral Steppe':'遗迹平原','Arctic Ridge':'雪山','Arctic Ridge (N)':'雪山（夜）','Arena':'斗技场','Castle Schrade':'修雷德城','Desert':'沙漠','Deserted Island':'孤岛','Dunes':'旧沙漠','Forlorn Arena':'塔之秘境','Fortress':'砦','Frozen Seaway':'冰海','Ingle Isle':'溶岩岛','Jungle':'密林','Jurassic Frontier':'古代林','Jurassic Frontier (N)':'古代林（夜）','Marshlands':'沼地','Misty Peaks':'溪流','Misty Peaks (N)':'溪流（夜）','Polar Field':'极圈','Primal Forest':'原生林','Ruined Pinnacle':'遗群岭','Sacred Pinnacle':'灵峰','Sanctuary':'禁足地','Verdant Hills':'森丘','Verdant Hills (N)':'森丘（夜）','Volcanic Hollow':'地底火山','Volcano':'火山',"Wyvern's End":'龙之墓场'}
locs={r['_id']:location_names.get(r['name'],r['name']) for r in db.execute('select _id,name from locations')}
loc_alias={'极圏':'极圈','シュレイド城':'修雷德城','原生林':'原生林','旧沙漠':'旧沙漠','溪流':'溪流','森丘':'森丘','遗迹平原':'遗迹平原','遗群岭':'遗群岭','古代林':'古代林','禁足地':'禁足地'}
def locnorm(n):
 n=re.sub(r'（.*?）|\(.*?\)','',n).strip();return loc_alias.get(n,n)
def kind(n):
 if n.startswith('Capture'):return '捕获'
 if n.startswith('Deliver') or n.startswith('Survive'):return '采集'
 if n.startswith('Slay'):return '讨伐'
 return '狩猎'
def signature(q):return (q['hub'],q['stars'],locnorm(q['location']),tuple(q['monsters']),q['type'])
lookup=collections.defaultdict(list)
for q in source_quests.values():
 q['type']={'连续狩猎':'狩猎','狩猎':'狩猎','捕获':'捕获','讨伐':'讨伐','采集':'采集'}.get(q['type'],q['type']);lookup[signature(q)].append(q)
qnative=collections.defaultdict(list)
for q in db.execute('select * from quests'):
 mons=[r[0] for r in db.execute('select distinct monster_id from monster_to_quest where quest_id=? order by monster_id',(q['_id'],))]
 sig=(q['hub'],q['stars'],locnorm(locs.get(q['location_id'],'')),tuple(mons),kind(q['goal']))
 qnative[sig].append(dict(q))
quests={};qevidence={}
for sig,source in lookup.items():
 native=qnative[sig]
 if len(source)!=1 or len(native)!=1 or not chinese(source[0]['name']):continue
 q=native[0];quests[str(q['_id'])]=source[0]['name'];qevidence[str(q['_id'])]={'english':q['name'],'source':'jestar719/mhgu:app/src/main/assets/mhxx/'+source[0]['source'],'method':'unique hub/stars/location/all-monsters/objective-type fingerprint','fingerprint':sig}
# Skill effects: match exact Chinese skill-tree name + activation threshold.
c=sqlite3.connect(CACHE/'jestar-mhgu.db');c.row_factory=sqlite3.Row
skilllookup=collections.defaultdict(list)
for r in c.execute('select * from SkillEffect'):skilllookup[(r['skillName'],r['value'])].append(dict(r))
effects={};effectdescs={}
for r in db.execute('select s.*,t.name as tree_name from skills s join skill_trees t on t._id=s.skill_tree_id'):
 name=base['skill_trees'].get(r['tree_name'],r['tree_name']);match=skilllookup[(name,r['required_skill_tree_points'])]
 if len(match)==1:effects[r['name']]=match[0]['name'];effectdescs[r['name']]=match[0]['effect']
result={'items_by_id':items,'quests_by_id':quests,'skill_effects':effects,'skill_descriptions':effectdescs,'elements':{'Blastblight':'爆破'},'hubs':{'Permit':'特殊许可'},'locations':location_names}
(RES/'linked-localization.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(ROOT/'LINKED-LOCALIZATION-SOURCES.json').write_text(json.dumps({'items':evidence,'quests':qevidence,'conflicts':conflicts,'skill_effect_method':'exact Chinese skill-tree name + threshold in jestar SkillEffect','counts':{'items':len(items),'quests':len(quests),'skill_effects':len(effects)}},ensure_ascii=False,indent=2)+'\n')
print('Items',len(items),'quests',len(quests),'skills',len(effects),'conflicts',len(conflicts),'source quests',len(source_quests))
print('sample items',list(items.items())[:8]);print('sample quests',list(quests.items())[:8])
print('source locations',sorted(set(q['location'] for q in source_quests.values())))
print('database locations',locs)
