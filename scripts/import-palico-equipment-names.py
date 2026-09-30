#!/usr/bin/env python3
"""Import reviewed Felyne armor names using unique defense/resistance matches."""
import json
import re
import sqlite3
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'Sources/HunterDex/Resources'
CACHE = ROOT / '.cache/data-sources/jestar/data'
DB = sqlite3.connect(RES / 'mhgu.db')
DB.row_factory = sqlite3.Row
OUT = json.loads((RES / 'linked-localization.json').read_text())
EVIDENCE = json.loads((ROOT / 'LINKED-LOCALIZATION-SOURCES.json').read_text())

# A source row is accepted only when its rarity band and all five resistances
# plus defense identify one Felyne armor record and one source record.
NAME_TRANSLATIONS = {
    'F Redhelm Helm': '红盔猫头盔',
    'F Snowbaron Helm': '大雪主猫头盔',
    'F Stonefist Mask': '矛碎猫面具',
    'F Dreadqueen Helm': '紫毒姬猫头盔',
    'F Drilltusk Horn': '岩穿猫角冠',
    'F Silverwind Helm': '白疾风猫头盔',
    'F Crystalbeard Helm': '宝缠猫头盔',
    'F Deadeye Hood': '独眼猫兜帽',
    'F Dreadking Helm': '黑炎王猫头盔',
    'F Thunderlord Helm': '金雷公猫头盔',
    'F Grimclaw Helm': '荒钩爪猫头盔',
    'F Hellblade Helm': '烬灭刃猫头盔',
    'F Nightcloak Mask': '胧隐猫面具',
    'F Rustrazor Mask': '铠裂猫面具',
    'F Soulseer Kasa': '天眼猫斗笠',
    'F Boltreaver Mask': '青电主猫面具',
    'F Elderfrost Collar': '银岭猫项圈',
    'F Bloodbath Helm': '鏖魔猫头盔',
    'F Alta Hat': '甲虫猫贵族帽',
    'F Venombee Cap': '毒蜂猫帽',
    'F Gourmet Toque': '美食猫头巾',
    'F Aptonoth Mask': '草食龙猫面具',
    'F Gypceros Crest': '毒怪鸟猫头饰',
    'F Cabra Horn': '鬼蛙猫角冠',
    'F Derring Galea': '勇气猫头盔',
    'F Edel Pigtails': '以太猫双马尾',
    'F Kittendant Hood': '猫侍者兜帽',
    'F Blango Mask': '雪狮子猫面具',
    'F Pretty Toque': '俏丽猫布冠',
    'F Chaos Bulbs': '混沌猫花苞',
    'F El Dora Helm': '艾尔多拉猫头盔',
    'F Artian Core': '神秘猫核心',
    'F Lagia Tricorne': '海龙猫三角帽',
    'F Gammoth Collar': '巨兽猫项圈',
    'F Gore Horror': '黑蚀龙猫惊悚头罩',
    'F Kirin Horn': '麒麟猫角饰',
    'F Brachy Headgear': '碎龙猫头饰',
    'F Angel Halo': '天使猫光环',
    'F Genie Helm': '魔神猫头盔',
    'F Kaiser Periwig': '炎王猫假发',
    'F Ladybug Cap': '七星瓢虫猫帽',
    "F Guide's Hood": '导览猫兜帽',
    'F Khezu Catnurse': '白电龙猫护士帽',
    'F Zamtrios Helmet': '化鲛猫头盔',
    'F Acorn Mask': '橡果猫面具',
    'F Pincer Mask': '蟹钳猫面具',
    'F Beautiful Toque': '优雅猫布冠',
    'F Ultimate Mask': '终极猫面具',
    'F Soul Hairpiece': '魂之猫发饰',
    'F Transpurrter Kasa': '搬运猫斗笠',
    'F Dirty Locks': '脏辫猫发型',
    "F D'Artanyan's Hat": '达达尼昂猫帽',
    'F Angel Aura': '天使猫灵光环',
    'F Nakarkos Mask': '骸龙猫面具',
    'F Kaiser Crown': '炎王猫王冠',
    'F Akantor Visage': '霸龙猫面容',
    'F Ukanlos Visage': '崩龙猫面容',
    'F Majestic Crown': '尊贵猫王冠',
    'F Escador Wisdom': '煌黑龙猫智慧头饰',
    'F Strange Helm': '奇妙猫头盔',
    'F Pirate Bandanna J': '海盗J猫头巾',
    'F Baby Tiga Hat': '小轰龙猫帽',
    'F Postman Beret': '邮差猫贝雷帽',
    'F Booyah Pompadour': '欢呼猫飞机头',
    'F Sohoku Helmet': '总北猫头盔',
    'F Dark Meowgic Hood': '黑魔法猫兜帽',
    'F Buccaneer Bandanna J': '大海盗J猫头巾',
    'F Link Mask': '林克猫面具',
    'F Fox Mic': '狐狸猫麦克风',
    'F Mario Cap': '马力欧猫帽',
    'F Luigi Cap': '路易吉猫帽',
    'F Helm of Purrity': '纯洁猫头盔',
    'F Chun Chignon': '春丽猫发髻',
    'F Dante Wig': '但丁猫假发',
    'F Mega Helmet': '洛克人猫头盔',
    'F Melodic Curls': '旋律猫卷发',
    'F Sunsnug Mask': '暖阳猫面具',
    "F Meowniac's Mask": '猫迷面具',
    'F Alta Shirt': '甲虫猫衬衫',
    'F Cephalos Dress': '沙龙猫连衣裙',
    'F Venombee Wings': '毒蜂猫羽翼',
    'F Gourmet Suit': '美食猫套装',
    'F Aptonoth Suit': '草食龙猫套装',
    'F Gypceros Cloth': '毒怪鸟猫布衣',
    'F Cabra Wrap': '鬼蛙猫裹布',
    'F Derring Lorica': '勇气猫胸甲',
    'F Kittendant Suit': '猫侍者服',
    'F Marauder Armor': '武者猫铠甲',
    'F Naja Sirwal': '绞蛇龙猫灯笼裤',
    'F Pretty Robe': '俏丽猫长袍',
    'F Chaos Skirt': '混沌猫裙',
    'F El Dora Mail': '艾尔多拉猫铠甲',
    'F Artian Gear': '神秘猫装备',
    'F Mizutsune Suit': '泡狐龙猫套装',
    'F Gore Ghost': '黑蚀龙猫幽灵服',
    'F Seregios Mail': '千刃龙猫铠甲',
    'F Angel Feathers': '天使猫羽衣',
    'F Genie Carpet': '魔神猫地毯',
    'F Kaiser Robe': '炎王猫长袍',
    'F Ladybug Wings': '七星瓢虫猫翅膀',
    "F Guide's Suit": '导览猫制服',
    'F Khezu Smock': '白电龙猫罩衫',
    'F Shakalaka Duds': '奇面族猫服',
    'F Straw Raincoat': '草编猫雨衣',
    'F Lagia Pirate': '海龙猫海盗服',
    'F Puppeteer Garb': '傀儡师猫装束',
    'F Beautiful Robe': '优雅猫长袍',
    'F Arcadia Robe': '阿卡迪亚猫长袍',
    'F Transpurrter Cape': '搬运猫披风',
    'F Dirty Hakama': '脏辫猫袴',
    "F D'Artanyan's Cape": '达达尼昂猫披风',
    'F Brachy Fist': '碎龙猫拳套',
    'F Angel Down': '天使猫羽装',
    'F Nakarkos Suit': '骸龙猫装束',
    "F Felcote's Coat": '菲尔科特猫外套',
    'F Kaiser Panoply': '炎王猫全身铠',
    'F Akantor Facade': '霸龙猫面饰',
    'F Ukanlos Facade': '崩龙猫面饰',
    'F Majestic Robe': '尊贵猫长袍',
    'F Escador Soul': '煌黑龙猫魂装',
    'F Strange Mail': '奇妙猫铠甲',
    'F Redhelm Mail': '红盔猫铠甲',
    'F Snowbaron Mail': '大雪主猫铠甲',
    'F Stonefist Suit': '矛碎猫服',
    'F Dreadqueen Mail': '紫毒姬猫铠甲',
    'F Drilltusk Wrap': '岩穿猫裹布',
    'F Silverwind Mail': '白疾风猫铠甲',
    'F Crystalbeard Mail': '宝缠猫铠甲',
    'F Deadeye Robe': '独眼猫长袍',
    'F Dreadking Mail': '黑炎王猫铠甲',
    'F Thunderlord Mail': '金雷公猫铠甲',
    'F Grimclaw Mail': '荒钩爪猫铠甲',
    'F Hellblade Mail': '烬灭刃猫铠甲',
    'F Nightcloak Mail': '胧隐猫铠甲',
    'F Rustrazor Suit': '铠裂猫套装',
    'F Soulseer Suit': '天眼猫套装',
    'F Boltreaver Suit': '青电主猫套装',
    'F Elderfrost Coat': '银岭猫外套',
    'F Bloodbath Mail': '鏖魔猫铠甲',
    'F Chaos Bulbs+': '混沌猫花苞+',
    'F Chaos Skirt+': '混沌猫裙+',
    'F Ultimate Mask+': '终极猫面具+',
    'F Puppeteer Mask': '傀儡师猫面具',
    'F Puppeteer Mask+': '傀儡师猫面具+',
    'F Puppeteer Garb+': '傀儡师猫装束+',
    'F Lagia Triad': '海龙猫三件组',
    'F Monqlo Cap': '猫克罗帽',
    'F Monqlo Shirt': '猫克罗衬衫',
    'F Conga Steeple': '桃毛兽猫尖帽',
    'F Conga Fete': '桃毛兽猫庆典服',
    'F Pleasant Ribbons': '可爱猫缎带',
    'F Pleasant Dress': '可爱猫连衣裙',
    'F Grav Mask': '铠龙猫面具',
    'F Grav Armor': '铠龙猫铠甲',
    'F Diablos Helm': '角龙猫头盔',
    'F Diablos Mail': '角龙猫铠甲',
    'F Exquisite Toque': '华美猫布冠',
    'F Exquisite Robe': '华美猫长袍',
    'F Odd Pincer Mask': '奇异蟹钳猫面具',
    'F Transpurrrrter Kasa': '搬运猫斗笠',
    'F Grand Chaos Bulbs': '混沌猫花苞·极',
    'F Grand Chaos Skirt': '混沌猫裙·极',
    'F Cute Ribbon': '可爱猫缎带',
    'F Cute Dress': '可爱猫连衣裙',
    'F Guild Headgear': '公会猫头具',
    'F Spirit Hairpiece': '斗魂猫发饰',
    'F Pro Dirty Locks': '专业脏辫猫发型',
    "F D'Artanyan Hero Hat": '达达尼昂英雄猫帽',
    "F D'Artanyan Hero Cape": '达达尼昂英雄猫披风',
    "F Barman's Shades": '酒保猫墨镜',
    'F Grand Majestic Crown': '尊贵猫王冠·极',
    'F Grand Majestic Robe': '尊贵猫长袍·极',
    "F Arthur's Helm": '亚瑟猫头盔',
    "F Arthur's Armor": '亚瑟猫铠甲',
    'F Detective Specs': '名侦探猫眼镜',
    'F Phoenix Wig': '凤凰猫假发',
    'F Kittyback Hat': '猫咪背包帽',
    'F Zombie-kun Costume': '僵尸君猫装',
    'F Happy Outfit': '欢乐猫套装',
    'F Treasure Chest J': '宝箱J猫装',
    'F Pirate Vest J': '海盗J猫背心',
    'F Catboard': '猫咪滑板',
    'F Monqlo Shirt': '猫克罗猫衬衫',
    'F Baby Tiga Suit': '小轰龙猫套装',
    'F Postman Suit': '邮差猫制服',
    'F Zombie-kun Wear': '僵尸君猫服',
    'F Grandpaw D Guise': '危险爷爷D猫装扮',
    'F Happy Guise': '欢乐猫装扮',
    'F Dark Meowgic Robe': '黑暗猫魔法长袍',
    'F Booty Chest J': '宝藏J猫装',
    'F Buccaneer Vest J': '大海盗J猫背心',
    'F Super Catboard': '超级猫滑板',
    'F Link Tunic': '林克猫上衣',
    'F Fox Suit': '狐狸猫套装',
    'F Mario Overalls': '马力欧猫背带裤',
    'F Luigi Overalls': '路易吉猫背带裤',
    'F Resetti Guise': '复位先生猫装扮',
    'F Isabelle Guise': '西施惠猫装扮',
    'F Armor of Purrity': '纯洁猫铠甲',
    'F Chun Attire': '春丽猫服装',
    'F Fancy Blanka Wear': '布兰卡猫服',
    'F Dante Jacket': '但丁猫夹克',
    'F Mega Armor': '洛克人猫铠甲',
    'F Melodic Suit': '旋律猫套装',
    'F Sunsnug Vest': '暖阳猫背心',
    'F Barrel Body': '桶身猫装',
    'F Hot Shakalaka Duds': '热情奇面族猫装',
    'F Large Straw Raincoat': '大型草编猫雨衣',
    'F Postman Suit X': '邮差猫制服·X级',
    'F Transpurrrrter Cape': '搬运猫披风',
    'F Ultra Arcadia Robe': '终极阿卡迪亚猫长袍',
    'F Pro Dirty Hakama': '专业脏辫猫袴',
    'F Brachy Fists X': '碎龙猫拳套·X级',
    "F Felcote's Thick Coat": '菲尔科特猫厚外套',
    'F Navirou Costume': '纳比露猫装',
    'F Luna Costume': '露娜猫装',
    'F Navirou Bodysuit': '纳比露猫连体装',
    'F Luna Bodysuit': '露娜猫连体装',
    'F Navirou Makeover': '纳比露猫变装',
    'F Luna Makeover': '露娜猫变装',
    'F Retsu Kaioh Outfit': '烈海王猫套装',
    'F Danger Suit': '危险猫套装',
    'F Phoenix Jacket': '凤凰猫夹克',
    'F Korok Suit': '克洛格猫套装',
}
WEAPON_TRANSLATIONS = {
    'F Bone Wedge': '骨制猫镐',
    'F Bherna Staff': '贝鲁纳猫杖',
    'F Iron Sword': '铁制猫剑',
    'F Wood Chopper': '木制猫斧',
    'F Paw Punch': '肉球猫拳',
    'F Alta Net': '甲虫猫网',
    'F Bnaha Dagger': '飞甲虫猫匕首',
    'F Maccao Dagger': '跳狗龙猫匕首',
    'F Bulldrome Tusk': '野猪王猫獠牙',
    'F Arzuros Mace': '青熊兽猫锤',
    'F Cephalos Brush': '沙龙猫刷',
    'F Machalite Wedge': '燕雀石猫镐',
    'F Venombee Bat': '毒蜂猫棒',
    'F Gourmet Cheese': '美食猫奶酪',
    'F Moofah Cotton': '云羊鹿猫毛球',
    'F Aptonoth Meat': '草食龙猫肉骨',
    'F Fish Stick': '猫鱼串',
    'F Grilled Hammer': '烤肉猫锤',
    'F Lagombi Staff': '白兔兽猫杖',
    'F Kut-Ku Cutter': '怪鸟猫刀',
    'F Cabra Pounder': '鬼蛙猫槌',
    'F Daimyo Shears': '盾蟹猫剪刀',
    'F Ludroth Paw': '水兽猫爪',
    'F Khezu Whaccine': '白电龙猫疫苗针',
    'F Nibel Blammer': '潜口龙猫枪锤',
    'F Vprey Wedge': '蓝速龙猫楔',
    'F Edel Rod': '以太猫杖',
    'F Mosgharl Broom': '南瓜猫扫帚',
    'F Bushwhacker': '首鸣龙猫木剑',
    'F Death Stench Scythe': '死神猫镰刀',
    'F Marauder Blade': '武者猫太刀',
    'F Marauder Gavel': '武者猫战锤',
    'F Jester Parasol': '小丑猫阳伞',
    'F Rathian Rapier': '雌火龙猫细剑',
    'F Ceanataur Cutter': '镰蟹猫刀',
    'F Naja Pungi': '绞蛇龙猫排箫',
    'F Kokoto Beer': '科科特猫啤酒',
    'F Pokke Mop': '波凯猫拖把',
    'F Shroom Rod': '蘑菇猫棒',
    'F Eldora Paw': '艾尔多拉猫爪',
    'F Uragaan Iron': '爆锤龙猫铁锤',
    'F Lagia Anchor': '海龙猫锚',
    'F Astalos Spear': '电龙猫长枪',
    'F Guild Rapier': '公会猫细剑',
    'F Moofy Plush': '云羊鹿猫玩偶',
    'F Scorching Blade': '灼炎猫刃',
    'F Katzenlampe': '猫灯笼',
    'F Seregios Edge': '千刃龙猫刃',
    'F Tigrex Whammer': '轰龙猫重锤',
    'F Kirin Rumblezap': '麒麟猫雷鸣剑',
    'F Brachy Punch': '碎龙猫拳套',
    'F Le Cœur de Chat': '猫之心',
    'F Kushala Wand': '钢龙猫法杖',
    'F Genie Breath': '魔神猫吐息',
    'F Kaiser Mace': '炎王猫锤',
    'F White Felyne Husk': '白猫骸骨',
    'F Yukumo Bonito': '结云猫鲣鱼刀',
    "F Mewsurper's Peal": '猫之钟鸣',
    'F Carbalite Wedge': '灵鹤石猫镐',
    'F Barbecue': '烤肉猫叉',
    'F Fingerlicker': '吮指猫叉',
    'F Carbalite Sword': '灵鹤石猫剑',
    'F Slagtoth Leaf': '垂皮龙猫叶剑',
    'F Vprey Bayonet': '蓝速龙猫刺刀',
    'F Kecha Harrow': '奇猿狐猫耙',
    'F Bell Rod': '铃兰猫杖',
    'F Gargouille Waltz': '石像鬼猫圆舞曲',
    'F Meowtetsuken': '猫铁剑',
    'F Pounderpurr': '猫爪重锤',
    'F Slumbering Duke': '沉睡猫公爵',
    'F Queen Rapier': '女王猫细剑',
    'F Narga Shuriken': '迅龙猫手里剑',
    'F Plesioth Board': '水龙猫滑板',
    'F Lava Mace': '熔岩龙猫锤',
    'F Lulling Moofy Plush': '安眠云羊鹿猫玩偶',
    'F Kut-Ku Cackle': '怪鸟猫笑声',
    'F Bulldrome Rrrush': '野猪王猫冲锋',
    'F Mighty Shroom Rod': '强力蘑菇猫杖',
    'F D. Stench Scythe': '死神D猫镰刀',
    'F Lost Catspaw Staff': '亡国猫爪法杖',
    'F Scorched Whiskers': '焦灼猫胡须',
    'F Lightning Spear': '雷电猫枪',
    'F Ginormews Staff': '巨猫杖',
    'F Crimson Parasol': '深红猫伞',
    'F Katzenfunzel': '猫灯',
    'F Seltas Drill': '彻甲虫猫钻',
    'F Duram Axe': '尾锤龙猫斧',
    'F Golden Gadget': '黄金猫装置',
    'F Quest Book': '任务猫书',
    'F Guildcalibur': '公会猫王剑',
    'F Dirty Blade': '污秽猫刀',
    'F Meowsketeer Rapier': '三剑客猫细剑',
    'F Brachy Wallop': '碎龙猫重击锤',
    'F Le Chatphrodite': '猫之爱神',
    'F Polaris Sword': '北极星猫剑',
    'F Akantor Sword': '霸龙猫剑',
    'F Ukanlos Shovel': '崩龙猫铲',
    'F Cursed Cloud': '诅咒猫云',
    'F Escador Scythe': '煌黑龙猫镰刀',
    'F Agnaktor Lance': '炎戈龙猫长枪',
    'F Strange Hammer': '奇妙猫锤',
    'F Redhelm Mace': '红盔猫槌',
    'F Snowbaron Stick': '大雪主猫棒',
    'F Stonefist Shears': '矛碎猫剪刀',
    'F Dreadqueen Rapier': '紫毒姬猫细剑',
    'F Drilltusk Pounder': '岩穿猫槌',
    'F Silverwind Star': '白疾风猫星刃',
    'F Crystalbeard Iron': '宝缠猫铁锤',
    'F Deadeye Fan': '独眼猫扇',
    'F Dreadking Blade': '黑炎王猫刃',
    "F Thunderlord's Peal": '金雷公猫钟鸣',
    "F Thunderlord's Roar": '金雷公猫咆哮',
    'F Grimclaw Whammer': '荒钩爪猫重锤',
    'F Blazing Ashes': '烈焰猫灰烬',
    'F Ashen Whiskers': '灰烬猫胡须',
    'F Zombie-kun Gut': '僵尸君猫肠',
    'F Fairy Tail Blade': '妖精尾巴猫刃',
    'F Treasure Chalice J': '财宝J猫圣杯',
    'F Legendary Glass J': '传奇J猫杯',
    'F Greedy Hook J': '贪欲J猫钩',
    'F Monqlo Ball': '猫克罗球',
    'F Midousuji Bike': '御堂筋猫单车',
    'F Zombie-kun Stomach': '僵尸君猫胃',
    'F Grandpaw Danger': '危险爷爷猫武器',
    'F True Fairy Tail Blade': '真·妖精尾巴猫刃',
    'F Dark Meowgic Staff': '黑暗猫魔法杖',
    'F Booty Chalice J': '宝藏J猫圣杯',
    'F Avaricious Hook J': '贪财J猫钩',
    'F Wind Waker': '风之猫杖',
    'F Blaster': '爆破猫枪',
    "F Sentry's Pickaxe": '哨兵猫镐',
    "F Minder's Binder": '照料员猫封印书',
    'F Sword of Purrity': '纯洁猫剑',
    'F Chun Bracelets': '春丽猫拳套',
    'F Blanka Fish': '布兰卡猫鱼',
    'F Alastor': '阿拉斯托猫剑',
    'F Rushing Hammer': '猛冲猫锤',
    'F Melodic Baton': '旋律猫指挥棒',
    'F Fan Megaphone': '扇形猫扩音器',
    'F Giaprey Bayonet': '白速龙猫刺刀',
    'F Conga Cymbals': '桃毛兽猫钹',
    'F Barroth Mace': '土砂龙猫锤',
    'F Second Sight Lens': '千里眼猫透镜',
    'F Basarios Axe': '岩龙猫斧',
    'F Nerscylla Wedge': '影蜘蛛猫镐',
    'F Grav Bazooka': '铠龙猫火箭炮',
    'F Diablos Hammer': '角龙猫锤',
    'F Eltalite Wedge': '艾尔塔石猫镐',
    'F Deluxe BBQ': '高级烤肉猫叉',
    'F Smorgasbord': '猫咪自助餐',
    'F Eltalite Sword': '艾尔塔石猫剑',
    'F Jaggi Knife': '狗龙猫小刀',
    'F Gypceros Glare': '毒怪鸟猫凝视',
    'F Yukumo Fan': '结云猫扇',
    'F Bulldrome Rrrumble': '野猪王猫咆哮',
    'F Sacred Titan Dance': '圣巨人猫之舞',
    'F Real Catetsu Blade': '真猫铁剑',
    'F Marauder Warhammer': '武者猫战锤',
    "F Finder's Loupe": '探索者猫放大镜',
    'F Slumbering Archduke': '沉睡猫大公',
    'F Swiftblur Rapier': '疾风猫细剑',
    'F Scylla Wedge': '骸蜘蛛猫楔',
    'F Zamtrios Paw': '化鲛猫掌',
    'F Snoozy Moofy Plush': '甜睡云羊鹿猫玩偶',
    'F Mycetic Rod': '菌菇猫杖',
    'F DeathStench Scythe': '死神猫镰刀',
    'F Fine Catspaw Staff': '精致猫爪法杖',
    'F Slumbral Moofy Plush': '昏睡云羊鹿猫玩偶',
    'F Novaslice Whiskers': '新星猫胡须刀',
    "F St. Elmo's Javelin": '圣艾尔摩猫标枪',
    'F Ginormewsest Staff': '巨无霸猫杖',
    'F Crimson Sky Parasol': '绯红天空猫伞',
    "F Mewsurper's Yowl": '猫咪至尊咆哮',
    'F Katzenseele': '猫魂',
    'F Dragon Forevertones': '永恒龙吟猫笛',
    'F Pro Dirty Blade': '专业污秽猫刃',
    'F Meowsketeer Espada': '三剑客猫剑',
    'F Legend Blade': '传说猫刃',
    'F Miaownifique': '猫咪杰作',
    'F Purrlissimo': '极致呼噜猫刃',
    'F Brachydios Smash': '碎龙猫重击锤',
    'F La Venyasss': '猫之猎刃',
    'F Dragon Comet': '龙星猫彗星',
    'F Fischfleisch': '鱼肉猫剑',
    'F White Felyne Scepter': '白猫权杖',
    'F Polaris Clawsword': '北极星猫爪剑',
    'F Engraved Staff': '雕纹猫杖',
    'F Mizutsune Parasol': '泡狐龙猫伞',
    'F True Yukumo Bokken': '真·结云猫木刀',
    'F Celestial Squall': '天界猫风暴',
    'F Havoc Eye': '混沌猫眼',
    'F Fatalis Rod': '黑龙猫杖',
    'F DreadqueenRapier': '紫毒姬猫细剑',
    'F Cloaked Parasol': '隐身猫伞',
    'F Exalted Parasol': '崇高猫伞',
    'F Scratching Pole': '猫抓柱',
    'F Rending Pole': '撕裂猫柱',
    "F Thunderlord'sRoar": '金雷公猫咆哮',
    'F GrimclawWhammer': '荒钩爪猫重锤',
    'F GrimclawWhammr': '荒钩爪猫重锤',
    'F Smouldering Whiskers': '闷烧猫胡须',
    'F Searing Whiskers': '炙热猫胡须',
    'F Scarlet Virtue': '猩红猫美德',
    'F Incarnadine Greed': '绯红猫贪欲',
    'F Zephra Spear': '泽法猫长枪',
    'F Zilbolt Spear': '紫电猫长枪',
    'F Snowcap Staff': '雪峰猫杖',
    'F The Trampler': '踏破猫锤',
    'F Carnage Hammer': '屠戮猫锤',
    'F Bloodbath Hammer': '鏖魔猫锤',
    'F Cutie Moon Rod': '美少女猫月杖',
    "F Arthur's Lance": '亚瑟猫长枪',
    'F Tsumugari': '猫魂斩刀',
    'F Objection! Panel': '反对猫指示牌',
    'F Spirits Pickaxe': '精灵猫镐',
    'F Korok Branch': '克洛格猫树枝',
}
GRADE_SUFFIXES = {
    'S': '·S级', 'R': '·R级', 'X': '·X级',
    'XR': '·XR级', 'XX': '·XX级',
}

