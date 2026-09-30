#!/usr/bin/env python3
"""Import reviewed item names after checking cached Chinese detail pages."""
import json
import re
import sqlite3
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'Sources/HunterDex/Resources'
CACHE = ROOT / '.cache/data-sources/jestar/ida'
db = sqlite3.connect(RES / 'mhgu.db')
db.row_factory = sqlite3.Row
linked_path = RES / 'linked-localization.json'
evidence_path = ROOT / 'LINKED-LOCALIZATION-SOURCES.json'
linked = json.loads(linked_path.read_text())
evidence = json.loads(evidence_path.read_text())

# English database item -> (app translation, source title, detail page ID).
# Translations were reviewed against the Chinese item index; target pages are
# checked again on every run. A few source titles contain traditional glyphs,
# so their simplified app form is recorded separately.
TRANSLATIONS = {
    'Bherna Ticket': ('贝尔纳券', '贝尔纳券', '226824'),
    'Bherna Ticket G': ('贝尔纳券G', '贝尔纳券G', '295214'),
    'Kokoto Ticket': ('科科特券', '科科特券', '226815'),
    'Kokoto Ticket G': ('科科特券G', '科科特券G', '295183'),
    'Pokke Ticket': ('波克券', '波克券', '219952'),
    'Pokke Ticket G': ('波克券G', '波克券G', '295216'),
    'Yukumo Ticket': ('结云券', '结云券', '189652'),
    'Yukumo Ticket G': ('结云券G', '结云券G', '295218'),
    'Wycademy Ticket': ('龙历院券', '龙历院券', '219272'),
    'Wycademy Ticket G': ('龙历院券G', '龙历院券G', '295220'),
    'Soaratorium Ticket': ('龙识船券', '龙识船券', '296115'),
    'Pub Ticket': ('酒场券', '酒场券', '296031'),
    'Palico Ticket': ('随从猫券', '随从猫券', '219765'),
    'Palico Ticket G': ('随从猫券G', '随从猫券G', '295173'),
    'Airship Ticket': ('飞行船券', '飞行船券', '219938'),
    'Airship Ticket G': ('飞行船券G', '飞行船券G', '296100'),
    'Bistro Ticket': ('食堂券', '食堂券', '226822'),
    'Trade Ticket': ('交易券', '交易券', '229824'),
    'Footbath Ticket': ('足浴券', '足浴券', '229765'),
    'Blackbelt Ticket': ('黑带券', '黑带券', '226813'),
    'Expert Ticket': ('达人券', '达人券', '229844'),
    'Expert Ticket G': ('达人券G', '达人券G', '296038'),
    'Legend Ticket': ('传说券', '传说券', '229854'),
    'Legend Ticket G': ('传说券G', '传说券G', '296043'),
    'EX Rathalos Ticket': ('EX火龙券', 'EX火龙券', '234118'),
    'EX Lavasioth Ticket': ('EX溶岩龙券', 'EX溶岩龙券', '234128'),
    'EX S.Magala Ticket': ('EX天廻龙券', 'EX天廻龙券', '234127'),
    'EX Daora Ticket': ('EX钢龙券', 'EX钢龙券', '234122'),
    'EX Chameleos Ticket': ('EX霞龙券', 'EX霞龙券', '234117'),
    'EX Teostra Ticket': ('EX炎王龙券', 'EX炎王龙券', '234116'),
    'EX G.Rathian Ticket': ('EX金火龙券', 'EX金火龙券', '234120'),
    'EX S.Rathalos Ticket': ('EX银火龙券', 'EX银火龙券', '234121'),
    'EX C.Fatalis Ticket': ('EX黑龙券・红', 'EX黑龙券・红', '296009'),
    'EX Old Fatalis Ticket': ('EX黑龙券・白', 'EX黑龙券・白', '296008'),
    'EX Lao-Shan Ticket S': ('EX老山龙券S', 'EX老山龙券S', '296011'),
    'Choice Mushroom': ('严选蘑菇', '严选蘑菇', '188677'),
    'Ripened Mushroom': ('熟成蘑菇', '熟成蘑菇', '189009'),
    'Unique Fern': ('特产紫萁', '特产紫萁', '218393'),
    'Goldenfish': ('黄金鱼', '黄金魚', '188362'),
    'Brocadefish': ('锦鱼', '锦魚', '221870'),
    'King Brocadefish': ('王锦鱼', '王锦魚', '227467'),
    'White Liver': ('白肝', '白肝', '219347'),
    'Monster Guts': ('怪物的肝', '怪物的肝', '219966'),
    'Piscine Liver': ('鱼龙的肝', '魚龙的肝', '219822'),
    'Popo Tongue': ('猛犸的舌头', '猛犸的舌头', '219345'),
    'Slagtoth Oil': ('垂皮油', '垂皮油', '189055'),
    'Fine Stomach': ('漂亮之腹袋', '漂亮之腹袋', '188598'),
    'Luminous Stomach': ('闪光腹袋', '闪光腹袋', '219791'),
    'Deep Bloodstone': ('深血石', '深血石', '227537'),
    'Water Lily Tuber': ('深睡莲的块根', '深睡莲的块根', '220941'),
    'Khezu Coin': ('白电龙币', '白电龙币', '229905'),
    'Najarala Coin': ('绞蛇龙币', '绞蛇龙币', '229787'),
    'Rathalos Coin': ('雄火龙币', '雄火龙币', '229932'),
    'Kecha Coin': ('奇猿狐币', '奇猿狐币', '229823'),
    'Plesioth Coin': ('水龙币', '水龙币', '229786'),
    'Brachydios Coin': ('碎龙币', '碎龙币', '229904'),
    'Gypceros Coin': ('毒怪鸟币', '毒怪鸟币', '226814'),
    'Garuga Coin': ('黑狼鸟币', '黑狼鸟币', '296019'),
    'Uragaan Coin': ('爆锤龙币', '爆锤龙币', '296020'),
    'Seregios Coin': ('千刃龙币', '千刃龙币', '296116'),
    'Tetsucabra Coin': ('鬼蛙币', '鬼蛙币', '296018'),
    'Congalala Coin': ('桃毛兽币', '桃毛兽币', '296099'),
    'Insect Scrap': ('虫的端材', '虫的端材', '229919'),
    'Insect Scrap+': ('虫的上端材', '虫的上端材', '229918'),
    'Heavy Insect Scrap': ('虫的重端材', '虫的重端材', '321641'),
    'Wood Scrap': ('木的端材', '木的端材', '229791'),
    'Wood Scrap+': ('木的上端材', '木的上端材', '229790'),
    'Heavy Wood Scrap': ('木的重端材', '木的重端材', '321531'),
    'Fur Scrap': ('毛皮的端材', '毛皮的端材', '229822'),
    'Fur Scrap+': ('毛皮的上端材', '毛皮的上端材', '229821'),
    'Heavy Fur Scrap': ('毛皮的重端材', '毛皮的重端材', '321544'),
    'Humble Scrap': ('朴素端材', '朴素端材', '189140'),
    'Humble Scrap+': ('朴素的上端材', '朴素的上端材', '189139'),
    'Heavy Humble Scrap': ('朴素的重端材', '朴素的重端材', '321594'),
    'Gourmet Voucher': ('高级餐券', '高级餐券', '188697'),
    'Commendation': ('勇气之证', '勇气之证', '189645'),
    'Commendation G': ('勇气之证G', '勇气之证G', '189646'),
    'Accolade G': ('希望之证G', '希望之证G', '229793'),
    'Pawprint Stamp': ('肉球印章', '肉球印章', '189351'),
    'Pawprint Ticket': ('肉球的优待券', '肉球的優待券', '286370'),
    'Handsome Scrap': ('纯粹端材', '纯粹端材', '188297'),
    'Handsome Scrap+': ('纯粹上端材', '纯粹上端材', '188296'),
    'Heavy Handsome Scrap': ('纯粹重端材', '纯粹重端材', '321488'),
    'Great Jaggi Scrap': ('狗龙的端材', '狗龙的端材', '237546'),
    'Great Jaggi Scrap+': ('狗龙的上端材', '狗龙的上端材', '237545'),
    'Hvy Great Jaggi Scrap': ('狗龙的重端材', '狗龙的重端材', '321543'),
    'Cephalos Scrap': ('沙龙的端材', '沙龙的端材', '237567'),
    'Cephalos Scrap+': ('沙龙的上端材', '沙龙的上端材', '219844'),
    'Heavy Cephalos Scrap': ('沙龙的重端材', '沙龙的重端材', '321564'),
    'Shogun Scrap': ('镰蟹的端材', '镰蟹的端材', '237524'),
    'Shogun Scrap+': ('镰蟹的上端材', '镰蟹的上端材', '237523'),
    'Heavy Shogun Scrap': ('镰蟹的重端材', '镰蟹的重端材', '321520'),
    'Khezu Scrap': ('电龙的端材', '电龙的端材', '237639'),
    'Heavy K.Daora Scrap': ('钢龙的重端材', '钢龙的重端材', '321550'),
    'Heavy Lao Shan Scrap': ('老山龙的重端材', '老山龙的重端材', '321661'),
    'Heavy O.Fatalis Scrap': ('祖龙的重端材', '祖龙的重端材', '321595'),
    'Husk Scrap': ('骸的端材', '骸的端材', '237673'),
    'Husk Scrap+': ('骸的上端材', '骸的上端材', '237672'),
    'Heavy Husk Scrap': ('骸的重端材', '骸的重端材', '321640'),
    'Heavy Narkakos Scrap': ('骸龙的重端材', '骸龙的重端材', '321510'),
    'Prime Redhelm Scrap': ('红盔的铭端材', '红盔的銘端材', '237657'),
    'Elite Redhelm Scrap': ('红盔的真端材', '红盔的真端材', '321627'),
    'Prime Snowbaron Scrap': ('大雪主的铭端材', '大雪主的銘端材', '237518'),
    'Elite Snowbaron Scrap': ('大雪主的真端材', '大雪主的真端材', '321498'),
    'Prime Deadeye Scrap': ('独眼的铭端材', '独眼的銘端材', '237619'),
    'Elite Deadeye Scrap': ('独眼的真端材', '独眼的真端材', '321586'),
    'Prime Drilltusk Scrap': ('岩穿的铭端材', '岩穿的銘端材', '237506'),
    'Elite Drilltusk Scrap': ('岩穿的真端材', '岩穿的真端材', '321490'),
    'Prime Stonefist Scrap': ('矛碎的铭端材', '矛碎的銘端材', '237671'),
    'Elite Stonefist Scrap': ('矛碎的真端材', '矛碎的真端材', '321637'),
    'Elite Rustrazor Scrap': ('铠裂的真端材', '铠裂的真端材', '321652'),
    'Prime C.beard Scrap': ('宝缠的铭端材', '宝缠的銘端材', '237633'),
    'Elite C.beard Scrap': ('宝缠的真端材', '宝缠的真端材', '321596'),
    'Perfect C.beard Scrap': ('宝缠的天端材', '宝缠的天端材', '321597'),
    'Prime Silverwind Scrap': ('白疾风的铭端材', '白疾风的銘端材', '237593'),
    'Elite Silverwind Scrap': ('白疾风的真端材', '白疾风的真端材', '321571'),
    'Prime Dreadking Scrap': ('黑炎王的铭端材', '黑炎王的銘端材', '237562'),
    'Elite Dreadking Scrap': ('黑炎王的真端材', '黑炎王的真端材', '321553'),
    'Prime Thunderlord Scrap': ('金雷公的铭端材', '金雷公的銘端材', '237544'),
    'Elite Thunderlord Scrap': ('金雷公的真端材', '金雷公的真端材', '321539'),
    'Perf. Thunderlord Scrap': ('金雷公的天端材', '金雷公的天端材', '321540'),
    'Elite Boltreaver Scrap': ('青电主的真端材', '青电主的真端材', '321583'),
    'Elite Elderfrost Scrap': ('银岭的真端材', '银岭的真端材', '321541'),
    'Elite Soulseer Scrap': ('天眼的真端材', '天眼的真端材', '321604'),
    'Prime Hellblade Scrap': ('烬灭刃的铭端材', '烬灭刃的銘端材', '237605'),
    'Elite Hellblade Scrap': ('烬灭刃的真端材', '烬灭刃的真端材', '321575'),
    'Prime Grimclaw Scrap': ('荒钩爪的铭端材', '荒钩爪的銘端材', '237491'),
    'Elite Grimclaw Scrap': ('荒钩爪的真端材', '荒钩爪的真端材', '321485'),
    'Elite Bloodbath Scrap': ('鏖魔的真端材', '鏖魔的真端材', '321495'),
    'Hyper Kut-Ku Scrap': ('怪鸟的猛端材', '怪鸟的猛端材', '237520'),
    'Hyper Kut-Ku Scrap X': ('怪鸟的狞端材', '怪鸟的狞端材', '321508'),
    'Hyper Gypceros Scrap': ('毒怪鸟的猛端材', '毒怪鸟的猛端材', '237643'),
    'Hyper Gypceros Scrap X': ('毒怪鸟的狞端材', '毒怪鸟的狞端材', '321611'),
    'Hyper Kecha Scrap': ('奇猿狐的猛端材', '奇猿狐的猛端材', '237527'),
    'Hyper Kecha Scrap X': ('奇猿狐的狞端材', '奇猿狐的狞端材', '321530'),
    'Hyper Plesioth Scrap': ('水龙的猛端材', '水龙的猛端材', '237608'),
    'Hyper Plesioth Scrap X': ('水龙的狞端材', '水龙的狞端材', '321582'),
    'Hyper R.Ludroth Scrap': ('水兽的猛端材', '水兽的猛端材', '237607'),
    'Hyper R.Ludroth Scrap X': ('水兽的狞端材', '水兽的狞端材', '321580'),
    'Hyper Nibelsnarf Scrap': ('潜口龙的猛端材', '潜口龙的猛端材', '237620'),
    'Hypr Nibelsnarf Scrap X': ('潜口龙的狞端材', '潜口龙的狞端材', '321590'),
    'Hyper Lagiacrus Scrap': ('海龙的猛端材', '海龙的猛端材', '237521'),
    'Hyper Lagiacrus Scrap X': ('海龙的狞端材', '海龙的狞端材', '321511'),
    'Hyper Agnaktor Scrap': ('炎戈龙的猛端材', '炎戈龙的猛端材', '237507'),
    'Hyper Agnaktor Scrap X': ('炎戈龙的狞端材', '炎戈龙的狞端材', '321494'),
    'Hyper Tetsu. Scrap': ('鬼蛙的猛端材', '鬼蛙的猛端材', '237519'),
    'Hyper Tetsu. Scrap X': ('鬼蛙的狞端材', '鬼蛙的狞端材', '321503'),
    'Hyper Najarala Scrap': ('绞蛇龙的猛端材', '绞蛇龙的猛端材', '237550'),
    'Hyper Najarala Scrap X': ('绞蛇龙的狞端材', '绞蛇龙的狞端材', '321549'),
    'Hyper Hermitaur Scrap': ('盾蟹的猛端材', '盾蟹的猛端材', '237635'),
    'Hypr Hermitaur Scrap X': ('盾蟹的狞端材', '盾蟹的狞端材', '321599'),
    'Hyper Shogun Scrap': ('镰蟹的猛端材', '镰蟹的猛端材', '237525'),
    'Hyper Shogun Scrap X': ('镰蟹的狞端材', '镰蟹的狞端材', '321521'),
    'Hyper Nerscylla Scrap X': ('影蜘蛛的狞端材', '影蜘蛛的狞端材', '321518'),
    'Hyper S.Queen Scrap': ('重甲虫的猛端材', '重甲虫的猛端材', '237582'),
    'Hyper S.Queen Scrap X': ('重甲虫的狞端材', '重甲虫的狞端材', '321570'),
    'Hyper Duram Scrap': ('尾锤龙的猛端材', '尾锤龙的猛端材', '237646'),
    'Hyper Duram Scrap X': ('尾锤龙的狞端材', '尾锤龙的狞端材', '321623'),
    'Hyper Nargacuga Scrap': ('迅龙的猛端材', '迅龙的猛端材', '237606'),
    'Hyper Narga Scrap X': ('迅龙的狞端材', '迅龙的狞端材', '321578'),
    'Hyper Barioth Scrap X': ('冰牙龙的狞端材', '冰牙龙的狞端材', '321626'),
    'Hyper Basarios Scrap X': ('岩龙的狞端材', '岩龙的狞端材', '321526'),
    'Hyper Gravios Scrap X': ('铠龙的狞端材', '铠龙的狞端材', '321656'),
    'Hyper Rathian Scrap': ('雌火龙的猛端材', '雌火龙的猛端材', '237675'),
    'Hyper Rathian Scrap X': ('雌火龙的狞端材', '雌火龙的狞端材', '321643'),
    'Hyper Zinogre Scrap': ('雷狼龙的猛端材', '雷狼龙的猛端材', '237684'),
    'Hyper Zinogre Scrap X': ('雷狼龙的狞端材', '雷狼龙的狞端材', '321660'),
    'Hyper Gammoth Scrap': ('巨兽的猛端材', '巨兽的猛端材', '237532'),
    'Hypr Gammoth Scrap X': ('巨兽的狞端材', '巨兽的狞端材', '321535'),
    'Hyper Mizutsune Scrap': ('泡狐龙的猛端材', '泡狐龙的猛端材', '237660'),
    'Hyper Mizutsune Scrap X': ('泡狐龙的狞端材', '泡狐龙的狞端材', '321635'),
    'Hyper Glavenus Scrap': ('斩龙的猛端材', '斩龙的猛端材', '237570'),
    'Hyper Glavenus Scrap X': ('斩龙的狞端材', '斩龙的狞端材', '321566'),
    'Hyper Tigrex Scrap': ('轰龙的猛端材', '轰龙的猛端材', '237551'),
    'Hyper Tigrex Scrap X': ('轰龙的狞端材', '轰龙的狞端材', '321552'),
    'Hyper Seregios Scrap': ('千刃龙的猛端材', '千刃龙的猛端材', '237622'),
    'Hyper Seregios Scrap X': ('千刃龙的狞端材', '千刃龙的狞端材', '321592'),
    'Hyper Rajang Scrap': ('金狮子的猛端材', '金狮子的猛端材', '237533'),
    'Hyper Rajang Scrap X': ('金狮子的狞端材', '金狮子的狞端材', '321538'),
    'Hyper Deviljho Scrap': ('恐暴龙的猛端材', '恐暴龙的猛端材', '237529'),
    'Hyper Deviljho Scrap X': ('恐暴龙的狞端材', '恐暴龙的狞端材', '321533'),
    'Hyper Malfestio Scrap': ('夜鸟的猛端材', '夜鸟的猛端材', '237678'),
    'Hyper Malfestio Scrap X': ('夜鸟的狞端材', '夜鸟的狞端材', '321647'),
    'Elite Nightcloak Scrap': ('胧隐的真端材', '朧隠的真端材', '321504'),
    'Perf. Nightcloak Scrap': ('胧隐的天端材', '朧隠的天端材', '321505'),
    'Hyper Garuga Scrap': ('黑狼鸟的猛端材', '黑狼鸟的猛端材', '237565'),
    'Hyper Garuga Scrap X': ('黑狼鸟的狞端材', '黑狼鸟的狞端材', '321560'),
    'Hyper Blangonga Scrap': ('雪狮子的猛端材', '雪狮子的猛端材', '237681'),
    'Hypr Blangonga Scrap X': ('雪狮子的狞端材', '雪狮子的狞端材', '321649'),
    'Hyper Barroth Scrap X': ('土沙龙的狞端材', '土沙龙的狞端材', '321614'),
    'Hyper Brach Scrap': ('碎龙的猛端材', '碎龙的猛端材', '237566'),
    'Hyper Brach Scrap X': ('碎龙的狞端材', '碎龙的狞端材', '321563'),
    'Hyper Diablos Scrap X': ('角龙的狞端材', '角龙的狞端材', '321515'),
    'Hyper Congalala Scrap': ('桃毛兽的狞端材', '桃毛兽的狞端材', '321645'),
    'Hyper Lavasioth Scrap': ('熔岩龙的猛端材', '溶岩龙的猛端材', '237683'),
    'Hyper Lavasioth Scrap X': ('熔岩龙的狞端材', '溶岩龙的狞端材', '321651'),
    'Zamtrios Scrap+': ('变形冰鲨的上端材', '化け鮫的上端材', '189420'),
    'Heavy Zamtrios Scrap': ('变形冰鲨的重端材', '化け鮫的重端材', '321618'),
    'Hyper Zamtrios Scrap': ('变形冰鲨的猛端材', '化け鮫的猛端材', '237645'),
    'Hyper Zamtrios Scrap X': ('变形冰鲨的狞端材', '化け鮫的狞端材', '321619'),
    'Hyper Uragaan Scrap': ('爆锤龙的猛端材', '爆鎚龙的猛端材', '237644'),
    'Hyper Uragaan Scrap X': ('爆锤龙的狞端材', '爆鎚龙的狞端材', '321616'),
    'Hyper Rathalos Scrap': ('火龙的猛端材', '火龙的猛端材', '237526'),
    'Hyper Rathalos Scrap X': ('火龙的狞端材', '火龙的狞端材', '321523'),
    'Heavy Ahtal-Ka Scrap': ('阁螳螂的重端材', '閣螳螂的重端材', '321512'),
    'Hyper Scrap': ('狞猛之端材', '狞猛之端材', '229882'),
    'Hyper Scrap+': ('狞猛之猛端材', '狞猛之猛端材', '229886'),
    'Hyper Scrap X': ('狞猛之狞端材', '狞猛之狞端材', '321608'),
    'Hyper Scrap XX': ('狞猛之狞猛端材', '狞猛之狞猛端材', '321609'),
    'Irregular Scrap': ('异形的端材', '异形的端材', '237494'),
    'Prime Irregular Scrap': ('异形的铭端材', '异形的銘端材', '237495'),
    'Elite Irregular Scrap': ('异形的真端材', '异形的真端材', '321489'),
    'Prime Dreadqueen Scrap': ('紫毒姬的铭端材', '紫毒姫的銘端材', '237581'),
    'Elite Dreadqueen Scrap': ('紫毒姬的真端材', '紫毒姫的真端材', '321567'),
    'Perfect Drdqueen Scrap': ('紫毒姬的天端材', '紫毒姫的天端材', '321568'),
    'Heavy C.Fatalis Scrap': ('黑龙的红重端材', '黑龙的红重端材', '321558'),
}

