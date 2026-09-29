#!/usr/bin/env python3
"""Project-reviewed functional terminology, kept distinct from upstream translations."""
from pathlib import Path
import sqlite3,json,re
ROOT=Path(__file__).resolve().parents[1];RES=ROOT/'Sources/HunterDex/Resources'
db=sqlite3.connect(RES/'mhgu.db');db.row_factory=sqlite3.Row
out=json.loads((RES/'linked-localization.json').read_text());provenance=json.loads((ROOT/'LINKED-LOCALIZATION-SOURCES.json').read_text());old=json.loads((RES/'localization.json').read_text());base=json.loads((RES/'zh.json').read_text())
common={'Organizer Guide':'收纳上手·技之书','Pack Rat Guide':'收纳上手·力之书','Mega Dash Juice':'强走药G','Might Pill':'怪力药丸','Adamant Pill':'忍耐药丸','Cleanser':'消散剂','Psychoserum':'千里眼药','Herbal Medicine':'汉方药','Energy Drink':'元气饮料','Lifepowder':'生命粉尘','Dust of Life':'生命大粉尘',"Hunter's Drink":'狩技饮料','Gunpowder':'火药','Lifecrystals':'生命之粉','Tranquilizer':'捕获用麻醉药','Yukumo Egg':'结云温泉蛋','Tanzia Chips':'坦吉亚薯片','Powercharm':'力之护符','Powertalon':'力之爪','Armorcharm':'守之护符','Armortalon':'守之爪','BBQ Spit':'烤肉架','Rare Steak':'半生肉','Burnt Meat':'焦肉','Chilled Meat':'冷肉','Hot Meat':'热肉','Mosswine Jerky':'蘑菇猪肉干','Old Pickaxe':'破铁镐','Iron Pickaxe':'铁镐','Mega Pickaxe':'铁镐G','Old Bug Net':'破虫网','Bug Net':'虫网','Mega Bug Net':'虫网G','Poison Knife':'毒投掷小刀','Sleep Knife':'睡眠投掷小刀','Paralysis Knife':'麻痹投掷小刀','Tranq Knife':'捕获用麻醉小刀','Bomb Casing':'素材玉','Tranq Bomb':'捕获用麻醉玉','Farcaster':'回家玉','Barrel Lid':'桶盖','Small Barrel':'小桶','Large Barrel':'大桶','Barrel Bomb S':'小桶爆弹','Barrel Bomb L':'大桶爆弹','Barrel Bomb L+':'大桶爆弹G','Bounce Bomb':'飞空爆弹','Bounce Bomb+':'飞空爆弹G','Affinity Oil':'会心刃药','Destroyer Oil':'重击刃药','Stamina Oil':'减气刃药',"Mind's Eye Oil":'心眼刃药','Bone Husk':'空心骨','Empty Phial':'空瓶','Gold Gargwa Egg':'丸鸟的金蛋','Gargwa Guano':'丸鸟的粪','Khezu Whelp':'白电龙幼体','Powderstone':'火药岩','Sootstone Ore':'燃石炭','Fossilized Bone':'化石骨','Water Lily Root':'深睡莲的根','Secret Stash':'秘密口袋','Secret Stashes':'秘密口袋','Silverfish':'白金鱼','Auristone Piece':'黄金石碎片','Silver Cricket':'银色蟋蟀'}
ammo={'Normal':'通常弹','Pierce':'贯通弹','Pellet':'散弹','Crag':'彻甲榴弹','Clust':'扩散弹','Flaming':'火炎弹','Water':'水冷弹','Thunder':'电击弹','Freeze':'冰结弹','Dragon':'灭龙弹','Poison':'毒弹','Para':'麻痹弹','Sleep':'睡眠弹','Exhaust':'减气弹','Recover':'回复弹','Paint':'染色弹','Tranq':'捕获用麻醉弹'}
coats={'Power':'强击瓶','Elem':'属性强化瓶','C.Range':'接击瓶','Poison':'毒瓶','Para':'麻痹瓶','Sleep':'睡眠瓶','Exhaust':'减气瓶','Blast':'爆破瓶','Paint':'染色瓶','Alchemy':'炼金瓶'}
deviants={'Redhelm':'红盔','Snowbaron':'大雪主','Stonefist':'矛碎','Dreadqueen':'紫毒姬','Drilltusk':'岩穿','Silverwind':'白疾风','Crystalbeard':'宝缠','Deadeye':'独眼','Dreadking':'黑炎王','Thunderlord':'金雷公','Grimclaw':'荒钩爪','Hellblade':'烬灭刃','Nightcloak':'胧隐','Rustrazor':'铠裂','Boltreaver':'青电主','Soulseer':'天眼','Elderfrost':'银岭','Bloodbath':'鏖魔'}
romans=['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII','XIII','XIV','XV']
for r in db.execute("select _id,name from items where type=''"):
 n=common.get(r['name']);m=re.fullmatch(r'(.*) S(?: Lv(\d+))?',r['name'])
 if not n and m and m[1] in ammo:n=ammo[m[1]]+(f' Lv.{m[2]}' if m[2] else '')
 m=re.fullmatch(r'(.*) Coating(?: Lv(\d+))?',r['name'])
 if not n and m and m[1] in coats:n=coats[m[1]]+(f' Lv.{m[2]}' if m[2] else '')
 m=re.fullmatch(r'(.*) Hunter ([IVX]+)',r['name'])
 if not n and m and m[1] in deviants and m[2] in romans:n=deviants[m[1]]+'狩猎之证'+str(romans.index(m[2])+1)
 if n:
  out['items_by_id'][str(r['_id'])]=n;provenance['items'][str(r['_id'])]=[{'name':n,'english':r['name'],'method':'project-reviewed functional terminology / explicit level, community terminology; not an official localization'}]