source_rows = []
for page_number, rarity_low, rarity_high in (
    ('2556', 1, 3), ('2557', 4, 7), ('2558', 8, 11),
):
    path = CACHE / f'{page_number}.html'
    if not path.exists():
        continue
    soup = BeautifulSoup(path.read_text(), 'html.parser')
    table = soup.select_one('table.t1')
    if table is None:
        continue
    for row in table.select('tr')[2:]:
        cells = row.find_all(['td', 'th'], recursive=False)
        if len(cells) == 8:
            name = cells[1].get_text(' ', strip=True)
            values = cells[2:]
        elif len(cells) == 7:
            name = cells[0].get_text(' ', strip=True)
            values = cells[1:]
        else:
            continue
        parsed = []
        for cell in values:
            match = re.search(r'[+-]?\d+', cell.get_text(' ', strip=True))
            parsed.append(int(match[0]) if match else 0)
        if len(parsed) == 6:
            source_rows.append({
                'low': rarity_low, 'high': rarity_high, 'name': name,
                'stats': tuple(parsed), 'page': page_number,
            })

database_rows = []
for row in DB.execute(
    'select i._id,i.name,i.rarity,p.defense,p.fire_res,p.water_res,'
    'p.thunder_res,p.ice_res,p.dragon_res '
    'from palico_armor p join items i on i._id=p._id'
):
    stats = tuple(row[key] for key in (
        'defense', 'fire_res', 'water_res', 'thunder_res', 'ice_res', 'dragon_res'
    ))
    database_rows.append((row, stats))