added = 0
for english, (chinese, source_title, source_id) in TRANSLATIONS.items():
    source_path = CACHE / f'{source_id}.html'
    if not source_path.exists():
        raise SystemExit(f'Missing source detail page for {english}: {source_path}')
    soup = BeautifulSoup(source_path.read_text(), 'html.parser')
    title = soup.select_one('table.t2 tr td .b')
    source_name = title.get_text(' ', strip=True) if title else ''
    if source_name != source_title:
        raise SystemExit(f'Source title mismatch for {english}: expected {source_title!r}, got {source_name!r}')

    rows = db.execute(
        "SELECT _id,rarity,carry_capacity FROM items WHERE type='' AND name=?",
        (english,),
    ).fetchall()
    if len(rows) != 1:
        raise SystemExit(f'Expected one database row for {english}, got {len(rows)}')

    source_stats = {}
    detail_rows = soup.select('table.t2 tr')
    if len(detail_rows) > 1:
        cells = detail_rows[1].find_all(['th', 'td'], recursive=False)
        for index in range(0, len(cells) - 1, 2):
            label = cells[index].get_text(' ', strip=True)
            value = re.search(r'\d+', cells[index + 1].get_text(' ', strip=True))
            if value and label.startswith('稀有度'):
                source_stats['rarity'] = int(value.group())
            elif value and label == '所持':
                source_stats['carry_capacity'] = int(value.group())
    expected_stats = {
        'rarity': rows[0]['rarity'],
        'carry_capacity': rows[0]['carry_capacity'],
    }
    if source_stats != expected_stats:
        raise SystemExit(f'Source stats mismatch for {english}: {source_stats} != {expected_stats}')
    item_id = str(rows[0]['_id'])
    previous = linked.setdefault('items_by_id', {}).get(item_id)
    if previous and previous != chinese:
        raise SystemExit(f'Conflicting existing translation for {english}: {previous!r}')
    linked['items_by_id'][item_id] = chinese
    evidence.setdefault('items', {})[item_id] = [{
        'name': chinese,
        'english': english,
        'method': 'reviewed English-to-Chinese item mapping; Chinese detail title, rarity and carry limit verified',
        'source': f'jestar719/mhgu:app/src/main/assets/mhxx/ida/{source_id}.html',
    }]
    if previous is None:
        added += 1

linked_path.write_text(json.dumps(linked, ensure_ascii=False, indent=2) + '\n')
evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
print(f'Imported {added} reviewed item names from checked Chinese detail pages.')
