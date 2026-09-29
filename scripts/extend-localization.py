#!/usr/bin/env python3
"""Extend linked names with attested terminology and explicit project translations.
Run after import-linked-localization.py. Original English remains searchable.
"""
import sqlite3,json,re,collections,unicodedata,importlib.util,argparse
from pathlib import Path
from bs4 import BeautifulSoup
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--goal-translator', required=True, type=Path, help='External build_zh.py providing GOAL_ALIASES, GOAL_ITEMS and synth_goals')
args=parser.parse_args()
if not args.goal_translator.is_file():
 parser.error('The supplied goal translator file does not exist')
ROOT=Path(__file__).resolve().parents[1];RES=ROOT/'Sources/HunterDex/Resources';CACHE=ROOT/'.cache/data-sources'
db=sqlite3.connect(RES/'mhgu.db');db.row_factory=sqlite3.Row
out=json.loads((RES/'linked-localization.json').read_text());base=json.loads((RES/'zh.json').read_text());old=json.loads((RES/'localization.json').read_text());provenance=json.loads((ROOT/'LINKED-LOCALIZATION-SOURCES.json').read_text())
monsters=old['monsters'];names=dict(monsters)
deviants={'Redhelm':'红盔','Snowbaron':'大雪主','Stonefist':'矛碎','Dreadqueen':'紫毒姬','Drilltusk':'岩穿','Silverwind':'白疾风','Crystalbeard':'宝缠','Deadeye':'独眼','Dreadking':'黑炎王','Thunderlord':'金雷公','Grimclaw':'荒钩爪','Hellblade':'烬灭刃','Nightcloak':'胧隐','Rustrazor':'铠裂','Boltreaver':'青电主','Soulseer':'天眼','Elderfrost':'银峰','Bloodbath':'鏖魔'}
names.update(deviants);names.update({'Monster':'怪物','Ore':'矿石','Insect':'昆虫','Bone':'骨','Hyper':'狞猛化','Deviant':'二名','Herbivore':'草食种','Neopteron':'甲虫种','Bird Wyvern':'鸟龙种','Rath':'火龙','Rath (Rare)':'火龙稀少种','Rathian (Any)':'雌火龙系','Rathalos (Any)':'雄火龙系','S.Rathalos':'银火龙','S. Magala':'天廻龙','Kushala':'钢龙','Fatalis (Crimson)':'红龙','Fatalis (Old)':'祖龙'})
for row in db.execute("select _id,name from items where type='Materials'"):
 m=re.fullmatch(r'(LR|HR|G) (.*) Materials',row['name'])
 if m and m[2] in names:
  out['items_by_id'][str(row['_id'])]={'LR':'下位','HR':'上位','G':'G位'}[m[1]]+'·'+names[m[2]]+'素材'
  provenance['items'][str(row['_id'])]=[{'name':out['items_by_id'][str(row['_id'])],'method':'project translation of rank + verified entity + material category','english':row['name']}]
for row in db.execute("select * from quests where hub='Permit'"):
 m=re.fullmatch(r'([A-Za-z]+) ([IVX]+|G[1-5]|EX): (Hunt|Capture)',row['name'])
 if m and m[1] in deviants:
  out['quests_by_id'][str(row['_id'])]='特殊许可·'+deviants[m[1]]+' '+m[2]+'：'+{'Hunt':'狩猎','Capture':'捕获'}[m[3]]
  provenance['quests'][str(row['_id'])]={'method':'project translation of explicit deviant/level/action title','english':row['name']}
# Attested source names; normalization only, no unattested suffix combinations accepted.
def norm(s):return unicodedata.normalize('NFKC',s).replace('姫','姬')
index=BeautifulSoup((CACHE/'jestar/data/2100.html').read_text(),'html.parser')
attested={norm(a.get_text(strip=True)):a['href'].replace('../','') for a in index.select('table a[href*="ida/"]')}
prefix=dict(names);prefix.update({'Rathalos':'火龙','Khezu':'白电','Basarios':'岩龙','Kut-Ku':'怪鸟','Garuga':'黑狼鸟','Kecha':'奇猿狐','R.Ludroth':'水兽','Tetsu.':'鬼蛙','S.Queen':'重甲虫','Brach':'碎龙','Duram':'尾锤龙','Narga':'迅龙','S.Magala':'天廻龙','Daora':'钢龙','G.Rathian':'金火龙','C.Fatalis':'红龙','Lao-Shan':'老山龙','Hermitaur':'盾蟹','Ceanataur':'镰蟹','Rathian':'雌火龙'})
# Use the community's material prefix when it differs from its monster's common name.
arts=json.loads((ROOT/'ARTWORK-SOURCES.json').read_text())['portraits']
for mid,record in arts.items():
 p=CACHE/'jestar/data'/record['reference'].split('/')[-1]
 if not p.exists():continue
 s=BeautifulSoup(p.read_text(),'html.parser');t=s.select_one('table')
 if t:
  text=t.get_text(' ',strip=True);m=re.search(r'素材名\s+(\S+)',text)
  if m and not re.search('[\u3040-\u30ff]',m[1]):prefix[record['english']]=norm(m[1])
