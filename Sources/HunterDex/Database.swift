import Foundation
import CSQLite

enum Category: String, CaseIterable, Identifiable, Codable, Sendable {
    case weapons, armor, items, monsters, quests, favorites
    var id: String { rawValue }
    var title: String {
        switch self {
        case .weapons: "武器"
        case .armor: "防具"
        case .items: "道具与素材"
        case .monsters: "怪物"
        case .quests: "任务"
        case .favorites: "我的收藏"
        }
    }
    var icon: String {
        switch self {
        case .weapons: "hammer"
        case .armor: "shield.lefthalf.filled"
        case .items: "shippingbox"
        case .monsters: "pawprint"
        case .quests: "scroll"
        case .favorites: "star"
        }
    }
}

struct Destination: Hashable, Codable, Sendable {
    let category: Category
    let id: Int
    var key: String { "\(category.rawValue):\(id)" }
}

typealias Row = [String: String]
extension Dictionary where Key == String, Value == String {
    func str(_ key: String) -> String { self[key] ?? "" }
    func int(_ key: String) -> Int { Int(str(key)) ?? 0 }
}

struct Entry: Identifiable, Sendable {
    let destination: Destination
    let name: String
    let english: String
    let subtitle: String
    let rarity: Int
    let value: Int
    let filter: String
    let final: Bool
    var iconName: String = ""
    var iconColor: Int = 0
    var portraitName: String = ""
    var id: Destination { destination }
    var searchText: String { "\(name) \(english) \(subtitle) \(destination.id)" }
}

struct DetailLink: Identifiable, Sendable {
    var id: String { "\(destination?.key ?? "text")|\(title)|\(subtitle)|\(trailing)|\(depth)" }
    let title: String
    var subtitle: String = ""
    var trailing: String = ""
    var destination: Destination? = nil
    var depth: Int = 0
}
struct DetailSection: Identifiable, Sendable {
    var id: String { title }
    let title: String
    var note: String = ""
    let rows: [DetailLink]
}
struct Metric: Identifiable, Sendable {
    var id: String { label }
    let label: String
    let value: String
}
struct ItemDetail: Sendable {
    let entry: Entry
    var description: String = ""
    var metrics: [Metric] = []
    var sharpness: [[Int]] = []
    var tree: [DetailLink] = []
    var sections: [DetailSection] = []
}

enum DexError: LocalizedError {
    case message(String)
    var errorDescription: String? {
        switch self { case .message(let text): text }
    }
}

final class DexDatabase {
    private var db: OpaquePointer?
    private let translations: [String: [String: String]]
    private let descriptionTranslations: [String: String]
    private let portraits: [String: String]
    var weapons: [Int: WeaponInfo] = [:]
    var armors: [Int: ArmorInfo] = [:]
    var armorFamilies: [Int: [Int]] = [:]
    private(set) var entries: [Entry] = []
    private(set) var index: [Destination: Entry] = [:]

    init() throws {
        let packagedBundle = Bundle.main.resourceURL.flatMap { Bundle(url: $0.appendingPathComponent("HunterDex_HunterDex.bundle")) }
        if Bundle.main.bundleURL.pathExtension == "app" && packagedBundle == nil {
            throw DexError.message("应用中的离线资源不完整，请重新构建应用。")
        }
        let resources = packagedBundle ?? Bundle.module
        guard let url = resources.url(forResource: "mhgu", withExtension: "db"),
              let zhURL = resources.url(forResource: "zh", withExtension: "json") else {
            throw DexError.message("找不到离线数据库，请重新构建完整的应用。")
        }
        let json = try JSONSerialization.jsonObject(with: Data(contentsOf: zhURL)) as? [String: Any] ?? [:]
        var merged = json.compactMapValues { $0 as? [String: String] }
        guard let localizationURL = resources.url(forResource: "localization", withExtension: "json"),
              let artworkURL = resources.url(forResource: "artwork", withExtension: "json") else {
            throw DexError.message("缺少中文或图片索引，请重新构建完整的应用。")
        }
        guard let descriptionURL = resources.url(forResource: "description-localization", withExtension: "json") else {
            throw DexError.message("缺少中文说明词典，请重新构建完整的应用。")
        }
        let supplement = try JSONDecoder().decode([String: [String: String]].self, from: Data(contentsOf: localizationURL))
        for (group, values) in supplement { merged[group, default: [:]].merge(values) { _, newer in newer } }
        if let linkedURL = resources.url(forResource: "linked-localization", withExtension: "json") {
            let linked = try JSONDecoder().decode([String: [String: String]].self, from: Data(contentsOf: linkedURL))
            for (group, values) in linked { merged[group, default: [:]].merge(values) { _, newer in newer } }
        }
        translations = merged
        descriptionTranslations = try JSONDecoder().decode([String: String].self, from: Data(contentsOf: descriptionURL))
        portraits = try JSONDecoder().decode([String: [String: String]].self, from: Data(contentsOf: artworkURL))["portraits"] ?? [:]
        guard sqlite3_open_v2(url.path, &db, SQLITE_OPEN_READONLY, nil) == SQLITE_OK else {
            let message = db.map { String(cString: sqlite3_errmsg($0)) } ?? "Unknown error"
            if let db { sqlite3_close(db) }
            db = nil
            throw DexError.message("无法打开数据库：\(message)")
        }
        do { try loadCatalog(); try loadEquipment() }
        catch { sqlite3_close(db); db = nil; throw error }
    }
    deinit { sqlite3_close(db) }

