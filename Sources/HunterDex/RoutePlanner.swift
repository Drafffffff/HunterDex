import Foundation

struct RouteRequirement: Identifiable, Sendable {
    let entry: Entry
    var quantity: Int
    let points: Bool
    var id: Destination { entry.id }
}
struct WeaponRoute: Sendable {
    let start: Entry
    let target: Entry
    let steps: [Entry]
    let cost: Int
    let materials: [RouteRequirement]
}
extension DexDatabase {
    func route(from start: Int, to target: Int) throws -> WeaponRoute {
        guard let first = index[Destination(category: .weapons, id: start)], let last = index[Destination(category: .weapons, id: target)] else { throw DexError.message("路线端点不是有效武器。") }
        var path: [Int] = []; var seen: Set<Int> = []; var current = target
        while current != start {
            guard seen.insert(current).inserted, let weapon = weapons[current], let parent = weapon.parent else { throw DexError.message("目标不在起点的派生路线内。请选择起点的后续强化。") }
            path.append(current); current = parent
        }
        var requirements: [Int: RouteRequirement] = [:]; var cost = 0
        for id in path {
            cost += weapons[id]?.upgradeCost ?? 0
            let rows = try query("SELECT i._id,i.type,c.quantity FROM components c JOIN items i ON i._id=c.component_item_id WHERE c.created_item_id=? AND c.type='Improve'", [id])
            guard !rows.isEmpty else { throw DexError.message("路线中有未收录强化配方的节点，无法给出完整累计需求。") }
            for row in rows {
                let itemID = row.int("_id")
                if row.str("type") == "Weapon" && itemID == weapons[id]?.parent { continue }
                if requirements[itemID] != nil { requirements[itemID]!.quantity += row.int("quantity") }
                else if let entry = index[itemDestination(row)] { requirements[itemID] = RouteRequirement(entry: entry, quantity: row.int("quantity"), points: row.str("type") == "Materials") }
                else { throw DexError.message("路线中存在未收录的材料。") }
            }
        }
        return WeaponRoute(start: first, target: last, steps: path.reversed().compactMap { index[Destination(category: .weapons, id: $0)] }, cost: cost, materials: requirements.values.sorted { $0.entry.id.id < $1.entry.id.id })
    }
}
extension DetailRepository {
    func route(from start: Int, to target: Int) throws -> WeaponRoute {
        if database == nil { database = try DexDatabase() }
        return try database!.route(from: start, to: target)
    }
}
