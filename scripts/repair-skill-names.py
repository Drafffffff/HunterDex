#!/usr/bin/env python3
"""Derive skill names from independently matched armor names + exact point contributions.
Run after review-localization.py. Keep unmatched trees in English instead of legacy guesses.
"""
import sqlite3,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/name).read_text())
a=sqlite3.connect(ROOT/'Sources/HunterDex/Resources/mhgu.db');a.row_factory=sqlite3.Row
b=sqlite3.connect(ROOT/'.cache/data-sources/jestar-mhgu.db');b.row_factory=sqlite3.Row
names=read('Sources/HunterDex/Resources/localization.json')['items_by_id']
cn=collections.defaultdict(list)
for r in b.execute('select * from Equip'):cn[r['name']].append(r)
points=collections.defaultdict(list)
for r in b.execute('select * from EquipSkill'):points[r['equipId']].append(r)
evidence=collections.defaultdict(list)
for r in a.execute('select x.*, t.name tree from item_to_skill_tree x join skill_trees t on t._id=x.skill_tree_id join armor ar on ar._id=x.item_id'):
 candidates=cn.get(names.get(str(r['item_id']),''),[])
 if len(candidates)!=1:continue
 possible={x['name'] for x in points[candidates[0]['id']] if x['value']==r['point_value']}
 if possible:evidence[r['tree']].append((r['item_id'],possible))
fixed={};audit={}
for tree,rows in evidence.items():
 possible=set.intersection(*(x[1] for x in rows))
 if len(possible)==1 and len(rows)>=2:
  fixed[tree]=next(iter(possible));audit[tree]={'chinese':fixed[tree],'armor_ids':[x[0] for x in rows],'method':'intersection of exact point contributions across uniquely named, independently matched armor'}
# Reviewed against native English skill descriptions and the Chinese SkillEffect descriptions.
manual={'KO':'击晕','Sleep': '睡眠', 'Stun': '昏厥', 'Bladescale': '刃鳞', 'Normal S+': '通常弹追加', 'Pierce S+': '贯通弹追加', 'Pellet S+': '散弹追加', 'Crag S+': '榴弹追加', 'Clust S+': '扩散弹追加', 'Poison C+': '毒瓶追加', 'Para C+': '麻痹瓶追加', 'Sleep C+': '睡眠瓶追加', 'Elem C+': '属强瓶追加', 'C.Range C+': '接击瓶追加', 'Exhaust C+': '减气瓶追加', 'Blast C+': '爆破瓶追加', 'Expert': '达人', 'Destroyer': '重击', 'Team Player': '指挥', 'TeamLeader': '号令', 'Psychic': '千里眼', 'Perception': '观察眼', 'Rec Level': '回复量', 'Wide-Range': '广域', 'Eating': '进食', 'Bherna': '贝鲁纳', 'Kokoto': '可可特', 'Pokke': '波凯', 'Yukumo': '结云', 'Soaratorium': '龙识船', 'Flying Pub': '飞行酒吧', 'Prayer': '祈愿', 'Readiness': '居合', 'Resilience': '顽强', 'Stalwart': '持盾', 'Avarice': '强欲', 'Anti-Chameleos': '对霞龙', 'Anti-Teostra': '对炎龙', 'Redhelm': '红盔', 'Redhelm X': '真・红盔', 'Snowbaron': '大雪主', 'Snowbaron X': '真・大雪主', 'Stonefist': '矛碎', 'Stonefist X': '真・矛碎', 'Drilltusk': '岩穿', 'Drilltusk X': '真・岩穿', 'Dreadqueen': '紫毒姫', 'Dreadqueen X': '真・紫毒姫', 'C.beard': '宝缠', 'Crystalbeard X': '真・宝缠', 'Silverwind': '白疾风', 'Silverwind X': '真・白疾风', 'Deadeye': '独眼', 'Deadeye X': '真・独眼', 'Dreadking': '黑炎王', 'Dreadking X': '真・黑炎王', 'Hellblade': '烬灭刃', 'Hellblade X': '真・烬灭刃', 'Nightcloak': '胧隐', 'Nightcloak X': '真・胧隐', 'Rustrazor': '铠裂', 'Rustrazor X': '真・铠裂', 'Soulseer': '天眼', 'Soulseer X': '真・天眼', 'Boltreaver': '青电主', 'Boltreaver X': '真・青电主', 'Elderfrost': '银峰', 'Elderfrost X': '真・银峰', 'Bloodbath': '鏖魔', 'Bloodbath X': '真・鏖魔'}
for tree,name in manual.items():
 fixed[tree]=name
 audit[tree]={"chinese":name,"method":"project review of MHGenDatabase effect description against jestar SkillEffect; deviant identity and X variant explicitly resolved"}
legacy=read('Sources/HunterDex/Resources/zh.json')['skill_trees']
alltrees=[r['name'] for r in a.execute('select name from skill_trees')]
# Unmapped names deliberately retain English; their threshold data remains usable.
translations={k:fixed.get(k,k) for k in alltrees}
print('Verified',len(fixed),'/',len(alltrees))
print('Changed',[(k,legacy.get(k),v) for k,v in fixed.items() if legacy.get(k)!=v])
print('Unmatched',[x for x in alltrees if x not in fixed])
effects={};descriptions={}
lookup=collections.defaultdict(list)
for r in b.execute('select * from SkillEffect'):lookup[(r['skillName'],r['value'])].append(r)
source_tree_names={'击晕':'KO'}
for r in a.execute('select s.*, t.name tree from skills s join skill_trees t on t._id=s.skill_tree_id'):
 matches=lookup[(source_tree_names.get(translations[r['tree']],translations[r['tree']]),r['required_skill_tree_points'])]
 effects[r['name']]=matches[0]['name'] if len(matches)==1 else r['name']
 if len(matches)==1:descriptions[r['name']]=matches[0]['effect']
p=ROOT/'Sources/HunterDex/Resources/linked-localization.json';out=json.loads(p.read_text());out.update(skill_trees=translations,skill_effects=effects,skill_descriptions=descriptions);p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(ROOT/'SKILL-LOCALIZATION-SOURCES.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