    func query(_ sql: String, _ parameters: [Int] = []) throws -> [Row] {
        var statement: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw DexError.message(String(cString: sqlite3_errmsg(db)))
        }
        defer { sqlite3_finalize(statement) }
        for (offset, value) in parameters.enumerated() {
            sqlite3_bind_int64(statement, Int32(offset + 1), Int64(value))
        }
        var rows: [Row] = []
        var result = sqlite3_step(statement)
        while result == SQLITE_ROW {
            var row: Row = [:]
            for i in 0..<sqlite3_column_count(statement) {
                let key = String(cString: sqlite3_column_name(statement, i))
                if let value = sqlite3_column_text(statement, i) { row[key] = String(cString: value) }
            }
            rows.append(row)
            result = sqlite3_step(statement)
        }
        guard result == SQLITE_DONE else { throw DexError.message(String(cString: sqlite3_errmsg(db))) }
        return rows
    }

    func zh(_ group: String, _ name: String) -> String { translations[group]?[name] ?? name }
    func condition(_ name: String) -> String {
        for (english, chinese) in (translations["conditions"] ?? [:]).sorted(by: { $0.key.count > $1.key.count }) {
            if name.hasPrefix(english) { return chinese + name.dropFirst(english.count) }
        }
        return name
    }
    func itemName(_ row: Row) -> String {
        if let name = translations["items_by_id"]?[row.str("_id")] { return name }
        if row.str("type") == "Decoration" { return zh("decorations", row.str("_id")) == row.str("_id") ? row.str("name") : zh("decorations", row.str("_id")) }
        return zh("items", row.str("name"))
    }
    func itemDestination(_ row: Row) -> Destination {
        let kind: Category = row.str("type") == "Weapon" ? .weapons : row.str("type") == "Armor" ? .armor : .items
        return Destination(category: kind, id: row.int("_id"))
    }
    func itemLink(_ row: Row, subtitle: String = "", trailing: String = "") -> DetailLink {
        DetailLink(title: itemName(row), subtitle: subtitle, trailing: trailing, destination: itemDestination(row))
    }
    func questName(_ row: Row) -> String { translations["quests_by_id"]?[row.str("_id")] ?? zh("quests", row.str("name")) }
    func questStage(_ row: Row) -> String {
        let stars = row.int("stars")
        if row.str("hub") == "Permit" { return stars == 16 ? "超特殊许可" : stars > 10 ? "G\(stars - 10)" : "Lv.\(stars)" }
        return row.str("rank") == "G" && stars > 10 ? "G★\(stars - 10)" : "★\(stars)"
    }
    func questLink(_ row: Row, trailing: String = "") -> DetailLink {
        DetailLink(title: questName(row), subtitle: "\(zh("hubs", row.str("hub"))) · \(zh("ranks", row.str("rank"))) · \(questStage(row))", trailing: trailing, destination: Destination(category: .quests, id: row.int("_id")))
    }

    private func loadCatalog() throws {
        for row in try query("SELECT i._id,i.name,i.rarity,i.icon_name,i.icon_color,w.wtype,w.attack,w.final FROM weapons w JOIN items i ON i._id=w._id ORDER BY i._id") {
            entries.append(Entry(destination: Destination(category: .weapons, id: row.int("_id")), name: itemName(row), english: row.str("name"), subtitle: zh("weapon_types", row.str("wtype")), rarity: row.int("rarity"), value: row.int("attack"), filter: row.str("wtype"), final: row.int("final") == 1, iconName: row.str("icon_name"), iconColor: row.int("icon_color")))
        }
        for row in try query("SELECT i._id,i.name,i.rarity,i.icon_name,i.icon_color,a.slot,a.defense FROM armor a JOIN items i ON i._id=a._id ORDER BY i._id") {
            entries.append(Entry(destination: Destination(category: .armor, id: row.int("_id")), name: itemName(row), english: row.str("name"), subtitle: Self.slotName(row.str("slot")), rarity: row.int("rarity"), value: row.int("defense"), filter: row.str("slot"), final: false, iconName: row.str("icon_name"), iconColor: row.int("icon_color")))
        }
        for row in try query("SELECT _id,name,type,rarity,icon_name,icon_color FROM items WHERE type NOT IN ('Weapon','Armor') ORDER BY _id") {
            entries.append(Entry(destination: Destination(category: .items, id: row.int("_id")), name: itemName(row), english: row.str("name"), subtitle: row.str("type").isEmpty ? "道具 / 素材" : zh("item_types", row.str("type")), rarity: row.int("rarity"), value: 0, filter: row.str("type").isEmpty ? "Item" : row.str("type"), final: false, iconName: row.str("icon_name"), iconColor: row.int("icon_color")))
        }
        for row in try query("SELECT _id,name,goal,hub,rank,stars FROM quests ORDER BY sort_order,_id") {
            entries.append(Entry(destination: Destination(category: .quests, id: row.int("_id")), name: questName(row), english: row.str("name"), subtitle: "\(zh("hubs", row.str("hub"))) · \(questStage(row)) · \(zh("goals", row.str("goal")))", rarity: 0, value: row.int("stars"), filter: row.str("rank"), final: false, iconName: row.str("icon_name"), iconColor: row.int("icon_color")))
        }
        for row in try query("SELECT _id,name,class,icon_name FROM monsters ORDER BY _id") {
            entries.append(Entry(destination: Destination(category: .monsters, id: row.int("_id")), name: zh("monsters", row.str("name")), english: row.str("name"), subtitle: "怪物资料", rarity: 0, value: 0, filter: "", final: false, iconName: row.str("icon_name"), iconColor: row.int("icon_color"), portraitName: portraits[row.str("_id")] ?? ""))
        }
        index = Dictionary(uniqueKeysWithValues: entries.map { ($0.destination, $0) })
    }

    static func slotName(_ slot: String) -> String {
        ["Head": "头部", "Body": "胴部", "Arms": "腕部", "Waist": "腰部", "Legs": "脚部"][slot] ?? slot
    }

    func detail(for destination: Destination) throws -> ItemDetail {
        guard let entry = index[destination] else { throw DexError.message("数据库中没有这个条目。") }
        var detail = ItemDetail(entry: entry)
        switch destination.category {
        case .weapons, .armor, .items:
            guard let row = try query("SELECT * FROM items WHERE _id=?", [destination.id]).first else { throw DexError.message("物品记录缺失。") }
            let sourceDescription = row.str("description")
            detail.description = descriptionTranslations[sourceDescription] ?? sourceDescription
            if destination.category == .weapons {
                let weapon = try query("SELECT * FROM weapons WHERE _id=?", [destination.id]).first ?? [:]
                detail.metrics = [Metric(label: "攻击力", value: weapon.str("attack")), Metric(label: "会心率", value: weapon.str("affinity") + "%"), Metric(label: "插槽", value: slots(weapon.int("num_slots"))), Metric(label: "稀有度", value: "R\(entry.rarity)")]
                var attributes: [DetailLink] = []
                for (name, value) in [("element", "element_attack"), ("element_2", "element_2_attack"), ("awaken", "awaken_attack")] where !weapon.str(name).isEmpty {
                    attributes.append(DetailLink(title: name == "awaken" ? "觉醒属性" : "属性", trailing: "\(zh("elements", weapon.str(name))) \(weapon.str(value))"))
                }
                for (key, label) in [("defense", "防御加成"), ("phial", "瓶类型"), ("shelling_type", "炮击"), ("horn_notes", "音符"), ("charges", "蓄力"), ("coatings", "弓瓶"), ("recoil", "反动"), ("reload_speed", "装填速度"), ("deviation", "偏移"), ("creation_cost", "生产费用"), ("upgrade_cost", "强化费用")] where !weapon.str(key).isEmpty && weapon.str(key) != "0" {
                    attributes.append(DetailLink(title: label, trailing: weapon.str(key) + (key.hasSuffix("cost") ? " z" : "")))
                }
                if !attributes.isEmpty { detail.sections.append(DetailSection(title: "武器特性", rows: attributes)) }
                detail.sharpness = weapon.str("sharpness").split(separator: " ").map { $0.split(separator: ".").compactMap { Int($0) } }
                detail.tree = try weaponTree(destination.id)
            } else if destination.category == .armor {
                let armor = try query("SELECT * FROM armor WHERE _id=?", [destination.id]).first ?? [:]
                detail.metrics = [Metric(label: "基础防御", value: armor.str("defense")), Metric(label: "最大防御", value: armor.str("max_defense")), Metric(label: "插槽", value: slots(armor.int("num_slots"))), Metric(label: "稀有度", value: "R\(entry.rarity)")]
                detail.sections.append(DetailSection(title: "属性耐性", rows: [("fire_res", "火"), ("water_res", "水"), ("thunder_res", "雷"), ("ice_res", "冰"), ("dragon_res", "龙")].map { DetailLink(title: $0.1, trailing: armor.str($0.0)) }))
            } else {
                detail.metrics = [Metric(label: "稀有度", value: "R\(entry.rarity)"), Metric(label: "携带上限", value: row.str("carry_capacity")), Metric(label: "卖价", value: row.str("sell") + " z")]
            }
            let skills = try query("SELECT t.name,x.point_value FROM item_to_skill_tree x JOIN skill_trees t ON t._id=x.skill_tree_id WHERE x.item_id=? ORDER BY x.point_value DESC", [destination.id])
            if !skills.isEmpty {
                detail.sections.append(DetailSection(title: "技能点", rows: skills.map { DetailLink(title: zh("skill_trees", $0.str("name")), trailing: String(format: "%+d", $0.int("point_value"))) }))
            }
            let components = try query("SELECT i._id,i.name,i.type,c.quantity,c.type AS recipe FROM components c JOIN items i ON i._id=c.component_item_id WHERE c.created_item_id=? ORDER BY c.type,c._id", [destination.id]).filter { !(destination.category == .weapons && $0.str("recipe") == "Improve" && $0.int("_id") == weapons[destination.id]?.parent) }
            for recipe in Set(components.map { $0.str("recipe") }).sorted() {
                detail.sections.append(DetailSection(title: ["Create": "生产素材", "Improve": "强化素材", "Create B": "生产素材 · 路线 B"][recipe] ?? recipe, rows: components.filter { $0.str("recipe") == recipe }.map { itemLink($0, trailing: $0.str("type") == "Materials" ? "\($0.int("quantity")) 点" : "×\($0.int("quantity"))") }))
            }
            if destination.category == .items { try addSources(to: &detail, id: destination.id) }
        case .quests:
            try questDetail(&detail, id: destination.id)
        case .monsters:
            try monsterDetail(&detail, id: destination.id)
        case .favorites: break
        }
        return detail
    }

    private func slots(_ count: Int) -> String { String(repeating: "●", count: max(0, min(3, count))) + String(repeating: "○", count: max(0, 3 - count)) }

    func weaponTree(_ id: Int) throws -> [DetailLink] {
        let ancestors = try query("""
            WITH RECURSIVE ancestors(id,parent_id,depth) AS (
              SELECT _id,parent_id,0 FROM weapons WHERE _id=?
              UNION ALL SELECT w._id,w.parent_id,a.depth+1 FROM weapons w JOIN ancestors a ON w._id=a.parent_id WHERE a.depth<40
            ) SELECT id FROM ancestors ORDER BY depth DESC LIMIT 1
            """, [id])
        guard let root = ancestors.first?.int("id") else { return [] }
        return try query("""
            WITH RECURSIVE tree(id,depth,path) AS (
              SELECT _id,0,printf('%010d',_id) FROM weapons WHERE _id=?
              UNION ALL SELECT w._id,t.depth+1,t.path||'/'||printf('%010d',w._id) FROM weapons w JOIN tree t ON w.parent_id=t.id WHERE t.depth<40
            ) SELECT i._id,i.name,i.type,w.attack,w.final,t.depth FROM tree t JOIN items i ON i._id=t.id JOIN weapons w ON w._id=t.id ORDER BY t.path
            """, [root]).map { row in
                DetailLink(title: itemName(row), subtitle: row.int("final") == 1 ? "最终强化" : "", trailing: "\(row.int("attack"))", destination: Destination(category: .weapons, id: row.int("_id")), depth: row.int("depth"))
            }
    }

    private func addSources(to detail: inout ItemDetail, id: Int) throws {
        let pointMaterials = try query("SELECT i._id,i.name,i.type,m.amount FROM item_to_material m JOIN items i ON i._id=m.item_id WHERE m.material_item_id=? ORDER BY m.amount DESC,i._id", [id])
        if !pointMaterials.isEmpty {
            detail.sections.append(DetailSection(title: "可用素材", note: "这是一类素材的所需点数，可用下列素材抵扣。", rows: pointMaterials.map { itemLink($0, trailing: "\($0.int("amount")) 点 / 个") }))
        }
        let pointCategories = try query("SELECT i._id,i.name,i.type,m.amount FROM item_to_material m JOIN items i ON i._id=m.material_item_id WHERE m.item_id=? ORDER BY i._id", [id])
        if !pointCategories.isEmpty {
            detail.sections.append(DetailSection(title: "可计入素材类别", rows: pointCategories.map { itemLink($0, trailing: "\($0.int("amount")) 点 / 个") }))
        }
        let hunting = try query("SELECT m._id,m.name,h.condition,h.rank,h.stack_size,h.percentage FROM hunting_rewards h JOIN monsters m ON m._id=h.monster_id WHERE h.item_id=? ORDER BY h.percentage DESC,m._id,h.rank", [id])
        if !hunting.isEmpty {
            detail.sections.append(DetailSection(title: "狩猎获取", rows: hunting.map { DetailLink(title: zh("monsters", $0.str("name")), subtitle: "\(zh("ranks", $0.str("rank"))) · \(condition($0.str("condition"))) · ×\($0.int("stack_size"))", trailing: "\($0.int("percentage"))%", destination: Destination(category: .monsters, id: $0.int("_id"))) }))
        }
        let quests = try query("SELECT q._id,q.name,q.hub,q.rank,q.stars,r.percentage,r.stack_size,r.reward_slot FROM quest_rewards r JOIN quests q ON q._id=r.quest_id WHERE r.item_id=? ORDER BY r.percentage DESC,q._id,r.reward_slot", [id])
        if !quests.isEmpty {
            detail.sections.append(DetailSection(title: "任务报酬", note: "概率按各报酬栏分别展示，不代表整场任务的获取概率。", rows: quests.map { row in
                var link = questLink(row, trailing: "\(row.int("percentage"))%")
                link.subtitle += " · \(row.str("reward_slot")) 栏 · ×\(row.int("stack_size"))"
                return link
            }))
        }
        let gathering = try query("SELECT l.name,g.area,g.site,g.rank,g.quantity,g.percentage,g.rare,g.fixed,g.group_num FROM gathering g JOIN locations l ON l._id=g.location_id WHERE g.item_id=? ORDER BY g.percentage DESC,l._id,g.area", [id])
        if !gathering.isEmpty {
            detail.sections.append(DetailSection(title: "地图采集", rows: gathering.map { row in
                let site = ["Mining": "采矿", "Bug": "捕虫", "Fish": "钓鱼", "Plant": "采集", "Bone": "骨堆"][row.str("site")] ?? row.str("site")
                return DetailLink(title: zh("locations", row.str("name")), subtitle: "\(zh("ranks", row.str("rank"))) · 区域 \(row.str("area")) · \(site) · 组 \(row.str("group_num"))" + (row.int("rare") != 0 ? " · 稀有点" : ""), trailing: "\(row.int("percentage"))%")
            }))
        }
        let uses = try query("SELECT i._id,i.name,i.type,c.quantity,c.type AS recipe FROM components c JOIN items i ON i._id=c.created_item_id WHERE c.component_item_id=? ORDER BY i.type,i._id,c.type", [id])
        if !uses.isEmpty {
            detail.sections.append(DetailSection(title: "用于制作", rows: uses.map { itemLink($0, subtitle: ["Create": "生产", "Improve": "强化", "Create B": "生产 B"][$0.str("recipe")] ?? $0.str("recipe"), trailing: "×\($0.int("quantity"))") }))
        }
    }

    private func questDetail(_ detail: inout ItemDetail, id: Int) throws {
        let row = try query("SELECT q.*,l.name AS location FROM quests q LEFT JOIN locations l ON l._id=q.location_id WHERE q._id=?", [id]).first ?? [:]
        detail.description = zh("goals", row.str("goal"))
        detail.metrics = [Metric(label: "星级", value: questStage(row)), Metric(label: "限制时间", value: "\(row.int("time_limit")) 分"), Metric(label: "报酬金", value: "\(row.int("reward")) z"), Metric(label: "契约金", value: "\(row.int("fee")) z")]
        var info = [DetailLink(title: "狩猎地图", trailing: zh("locations", row.str("location"))), DetailLink(title: "任务等级", trailing: zh("ranks", row.str("rank")))]
        if !row.str("sub_goal").isEmpty { info.append(DetailLink(title: "副任务", subtitle: zh("goals", row.str("sub_goal")))) }
        detail.sections.append(DetailSection(title: "任务信息", rows: info))
        let monsters = try query("SELECT m._id,m.name FROM monster_to_quest x JOIN monsters m ON m._id=x.monster_id WHERE x.quest_id=?", [id])
        if !monsters.isEmpty { detail.sections.append(DetailSection(title: "出现怪物", rows: monsters.map { DetailLink(title: zh("monsters", $0.str("name")), destination: Destination(category: .monsters, id: $0.int("_id"))) })) }
        let rewards = try query("SELECT i._id,i.name,i.type,r.percentage,r.stack_size,r.reward_slot FROM quest_rewards r JOIN items i ON i._id=r.item_id WHERE r.quest_id=? ORDER BY r.reward_slot,r.percentage DESC", [id])
        for slot in Set(rewards.map { $0.str("reward_slot") }).sorted() {
            detail.sections.append(DetailSection(title: "报酬 · \(slot) 栏", note: "各报酬栏独立计算。", rows: rewards.filter { $0.str("reward_slot") == slot }.map { itemLink($0, subtitle: "×\($0.int("stack_size"))", trailing: "\($0.int("percentage"))%") }))
        }
    }

    private func monsterDetail(_ detail: inout ItemDetail, id: Int) throws {
        detail.description = "查看属性弱点、狩猎报酬与出现任务。掉落条件保留原数据库中的等级区间。"
        let weaknesses = try query("SELECT * FROM monster_weakness WHERE monster_id=?", [id])
        for row in weaknesses {
            detail.sections.append(DetailSection(title: "属性弱点 · \(condition(row.str("state")))", note: "数据库弱点评分，数值越高越弱；不是部位肉质。", rows: [("fire", "火"), ("water", "水"), ("thunder", "雷"), ("ice", "冰"), ("dragon", "龙")].map { DetailLink(title: $0.1, trailing: row.str($0.0)) }))
        }
        let drops = try query("SELECT i._id,i.name,i.type,h.rank,h.condition,h.stack_size,h.percentage FROM hunting_rewards h JOIN items i ON i._id=h.item_id WHERE h.monster_id=? ORDER BY h.rank,h.condition,h.percentage DESC", [id])
        if !drops.isEmpty { detail.sections.append(DetailSection(title: "狩猎报酬", rows: drops.map { itemLink($0, subtitle: "\(zh("ranks", $0.str("rank"))) · \(condition($0.str("condition"))) · ×\($0.int("stack_size"))", trailing: "\($0.int("percentage"))%") })) }
        let quests = try query("SELECT q._id,q.name,q.hub,q.rank,q.stars FROM monster_to_quest x JOIN quests q ON q._id=x.quest_id WHERE x.monster_id=? ORDER BY q.stars,q._id", [id])
        if !quests.isEmpty { detail.sections.append(DetailSection(title: "出现任务", rows: quests.map { questLink($0) })) }
    }
}
