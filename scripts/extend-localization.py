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
  level={'I':'1','II':'2','III':'3','IV':'4','V':'5','VI':'6','VII':'7','VIII':'8','IX':'9','X':'10'}.get(m[2])
  if m[2].startswith('G'):level='G级'+m[2][1:]
  elif m[2]=='EX':level='特别级'
  out['quests_by_id'][str(row['_id'])]='特殊许可·'+deviants[m[1]]+' '+(level or m[2])+'：'+{'Hunt':'狩猎','Capture':'捕获'}[m[3]]
  provenance['quests'][str(row['_id'])]={'method':'project translation of explicit deviant/level/action title','english':row['name']}
# Fill remaining English quest titles from a project-maintained Chinese title
# glossary. Existing source-matched and upstream Chinese titles take precedence.
quest_titles=json.loads((ROOT/'scripts/quest-title-translations.json').read_text())
quest_locations={'Jurassic Frontier':'古代林','Dunes':'旧沙漠','Verdant Hills':'森丘','Arctic Ridge':'雪山','Misty Peaks':'溪流','Deserted Island':'孤岛','Marshlands':'沼地','Volcano':'火山','Jungle':'密林','Frozen Seaway':'冰海'}
roman_titles={'I':'1','II':'2','III':'3','IV':'4','V':'5','VI':'6','VII':'7','VIII':'8','IX':'9','X':'10'}
quest_monsters={**old.get('monsters',{}),**names}
quest_monsters.update({'Great Maccao':'跳狗龙王','Velocidrome':'蓝速龙王','Giadrome':'白速龙王','Gendrome':'黄速龙王','Iodrome':'红速龙王','Yian Kut-Ku':'大怪鸟','Royal Ludroth':'水兽','Blangonga':'雪狮子王','Bullfango':'野猪','Jaggia':'贼龙','Giaprey':'白速龙','Genprey':'黄速龙','Velociprey':'蓝速龙','Arzuros':'青熊兽','Astalos':'电龙','Gammoth':'巨兽','Glavenus':'斩龙','Gore Magala':'黑蚀龙','Lagiacrus':'海龙','Lagombi':'白兔兽','Mizutsune':'泡狐龙','Nargacuga':'迅龙','Rathalos':'雄火龙','Tigrex':'轰龙','Volvidon':'赤甲兽','Zinogre':'雷狼龙'})
def translate_quest_title(title):
 m=re.fullmatch(r'Harvest Tour: (.+)',title)
 if m and m[1] in quest_locations:return '采集之旅：'+quest_locations[m[1]]
 m=re.fullmatch(r'(.+?) Accounting',title)
 if m and m[1] in quest_locations:return quest_locations[m[1]]+'采集结算'
 m=re.fullmatch(r'Event: Hunt-a-thon (\d+)',title)
 if m:return '活动任务：连续狩猎'+m[1]
 m=re.fullmatch(r'Event: Slay (?:a|an) (.+)',title)
 if m and m[1] in quest_monsters:return '活动任务：狩猎'+quest_monsters[m[1]]
 m=re.fullmatch(r'XX Trials: (.+)',title)
 if m:
  subject=m[1]
  if subject.startswith('Hunt-a-thon '):
   suffix=subject.rsplit(' ',1)[-1]
   return '双重交叉挑战：连续狩猎'+roman_titles.get(suffix,suffix)
  if subject in quest_monsters:return '双重交叉挑战：'+quest_monsters[subject]
 m=re.fullmatch(r'Grudge Match: (.+)',title)
 if m and m[1] in quest_monsters:return '宿敌对决：'+quest_monsters[m[1]]
 m=re.fullmatch(r'Lucky (.+) Cat',title)
 if m and m[1] in quest_locations:return '幸运猫咪：'+quest_locations[m[1]]
 m=re.fullmatch(r'Slay the (.+)!',title)
 if m and m[1] in quest_monsters:return '讨伐'+quest_monsters[m[1]]
 return None
for row in db.execute('select _id,name from quests'):
 iid=str(row['_id'])
 project_title=provenance.get('quests',{}).get(iid,{}).get('method')=='project translation of English quest title'
 if (iid in out.get('quests_by_id',{}) or row['name'] in base.get('quests',{})) and not project_title:continue
 translated=quest_titles.get(row['name']) or translate_quest_title(row['name'])
 if translated:
  out.setdefault('quests_by_id',{})[iid]=translated
  provenance.setdefault('quests',{})[iid]={'method':'project translation of English quest title','english':row['name']}