# Body-part goals are translated from their complete English structure, not fragments.
mon={**old['monsters'],'S.Magala':'天廻龙','S. Magala':'天廻龙','G. Magala':'黑蚀龙','G.Magala':'黑蚀龙','G.Maccao':'跳狗龙王','G.Rathian':'金火龙','K.Daora':'钢龙','S.Rathalos':'银火龙','S.Queen':'重甲虫','Y.Grg':'黑狼鸟','Brachy':'碎龙','Dreadqueen':'紫毒姬雌火龙','Daimyo':'大名盾蟹','Shogun':'将军镰蟹'}
parts={'claw':'爪','claws':'爪','horn':'角','horns':'角','head':'头部','tail':'尾巴','back':'背部','wing':'翅膀','wings':'翅膀','wingarm':'翼脚','wingarms':'翼脚','left wingarm':'左翼脚','right wingarm':'右翼脚','body':'躯干','chest':'胸部','jaw':'下颚','front leg':'前脚','front legs':'前脚','hind leg':'后脚','leg':'脚','legs':'脚','trunk':'鼻子','hump':'驼峰','spikes':'棘','fangs':'牙','arms':'腕部','crest':'头冠','mane':'鬃毛','ears':'耳朵','shell':'外壳','outer shell':'外壳','cutwing':'刃翼','top fin':'背鳍','wingtalon':'翼爪','feeler':'触角','feelers':'触角','side blowholes':'侧面喷气孔','gills':'鳃'}
for g in list(out['goals']):
 m=re.fullmatch(r"(?:Break|Wound) (?:the )?(.+?)'s (.+)",g)
 if m and m[1] in mon:
  texts=re.split(r'\s+and\s+|\s*&\s*|,\s*',m[2]);translated=[]
  for part in texts:
   if part.startswith(('sever its ','sever her ')):
    p=part.split(' ',2)[2];translated.append('切断'+mon[m[1]]+'的'+parts[p] if p in parts else None)
   else:translated.append(parts.get(part))
  if all(translated):out['goals'][g]='破坏'+mon[m[1]]+'的'+'、'.join(translated)
 if g.startswith('Deliver '):
  m=re.fullmatch(r'Deliver (\d+) (.+)',g)
  if m:
   en=m[2];cn=common.get(en) or common.get(en[:-1])
   if cn:out['goals'][g]='交付'+m[1]+'个'+cn
# Remaining sources maintain known locations; no guess at equipment availability or rewards.
(RES/'linked-localization.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');(ROOT/'LINKED-LOCALIZATION-SOURCES.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
counts={};missing=[];combined={**old['items_by_id'],**out['items_by_id']}
for r in db.execute('select _id,name,type from items'):
 name=combined.get(str(r['_id']),base.get('items',{}).get(r['name'],r['name']))
 if r['type']=='Decoration':name=base.get('decorations',{}).get(str(r['_id']),name)
 kind=r['type'] or 'Item';counts.setdefault(kind,[0,0]);counts[kind][1]+=1
 if re.search('[\u3400-\u9fff]',name):counts[kind][0]+=1
 elif kind in ['Item','Materials']:missing.append({'id':r['_id'],'english':r['name'],'type':kind})
qmissing=[]
for r in db.execute('select _id,name from quests'):
 n=out['quests_by_id'].get(str(r['_id']),base['quests'].get(r['name'],r['name']))
 if not re.search('[\u3400-\u9fff]',n):qmissing.append({'id':r['_id'],'english':r['name']})
counts['Quests']=[1355-len(qmissing),1355]
left=[{'english':k,'translated':v} for k,v in out['goals'].items() if re.search('[a-zA-Z]{2,}',v)]
(ROOT/'LOCALIZATION-COVERAGE.json').write_text(json.dumps({'coverage':counts,'untranslated_items':missing,'untranslated_quests':qmissing,'goals_needing_review':left},ensure_ascii=False,indent=2)+'\n')
print(counts);print('Remaining mixed goal text:',left)