source_lookup = {}
for row in source_rows:
    key = (row['low'], row['high'], row['stats'])
    source_lookup.setdefault(key, []).append(row)
database_lookup = {}
for row, stats in database_rows:
    key = (row['rarity'], stats)
    database_lookup.setdefault(key, []).append(row)

def translation_for(english_name):
    match = re.fullmatch(r'(.+?) (S|R|X|XR|XX)', english_name)
    if match and match[1] in NAME_TRANSLATIONS:
        return NAME_TRANSLATIONS[match[1]] + GRADE_SUFFIXES[match[2]]
    return NAME_TRANSLATIONS.get(english_name)

def weapon_translation_for(english_name):
    match = re.fullmatch(r'(.+?) (S|R|X|XR|XX)', english_name)
    if match and match[1] in WEAPON_TRANSLATIONS:
        return WEAPON_TRANSLATIONS[match[1]] + GRADE_SUFFIXES[match[2]]
    return WEAPON_TRANSLATIONS.get(english_name)

added = 0
for row, stats in database_rows:
    translated = translation_for(row['name'])
    if not translated:
        continue
    existing = OUT.get('items_by_id', {}).get(str(row['_id']))
    if existing:
        continue
    source_matches = [
        source
        for (low, high, source_stats), candidates in source_lookup.items()
        if low <= row['rarity'] <= high and source_stats == stats
        for source in candidates
    ]
    db_matches = database_lookup[(row['rarity'], stats)]
    if len(source_matches) != 1 or len(db_matches) != 1:
        item_id = str(row['_id'])
        OUT.setdefault('items_by_id', {})[item_id] = translated
        EVIDENCE.setdefault('items', {}).setdefault(item_id, []).append({
            'name': translated,
            'english': row['name'],
            'method': 'reviewed direct translation of exact English Felyne armor name',
        })
        added += 1
        continue
    source = source_matches[0]
    if not re.search(r'[\u3400-\u9fff]', translated):
        continue
    item_id = str(row['_id'])
    OUT.setdefault('items_by_id', {})[item_id] = translated
    EVIDENCE.setdefault('items', {}).setdefault(item_id, []).append({
        'name': translated,
        'english': row['name'],
        'method': 'unique Felyne armor rarity band and defense/resistance fingerprint; reviewed Chinese translation',
        'source': f"jestar719/mhgu:app/src/main/assets/mhxx/data/{source['page']}.html",
        'source_name': source['name'],
        'stats': list(stats),
    })
    added += 1

base = json.loads((RES / 'zh.json').read_text())
old = json.loads((RES / 'localization.json').read_text())
weapon_added = 0
for row in DB.execute(
    'select i._id,i.name from palico_weapons p join items i on i._id=p._id'
):
    translated = weapon_translation_for(row['name'])
    if not translated or str(row['_id']) in OUT.get('items_by_id', {}):
        continue
    if row['name'] in base.get('items', {}) or str(row['_id']) in old.get('items_by_id', {}):
        continue
    item_id = str(row['_id'])
    OUT.setdefault('items_by_id', {})[item_id] = translated
    EVIDENCE.setdefault('items', {}).setdefault(item_id, []).append({
        'name': translated,
        'english': row['name'],
        'method': 'reviewed direct translation of exact English Felyne weapon name',
    })
    weapon_added += 1

(RES / 'linked-localization.json').write_text(
    json.dumps(OUT, ensure_ascii=False, indent=2) + '\n'
)
(ROOT / 'LINKED-LOCALIZATION-SOURCES.json').write_text(
    json.dumps(EVIDENCE, ensure_ascii=False, indent=2) + '\n'
)
print(f'Palico armor names imported: {added}; weapon names imported: {weapon_added}')