suffix={'Scale':'鱗','Scale+':'上鱗','Shard':'厚鱗','Shell':'甲壳','Carapace':'坚壳','Cortex':'重壳','Crtx':'重壳','Claw':'爪','Claw+':'尖爪','Hardclaw':'刚爪','Tail':'尾巴','Lash':'靭尾','Marrow':'骨髄','Medulla':'延髄','Plate':'逆鱗','Ruby':'红玉','Mantle':'天鱗','Pallium':'天壳','Gem':'宝玉','Hide':'皮','Hide+':'上皮','Piel':'厚皮','Wing':'翼','Fellwing':'刚翼','Horn':'角','Horn+':'尖角','Hardhorn':'刚角','Pelt':'毛','Pelt+':'刚毛','Fur':'豪刚毛','Scalp':'头壳','Scrap':'端材','Scrap+':'上端材','Scrap G':'重端材','Hardfang':'重牙','Fang':'牙','Fang+':'锐牙','Hvy Fang':'重牙','Fin':'鳍','Fin+':'上鳍','Grandfin':'特上鳍','Webbing':'翼膜','Crest':'鸡冠','Comb':'冠','Talons':'翼爪','Talon':'翼爪','Hardbone':'坚骨','Hvy Bone':'重骨'}
for row in db.execute("select _id,name from items where type=''"):
 iid=str(row['_id']);en=row['name']
 if iid in out['items_by_id']:continue
 matches=[]
 for p,cn in sorted(prefix.items(),key=lambda v:-len(v[0])):
  if en.startswith(p+' '):
   suf=suffix.get(en[len(p)+1:])
   if suf:
    candidates=[cn+'的'+suf,cn+suf]
    matches += [n for n in candidates if n in attested]
  if en.startswith('Hyper '+p+' '):
   suf=suffix.get(en[len(p)+7:])
   if suf:
    matches += [n for n in ['狞猛化'+cn+'的'+suf,'狞猛化'+cn+suf] if n in attested]
 if len(set(matches))==1:
  n=matches[0];out['items_by_id'][iid]=n;provenance['items'][iid]=[{'name':n,'method':'reviewed prefix/suffix + exact attestation','source':'jestar719/mhgu:app/src/main/assets/mhxx/'+attested[n],'english':en}]
# Common consumables: use source wording, verify each full name appears in the Chinese item index.
common={'Mega Dash Juice':'强走药G','Dash Juice':'强走药','Demondrug':'鬼人药','Mega Demondrug':'鬼人药G','Armorskin':'硬化药','Mega Armorskin':'硬化药G','Nutrients':'营养剂','Mega Nutrients':'营养剂G','Might Seed':'怪力之种','Adamant Seed':'忍耐之种','Might Pill':'怪力药丸','Adamant Pill':'忍耐药丸','Immunizer':'活力剂','Catalyst':'增强剂','Energy Drink':'元气饮料','Cleanser':'消散剂','Deodorant':'消臭玉','Tranq Bomb':'捕获用麻醉玉','Tranq':'捕获用麻醉药','Smoke Bomb':'烟雾玉','Poison Smoke Bomb':'毒烟雾玉','Farcaster':'回家玉','Dung':'怪物的粪','Drugged Meat':'睡眠生肉','Tinged Meat':'麻痹生肉','Poisoned Meat':'毒生肉','Barrel Bomb S':'小桶爆弹','Barrel Bomb S+':'小桶爆弹G','Barrel Bomb L':'大桶爆弹','Barrel Bomb L+':'大桶爆弹G','Nitroshroom':'爆炸菇','Parashroom':'麻痹菇','Toadstool':'毒菇','Mopeshroom':'心跳加速蘑菇','Exciteshroom':'兴奋蘑菇','Dragon Toadstool':'曼陀罗','Paintberry':'染色果','Scatternut':'爆裂核桃','Needleberry':'针果','Huskberry':'空心果','Latchberry':'贯通果','Bomberry':'扩散果','Bom Arowana':'爆裂龙鱼','Bomb Arowana':'爆裂龙鱼','Burst Arowana':'破裂龙鱼','Gloamgrass Root':'落阳草之根','Fire Herb':'火药草','Sleep Herb':'睡眠草','Antidote Herb':'解毒草','Ivy':'常春藤叶','Sap Plant':'粘着草','Felvine':'木天蓼','Nulberry':'抵消果实','Flashbug':'光虫','Carpenterbug':'粘着白蚁','Fulgurbug':'超电雷光虫','Bnahabra Shell':'飞甲虫的甲壳','Spider Web':'蜘蛛的巢'}
for en,cn in common.items():
 if cn not in attested:continue
 for r in db.execute("select _id from items where name=? and type=''",(en,)):
  out['items_by_id'][str(r['_id'])]=cn;provenance['items'][str(r['_id'])]=[{'name':cn,'method':'reviewed common terminology + exact attestation','source':'jestar719/mhgu:app/src/main/assets/mhxx/'+attested[cn],'english':en}]
