#!/usr/bin/env python3
"""Conservative exact-stat alignment of community Chinese names; never join by position."""
import collections, json, re, sqlite3, unicodedata
from pathlib import Path
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache/data-sources'
RES = ROOT / 'Sources/HunterDex/Resources'
db = sqlite3.connect(RES/'mhgu.db'); db.row_factory = sqlite3.Row
cn = sqlite3.connect(CACHE/'jestar-mhgu.db'); cn.row_factory = sqlite3.Row
base = json.loads((RES/'zh.json').read_text())
translations = {}; provenance = {}; report = {}
TYPES = ['Great Sword','Long Sword','Sword and Shield','Dual Blades','Hammer','Hunting Horn','Lance','Gunlance','Switch Axe','Charge Blade','Insect Glaive','Bow','Light Bowgun','Heavy Bowgun']
ELEMENTS={'Fire':'火','Water':'水','Thunder':'雷','Ice':'冰','Dragon':'龙','Poison':'毒','Paralysis':'麻痹','Sleep':'睡眠','Blastblight':'爆破','Blast':'爆破'}

def normalized(text): return unicodedata.normalize('NFKC',text).strip()
def clean_name(text):
    text=normalized(text)
    text=re.sub(r'\[(?:生产G?|生产|购入|購入|XX|生産G?|终|最終)\]','',text).strip()
    if re.search(r'[\u3040-\u30ff]', text): return None
    return text if re.search(r'[\u3400-\u9fff]',text) else None

def signature_db(r):
    sharp=tuple(map(int,(r['sharpness'] or '').split()[0].split('.'))) if r['sharpness'] else ()
    elements=tuple(sorted((ELEMENTS.get(r[k],r[k]),r[v]) for k,v in [('element','element_attack'),('element_2','element_2_attack')] if r[k]))
    return (r['attack'],r['num_slots'],str(r['affinity']),elements,sharp,r['defense'] or 0)

def wiki_groups(paths,kind):
    groups=collections.defaultdict(list)
    for path in paths:
        if not path.exists(): continue
        soup=BeautifulSoup(path.read_text(),'html.parser')
        table=soup.select_one('#sorter')
        if not table:continue
        for tr in table.select(':scope > tbody > tr'):
            cells=tr.find_all('td',recursive=False)
            if len(cells)<5:continue
            first=cells[0];btn=first.select_one('.panel_btn')
            ids=re.findall(r'a_cl(\d+)', ' '.join(tr.get('class',[])))
            group=ids[0] if ids else (re.search(r'id(\d+)',btn.get('id','')).group(1) if btn else None)
            if not group:continue
            ranged=kind in ['Light Bowgun','Heavy Bowgun']
            stat=cells[1] if ranged else cells[2]
            attack=int(cells[1].select_one('.b').get_text()) if ranged else int(cells[1].get_text(strip=True))
            stattext=normalized(stat.get_text(' ',strip=True))
            affinity=re.search(r'会心\s*([\d+\-]+)\s*%',stattext)
            affinity=str(int(affinity.group(1))) if affinity else '0'
            defense=re.search(r'防[御禦]?\s*[+:]?\s*(\d+)',stattext)
            defense=int(defense.group(1)) if defense else 0
            elements=[]
            for el in stat.select('[class*=type_]'):
                t=normalized(el.get_text())
                match=re.search(r'(火|水|雷|冰|氷|龙|龍|毒|麻痹|麻痺|睡眠|爆破)\s*(\d+)',t)
                if match:
                    name={'氷':'冰','龍':'龙','麻痺':'麻痹'}.get(match.group(1),match.group(1))
                    elements.append((name,int(match.group(2))))
            sharp=tuple(len(tr.select_one('.kr'+str(i)).get_text()) for i in range(7)) if tr.select_one('.kr0') else ()
            slottext=cells[1].get_text() if ranged else cells[-1].get_text()
            slots=slottext.count('◯')+slottext.count('○')
            for el in first.select('.hasei,.panel_btn,.c_g,.c_r,.c_p'):el.decompose()
            name=normalized(''.join(first.stripped_strings))
            groups[group].append({'name':name,'signature':(attack,slots,affinity,tuple(sorted(elements)),sharp,defense),'page':path.name})
    return groups

