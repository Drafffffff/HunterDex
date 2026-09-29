import Foundation

struct SkillPoint: Identifiable, Sendable {
    let id: Int
    let name: String
    let points: Int
    var effects: [SkillEffect] = []
}
struct SkillEffect: Sendable { let name: String; let threshold: Int; let description: String }
struct WeaponInfo: Sendable {
    let id: Int
    let parent: Int?
    let type: String
    let attack: Int
    let affinity: String
    let slots: Int
    let elements: String
    let sharpness: [[Int]]
    let special: String
    let creationCost: Int
    let upgradeCost: Int
    var ranged: Bool { ["Bow", "Light Bowgun", "Heavy Bowgun"].contains(type) }
}
struct ArmorInfo: Sendable {
    let id: Int
    let slot: String
    let defense: Int
    let maximum: Int
    let slots: Int
    let resistances: [Int]
    let hunter: Int
    let gender: Int
    let family: Int
    let skills: [SkillPoint]
    var hunterLabel: String { [0: "剑士", 1: "射手", 2: "通用"][hunter] ?? "未标明" }
    var genderLabel: String { [0: "男性", 1: "女性", 2: "不限性别"][gender] ?? "未标明" }
    var summary: String { skills.map { "\($0.name) \(signed($0.points))" }.joined(separator: " · ") }
}
func signed(_ value: Int) -> String { value > 0 ? "+\(value)" : "\(value)" }

extension DexDatabase {
    static let weaponTypes = ["Great Sword", "Long Sword", "Sword and Shield", "Dual Blades", "Hammer", "Hunting Horn", "Lance", "Gunlance", "Switch Axe", "Charge Blade", "Insect Glaive", "Bow", "Light Bowgun", "Heavy Bowgun"]
    func loadEquipment() throws {
        for row in try query("SELECT * FROM weapons") {
            let elements = [("element", "element_attack"), ("element_2", "element_2_attack")].compactMap { key, value -> String? in
                guard !row.str(key).isEmpty else { return nil }
                return "\(zh("elements", row.str(key))) \(row.str(value))"
            }.joined(separator: " / ")
            let special = [row.str("shelling_type"), row.str("phial"), row.str("horn_notes"), row.str("charges"), row.str("rapid_fire")].filter { !$0.isEmpty }.joined(separator: " · ")
            weapons[row.int("_id")] = WeaponInfo(id: row.int("_id"), parent: row.int("parent_id") > 0 ? row.int("parent_id") : nil, type: row.str("wtype"), attack: row.int("attack"), affinity: row.str("affinity"), slots: row.int("num_slots"), elements: elements, sharpness: row.str("sharpness").split(separator: " ").map { $0.split(separator: ".").compactMap { Int($0) } }, special: special, creationCost: row.int("creation_cost"), upgradeCost: row.int("upgrade_cost"))
        }
        var effects: [Int: [SkillEffect]] = [:]
        for row in try query("SELECT * FROM skills ORDER BY required_skill_tree_points") {
            effects[row.int("skill_tree_id"), default: []].append(SkillEffect(name: zh("skill_effects", row.str("name")), threshold: row.int("required_skill_tree_points"), description: zh("skill_descriptions", row.str("name"))))
        }
        var points: [Int: [SkillPoint]] = [:]
        for row in try query("SELECT x.*,t.name FROM item_to_skill_tree x JOIN skill_trees t ON t._id=x.skill_tree_id ORDER BY point_value DESC") {
            points[row.int("item_id"), default: []].append(SkillPoint(id: row.int("skill_tree_id"), name: zh("skill_trees", row.str("name")), points: row.int("point_value"), effects: effects[row.int("skill_tree_id")] ?? []))
        }
        for row in try query("SELECT * FROM armor") {
            armors[row.int("_id")] = ArmorInfo(id: row.int("_id"), slot: row.str("slot"), defense: row.int("defense"), maximum: row.int("max_defense"), slots: row.int("num_slots"), resistances: ["fire_res", "water_res", "thunder_res", "ice_res", "dragon_res"].map { row.int($0) }, hunter: row.int("hunter_type"), gender: row.int("gender"), family: row.int("family"), skills: points[row.int("_id")] ?? [])
        }
        for row in try query("SELECT * FROM armor_families") {
            armorFamilies[row.int("_id")] = ["head_id", "body_id", "arms_id", "waist_id", "legs_id"].map { row.int($0) }.filter { armors[$0] != nil }
        }
    }
}