# Translate structured main and sub-goals with corrected monster and material names.
spec=importlib.util.spec_from_file_location('skill_zh',args.goal_translator);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.GOAL_ALIASES.update({'R.Ludroth':'水兽','Daimyo':'大名盾蟹','Shogun':'将军镰蟹'})
item_names={r['name']:out['items_by_id'].get(str(r['_id']),old.get('items_by_id',{}).get(str(r['_id']),base.get('items',{}).get(r['name'],r['name']))) for r in db.execute("select _id,name from items where type='' ")}
for en,cn in item_names.items():
 if cn!=en:
  module.GOAL_ITEMS[en]=cn;module.GOAL_ITEMS[en+'s']=cn
module.GOAL_ITEMS.update({'Kelbi Horns':'羚鹿的角','Great Maccao Heads':'跳狗龙王的头','Tetsucabra Heads':'鬼蛙的头','Seltas Pelvis':'彻甲虫的腹部','Congalala Anuses':'桃毛兽王的臀部','Brocadefish':'锦鱼','Rhenoplos':'草食龙'})
temp=sqlite3.connect(':memory:');temp.execute('create table quests(goal text)')
allgoals=[r[0] for r in db.execute("select goal from quests union select sub_goal from quests where sub_goal is not null and sub_goal!=''")]
temp.executemany('insert into quests values(?)',[(v,) for v in allgoals]);goals=module.synth_goals(temp,monsters)
out['goals']=goals
out['conditions']={'Break Forelegs':'破坏前脚','Break Hindlegs':'破坏后脚','Break Tail':'破坏尾巴','Break Wings':'破坏翅膀','Break Back':'破坏背部','Break Head':'破坏头部','Break Horn':'破坏角','Break Claws':'破坏爪','Break Body':'破坏躯干','Break Chest':'破坏胸部','Break Beak':'破坏喙','Break Fin':'破坏鳍','Break Wingtalon':'破坏翼爪','Break Ears':'破坏耳朵','Break Mane':'破坏鬃毛','Break Eye':'破坏眼部','Body Carve':'本体剥取','Tail Carve':'尾巴剥取','Shiny':'掉落物','Capture':'捕获','Meowster Hunter':'随从探险','Mining':'采矿','Body Gather':'本体采集'}
(RES/'linked-localization.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(ROOT/'LINKED-LOCALIZATION-SOURCES.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
merged={**base.get('items',{})};idmap={**old['items_by_id'],**out['items_by_id']}
coverage={};missing=[]
for r in db.execute('select _id,name,type from items'):
 n=idmap.get(str(r['_id']),merged.get(r['name'],r['name']));kind=r['type'] or 'Item';coverage.setdefault(kind,[0,0]);coverage[kind][1]+=1
 if re.search('[\u3400-\u9fff]',n):coverage[kind][0]+=1
 elif kind in ['Item','Materials']:missing.append({'id':r['_id'],'english':r['name'],'type':kind})
qcount=0;qmissing=[]
for r in db.execute('select _id,name from quests'):
 n=out['quests_by_id'].get(str(r['_id']),base['quests'].get(r['name'],r['name']))
 if re.search('[\u3400-\u9fff]',n):qcount+=1
 else:qmissing.append({'id':r['_id'],'english':r['name']})
coverage['Quests']=[qcount,1355]
(ROOT/'LOCALIZATION-COVERAGE.json').write_text(json.dumps({'coverage':coverage,'untranslated_items':missing,'untranslated_quests':qmissing},ensure_ascii=False,indent=2)+'\n')
print(coverage)
print('Goal text with latin remaining:',[(k,v) for k,v in goals.items() if re.search('[a-zA-Z]{3,}',v)][:25])