for i,kind in enumerate(TYPES):
    paths=[CACHE/'jestar/data'/f'{1900+i}.html']
    if i not in (9,10):paths.append(CACHE/'jestar/data'/f'{2882+i}.html')
    wiki=wiki_groups(paths,kind); source=collections.defaultdict(list); native=collections.defaultdict(list)
    for gid,rows in wiki.items():source[tuple(r['signature'] for r in rows)].append(gid)
    for row in db.execute('SELECT i.name,w.* FROM weapons w JOIN items i USING(_id) WHERE wtype=? ORDER BY w._id',(kind,)):
        native[row['family']].append(row)
    reverse=collections.Counter(tuple(signature_db(r) for r in rows) for rows in native.values())
    count=0
    for family,rows in native.items():
        sig=tuple(signature_db(r) for r in rows); candidates=source.get(sig,[])
        if len(candidates)!=1 or reverse[sig]!=1:continue
        gid=candidates[0]
        for row,zhrow in zip(rows,wiki[gid]):
            name=clean_name(zhrow['name'])
            if not name:continue
            level=int(re.search(r'(\d+)$',row['name']).group(1))
            if name.endswith(str(level)):name=name[:-len(str(level))].rstrip()
            translations[str(row['_id'])]=f'{name} Lv.{level}'
            provenance[str(row['_id'])]={'source':f'jestar719/mhgu:ida/{gid}.html','method':'unique complete-family attack/slots/affinity/elements/sharpness/defense sequence','english':row['name']}
            count+=1
    report[kind]={'mapped':count,'total':sum(map(len,native.values()))}

# Armor: require equal stats, equipment slot, gender and hunter type; ambiguity is not guessed.
lookup=collections.defaultdict(list)
for row in cn.execute('SELECT * FROM Equip'):
    sig=tuple(row[k] for k in ['defence','rare','slotNum','fire','water','ice','flash','dragon','part','sex','type'])
    lookup[sig].append(row)
armor_count=0
for row in db.execute('SELECT i.name,i.rarity,a.* FROM armor a JOIN items i USING(_id)'):
    sig=tuple(row[k] for k in ['defense','rarity','num_slots','fire_res','water_res','ice_res','thunder_res','dragon_res'])+(['Head','Body','Arms','Waist','Legs'].index(row['slot']),{0:1,1:2,2:0}[row['gender']],{0:1,1:2,2:0}[row['hunter_type']])
    candidates=lookup.get(sig,[])
    if row['hunter_type']!=2:candidates=[r for r in candidates if r['maxDefence']==row['max_defense']]
    names={clean_name(r['name']) for r in candidates};names.discard(None)
    if len(names)!=1:continue
    name=next(iter(names))
    translations[str(row['_id'])]=name
    provenance[str(row['_id'])]={'source':'jestar719/mhgu:'+candidates[0]['url'],'method':'unique armor stats/slot/gender/hunter-type','english':row['name']}
    armor_count+=1