# One upstream alias still abbreviates the title in Latin characters.
for row in db.execute("select _id,name from quests where name='Advanced: Ultimate Generation'"):
 out.setdefault('quests_by_id',{})[str(row['_id'])]='高难度：终极世代'
 provenance.setdefault('quests',{})[str(row['_id'])]={'method':'project translation of quest title alias','english':row['name']}
for row in db.execute("select _id,name from quests where name in ('Monster Hunter Channel I','Monster Hunter Channel II')"):
 out.setdefault('quests_by_id',{})[str(row['_id'])]='怪物猎人频道 '+roman_titles[row['name'].rsplit(' ',1)[-1]]
 provenance.setdefault('quests',{})[str(row['_id'])]={'method':'project translation of numbered quest title','english':row['name']}
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
# Item material names use these attested prefixes rather than the displayed
# monster names (for example, Great Maccao items are indexed under 跳狗龙).
prefix.update({'Great Maccao':'跳狗龙','Elderfrost':'银岭'})
suffix={'Scale':'鱗','Scale+':'上鱗','Shard':'厚鱗','Shell':'甲壳','Carapace':'坚壳','Cortex':'重壳','Crtx':'重壳','Claw':'爪','Claw+':'尖爪','Hardclaw':'刚爪','Tail':'尾巴','Lash':'靭尾','Marrow':'骨髄','Medulla':'延髄','Plate':'逆鱗','Ruby':'红玉','Mantle':'天鱗','Pallium':'天壳','Gem':'宝玉','Hide':'皮','Hide+':'上皮','Piel':'厚皮','Wing':'翼','Fellwing':'刚翼','Horn':'角','Horn+':'尖角','Hardhorn':'刚角','Pelt':'毛','Pelt+':'刚毛','Fur':'豪刚毛','Scalp':'头壳','Scrap':'端材','Scrap+':'上端材','Scrap G':'重端材','Hardfang':'重牙','Fang':'牙','Fang+':'锐牙','Hvy Fang':'重牙','Fin':'鳍','Fin+':'上鳍','Grandfin':'特上鳍','Webbing':'翼膜','Crest':'鸡冠','Comb':'冠','Talons':'翼爪','Talon':'翼爪','Hardbone':'坚骨','Hvy Bone':'重骨'}
item_overrides={
 'Great Maccao Hide+':'跳狗龙的上赤皮','Great Maccao Piel':'跳狗龙的大赤皮',
 'Maccao Tailspike':'跳狗龙的尾棘','Maccao Tailspear':'跳狗龙的重尾棘',
 'Moofah Fleeceball':'云羊鹿的毛球','Remobra Finehide':'翼蛇龙的上皮',
 'Redhelm Furyhair':'红盔的豪刚毛','Snowbaron Cuirass':'大雪主的腹甲',
 'Kut-Ku Ear':'怪鸟的耳','Kut-Ku Luckear':'怪鸟的福耳',
 'Malfestio Tailfeather':'夜鸟的尾羽','Garuga Ear':'黑狼鸟的耳',
 'Silverwind Blackfur+':'白疾风的上黑毛','Hellblade Powder':'烬灭刃的粉尘',
 'Apceros Liver':'草食龙的肝','Gargwa Egg':'丸鸟的蛋',
 'Vespoid Wing':'飞虫的羽','Vespoid Innerwing':'飞虫的薄羽',
 'Genprey Fang':'黄速龙的大牙','Bullfango Pelt':'野猪的毛皮',
 'Bullfango Thickfur':'野猪的厚毛皮','Mighty Remobra Head':'翼蛇龙的头',
 'Hornetaur Shell':'坚壳虫的甲壳','Hornetaur Wing':'坚壳虫的羽',
 'Stonefist Talon':'矛碎的刚爪','Elderfrost Pelt':'银岭的刚毛',
 'Bloodbath Chine':'鏖魔的重甲','Hyper Rajang Fur':'狞猛化金狮子毛',
 'Plesioth Head':'水龙的お头','Uber Plesio Head':'水龙的绝品お头'
}
for row in db.execute("select _id,name from items where type=''"):
 iid=str(row['_id']);en=row['name']
 if en in item_overrides and item_overrides[en] in attested:
  name=item_overrides[en];out['items_by_id'][iid]=name
  provenance['items'][iid]=[{'name':name,'method':'project-reviewed material name + exact Chinese item-index attestation','source':'jestar719/mhgu:'+attested[name],'english':en}]
  continue
 if iid in out['items_by_id']:continue
 # Cat scrap quality prefixes are irregular in English. Accept only Chinese
 # names that appear verbatim in the community item index.
 scrap_name=None
 quality=re.fullmatch(r'(?:Heavy|Hvy) (.+) Scrap',en)
 if quality:
  for p,cn in sorted(prefix.items(),key=lambda v:-len(v[0])):
   if quality[1]==p:
    scrap_name=next((candidate for candidate in [cn+'的重端材',cn+'重端材'] if candidate in attested),None)
    if scrap_name:break
 quality=re.fullmatch(r'Perfect (.+) Scrap',en)
 if not scrap_name and quality:
  for p,cn in sorted(prefix.items(),key=lambda v:-len(v[0])):
   if quality[1]==p:
    scrap_name=next((candidate for candidate in [cn+'的真端材',cn+'真端材'] if candidate in attested),None)
    if scrap_name:break
 if scrap_name:
  out['items_by_id'][iid]=scrap_name
  provenance['items'][iid]=[{'name':scrap_name,'method':'reviewed Palico-scrap quality + exact Chinese item-index attestation','source':'jestar719/mhgu:app/src/main/assets/mhxx/'+attested[scrap_name],'english':en}]
  continue
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
common={'Mega Dash Juice':'强走药G','Dash Juice':'强走药','Demondrug':'鬼人药','Mega Demondrug':'鬼人药G','Armorskin':'硬化药','Mega Armorskin':'硬化药G','Nutrients':'营养剂','Mega Nutrients':'营养剂G','Might Seed':'怪力之种','Adamant Seed':'忍耐之种','Might Pill':'怪力药丸','Adamant Pill':'忍耐药丸','Immunizer':'活力剂','Catalyst':'增强剂','Energy Drink':'元气饮料','Cleanser':'消散剂','Deodorant':'消臭玉','Tranq Bomb':'捕获用麻醉玉','Tranq':'捕获用麻醉药','Smoke Bomb':'烟雾玉','Poison Smoke Bomb':'毒烟雾玉','Farcaster':'回家玉','Dung':'怪物的粪','Drugged Meat':'睡眠生肉','Tinged Meat':'麻痹生肉','Poisoned Meat':'毒生肉','Barrel Bomb S':'小桶爆弹','Barrel Bomb S+':'小桶爆弹G','Barrel Bomb L':'大桶爆弹','Barrel Bomb L+':'大桶爆弹G','Nitroshroom':'爆炸菇','Parashroom':'麻痹菇','Toadstool':'毒菇','Mopeshroom':'疲劳伞菇','Exciteshroom':'心跳蘑菇','Dragon Toadstool':'曼陀罗','Paintberry':'染色果','Scatternut':'爆裂核桃','Needleberry':'针果','Huskberry':'空心果','Latchberry':'贯通果','Bomberry':'扩散果','Bom Arowana':'爆裂龙鱼','Bomb Arowana':'爆裂龙鱼','Burst Arowana':'破裂龙鱼','Gloamgrass Root':'落阳草之根','Fire Herb':'火药草','Sleep Herb':'睡眠草','Antidote Herb':'解毒草','Ivy':'常春藤叶','Sap Plant':'粘着草','Felvine':'木天蓼','Nulberry':'抵消果实','Flashbug':'光虫','Carpenterbug':'粘着白蚁','Fulgurbug':'超电雷光虫','Bnahabra Shell':'飞甲虫的甲壳','Spider Web':'蜘蛛的巢'}
common.update({
 'Power Jelly':'力的成长饵','Power Jelly+':'力的上成长饵','Power Jelly++':'力的特上成长饵',
 'Heavy Jelly':'重的成长饵','Heavy Jelly+':'重的上成长饵','Heavy Jelly++':'重的特上成长饵',
 'Speed Jelly':'速的成长饵','Speed Jelly+':'速的上成长饵','Speed Jelly++':'速的特上成长饵',
 'Fire Ambrosia':'火的蜜饵','Water Ambrosia':'水的蜜饵','Thunder Ambrosia':'雷的蜜饵',
 'Ice Ambrosia':'冰的蜜饵','Dragon Ambrosia':'龙的蜜饵',
 'Fire Ambrosia+':'火炎的蜜饵','Water Ambrosia+':'流水的蜜饵',
 'Thunder Ambrosia+':'雷光的蜜饵','Ice Ambrosia+':'冰结的蜜饵','Dragon Ambrosia+':'灭龙的蜜饵',
 'Douse Ambrosia':'断水的蜜饵','Drought Ambrosia':'鎮火的蜜饵',
 'Resistor Ambrosia':'绝雷的蜜饵','Melt Ambrosia':'碎冰的蜜饵',
 'De-wyrm Ambrosia':'破龙的蜜饵','Reverse Ambrosia':'回溯的蜜饵',
 'Frog':'青蛙鱼饵','Antidote Flute':'解毒笛','Demon Flute':'鬼人笛',
 'Armor Flute':'硬化笛','King Cactus':'仙人掌王','Stargazer Flower':'观星之花',
 'Frozen Berry':'冰结晶草莓','Dosbiscus':'五彩花王','Chaos Mushroom':'混沌茸',
 'Bumblepumpkin':'大南瓜','Giant Acorn':'大筒橡果',
 'Yukumo Stoutwood':'结云的重木','Rare Fish':'没烤熟的魚',
 'Burnt Fish':'烤焦的魚','Gourmet Fish':'烤熟的魚','Armor Stone':'铠石',
 'Sushifish':'刺身鱼','Pin Tuna':'针金枪鱼','Speartuna':'旗金枪鱼',
 'Popfish':'爆裂沙丁鱼','Scatterfish':'扩散凸眼金鱼',
 'Glutton Tuna':'贪吃金枪鱼','Gastronome Tuna':'贪吃金枪鱼王',
 'Wanchovy':'深水沙丁鱼','Armored Bream':'铠甲鱼',
 'Irregular Bone':'异形的骨','Irregular Stoutbone':'异形的坚骨',
 'Irregular Slogbone':'异形的重骨','Steel Egg':'钢蛋','Silver Egg':'银蛋',
 'Springnight Carp':'春夜鯉','Guardfish':'金刚魚','Great Hornfly':'大角蝴蝶',
 'Large Herbivore Bone':'草食种的大重骨','Wyvern Fang':'龙牙',
 'Hyper Extract':'狞猛化浸出物','Potent Hyper Extract':'狞猛化浓縮浸出物',
 'Hyper Hardfang':'狞猛之重牙','Hyper Claw':'狞猛之爪',
 'Hyper Potent Paratoxin':'狞猛之強麻痹毒液','Hyper Sleep Sac':'狞猛之睡眠袋',
 'Hyper Catalyst+':'狞猛之爆縮液','Gargwa Feather':'丸鸟的羽',
 'First-aid Med':'应急药','First-aid Med+':'应急药G','Ration':'携带食料',
 'Portable Spit':'烤肉架','Mini Whetstone':'携带砥石',
 'EZ Shock Trap':'携带麻痹陷阱','EZ Flash Bomb':'支给专用闪光玉',
 'EZ Sonic Bomb':'音爆弹','EZ Max Potion':'应急秘药',
 'EZ Barrel Bomb L':'大桶爆弹G',"EZ Hunter's Drink":'狩技饮料',
 'Paw Pass Ticket':'肉球印章','Anti-dragon Bomb':'对巨龙爆弹',
})
for en,cn in common.items():
 if cn not in attested:continue
 for r in db.execute("select _id from items where name=? and type=''",(en,)):
  out['items_by_id'][str(r['_id'])]=cn;provenance['items'][str(r['_id'])]=[{'name':cn,'method':'reviewed common terminology + exact attestation','source':'jestar719/mhgu:app/src/main/assets/mhxx/'+attested[cn],'english':en}]