report['Armor']={'mapped':armor_count,'total':5637}
# Verified community item names. Only accept exact names present in the source index.
item_soup=BeautifulSoup((CACHE/'jestar/data/2100.html').read_text(),'html.parser')
source_items={normalized(a.get_text()):a.get('href','').replace('../','') for a in item_soup.select('table a[href*="ida/"]')}
common={
'Iron Ore':'铁矿石','Earth Crystal':'大地的结晶','Machalite Ore':'燕雀石','Dragonite Ore':'辉龙石','Carbalite Ore':'灵鹤石','Eltalite Ore':'绯鸾石','Meldspar Ore':'云鸠石','Fucium Ore':'白鹭石','Lightcrystal':'光水晶','Novacrystal':'诺亚水晶','Purecrystal':'纯水晶','Ice Crystal':'冰结晶','Firestone':'红莲石','Lava Nugget':'溶岩块','Firecell Stone':'狱炎石','Allfire Stone':'真红莲石','Bealite Ore':'青闪石','Disc Stone':'圆盘石','Stone':'石子','Whetstone':'砥石','Herb':'药草','Blue Mushroom':'蓝蘑菇','Honey':'蜂蜜','Potion':'回复药','Mega Potion':'回复药G','Antidote':'解毒药','Max Potion':'秘药','Ancient Potion':'远古的秘药','Lifepowder':'生命粉尘','Lifedust':'生命之粉','Well-done Steak':'熟肉','Raw Meat':'生肉','Hot Drink':'热饮','Cool Drink':'冷饮','Paintball':'染色球','Dung Bomb':'肥料玉','Flash Bomb':'闪光玉','Sonic Bomb':'音爆弹','Shock Trap':'麻痹陷阱','Pitfall Trap':'落穴','Trap Tool':'陷阱工具','Spider Web':'蜘蛛的巢','Net':'网','Bitterbug':'苦虫','Godbug':'不死虫','Thunderbug':'雷光虫','Carpenterbug':'木天蓼虫','Monster Bone S':'龙骨【小】','Monster Bone M':'龙骨【中】','Monster Bone L':'龙骨【大】','Monster Bone+':'上龙骨','Dragonbone Relic':'古老的龙骨','Unknown Skull':'谜之头骨','Brute Bone':'兽骨','Mystery Bone':'谜之骨','Warm Pelt':'暖毛皮','Velociprey Scale':'蓝速龙的鱗','Velociprey Hide':'蓝速龙的皮','Rathalos Scale':'火龙的鱗','Rathian Scale':'雌火龙的鱗','Rathalos Shell':'火龙的甲壳','Rathian Shell':'雌火龙的甲壳'
}
# Material suffixes are only used when the exact full Chinese name is attested.
prefixes={'Rathalos':'火龙','Rathian':'雌火龙','Tigrex':'轰龙','Nargacuga':'迅龙','Zinogre':'雷狼龙','Lagiacrus':'海龙','Brachydios':'碎龙','Gammoth':'巨兽','Mizutsune':'泡狐龙','Astalos':'电龙','Glavenus':'斩龙','Gore Magala':'黑蚀龙','Shagaru Magala':'天廻龙','Diablos':'角龙','Basarios':'岩龙','Gravios':'铠龙','Uragaan':'爆锤龙','Barroth':'土砂龙','Duramboros':'尾锤龙','Valstrax':'天彗龙','Seregios':'千刃龙','Deviljho':'恐暴龙','Alatreon':'煌黑龙','Amatsu':'岚龙','Akantor':'霸龙','Ukanlos':'崩龙','Kirin':'麒麟','Teostra':'炎王龙','Kushala Daora':'钢龙','Chameleos':'霞龙','Rajang':'金狮子','Velociprey':'蓝速龙','Giaprey':'白速龙','Genprey':'黄速龙','Ioprey':'红速龙','Arzuros':'青熊兽','Lagombi':'白兔兽','Volvidon':'赤甲兽','Kecha Wacha':'奇猿狐','Tetsucabra':'鬼蛙','Najarala':'绞蛇龙','Nerscylla':'影蜘蛛','Malfestio':'夜鸟','Royal Ludroth':'水兽'}
suffixes={'Scale':'鱗','Scale+':'上鱗','Shard':'厚鱗','Shell':'甲壳','Carapace':'坚壳','Cortex':'重壳','Claw':'爪','Claw+':'尖爪','Hardclaw':'刚爪','Tail':'尾巴','Lash':'靭尾','Marrow':'骨髄','Medulla':'延髄','Plate':'逆鱗','Ruby':'红玉','Mantle':'天鱗','Pallium':'天壳','Gem':'宝玉','Hide':'皮','Hide+':'上皮','Wing':'翼','Fellwing':'刚翼','Horn':'角','Horn+':'尖角','Hardhorn':'刚角'}
item_count=0
for row in db.execute("SELECT _id,name FROM items WHERE type='' ORDER BY _id"):
    en=row['name'];name=common.get(en)
    if name not in source_items:
        name=None
        for prefix,zhprefix in prefixes.items():
            if not en.startswith(prefix+' '):continue
            suffix=suffixes.get(en[len(prefix)+1:])
            candidate=zhprefix+'的'+suffix if suffix else ''
            if candidate in source_items:name=candidate;break
    if not name or name not in source_items:continue
    translations[str(row['_id'])]=name
    provenance[str(row['_id'])]={'source':'jestar719/mhgu:'+source_items[name],'method':'reviewed material terminology + exact attested full-name','english':en}
    item_count+=1
report['Materials']={'mapped':item_count}
monster_names=json.loads((ROOT/'scripts/monster-names.json').read_text())
(RES/'localization.json').write_text(json.dumps({'items_by_id':translations,'monsters':monster_names,'weapon_types':{'Switch Axe':'斩击斧','Charge Blade':'盾斧','Heavy Bowgun':'重弩','Light Bowgun':'轻弩'},'conditions':{'Break Head':'破坏头部','Break Back':'破坏背部','Break Wings':'破坏翅膀','Break Horn':'破坏角','Break Horns':'破坏角','Break Claws':'破坏爪','Break Legs':'破坏脚','Break Shell':'破坏甲壳','Normal':'通常状态'}},ensure_ascii=False,indent=2)+'\n')
(ROOT/'LOCALIZATION-SOURCES.json').write_text(json.dumps({'sources':['https://github.com/jestar719/mhgu'],'coverage':report,'items':provenance},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
print('TOTAL',len(translations))