# Explicit project-reviewed item translations without an exact community-index
# match. These are based on each English item name and its database description.
project_item_translations={
 'Map':'地图','EZ Lifepowder':'生命粉尘','EZ Dust of Life':'生命大粉尘',
 'EZ Pitfall Trap':'携带落穴陷阱','EZ Farcaster':'携带回家玉',
 'Ballista Ammo':'弩炮弹','One-shot Binder':'单发式拘束弹',
 'Dense Marcoal':'高密度灭龙炭',
 'Kingmeat':'王者肉','Alchemy Barrel':'炼金桶','Alchemy Food':'炼金食物',
 'Sushifish Bait':'刺身鱼饵','Burst Bait':'爆裂鱼饵',
 'Goldenfish Bait':'黄金鱼饵','Garbage':'合成废料',
 'Spicy Mushroom':'特产蘑菇泡菜','Immaculate Ore':'无瑕矿石',
 'Bindshroom':'麻痹菌菇','Reststool':'椅子蘑菇',
 'Pristine Ore':'优质矿石',
}
for en,cn in project_item_translations.items():
 for r in db.execute("select _id from items where name=? and type=''",(en,)):
  iid=str(r['_id']);out['items_by_id'][iid]=cn
  provenance['items'][iid]=[{'name':cn,'method':'project-reviewed translation from English item name and database description; not an exact community-index match','english':en}]
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
for goal in allgoals:
 if goal=='None':goals[goal]='无'
 elif goal=='Place flag on mountain top':goals[goal]='在山顶插上旗帜'
 else:
  m=re.fullmatch(r'Mount (?:&|and) topple monster (twice|\d+ times)',goal)
  if m:
   count='两' if m[1]=='twice' else m[1].split()[0]
   goals[goal]=f'骑乘怪物并使其倒地{count}次'
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
