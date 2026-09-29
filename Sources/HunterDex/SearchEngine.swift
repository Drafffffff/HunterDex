import Foundation

struct SearchRequest: Sendable {
    var category: Category
    var text: String
    var scope: String
    var finalOnly: Bool
    var sort: String
    var hunter: Int
    var favorites: Set<Destination>
    var element: String = "all"
    var rarity: Int = 0
}
struct SearchRecord: Sendable {
    let entry: Entry
    let text: String
    let name: String
    let hunter: Int
    let nameOrder: Int
    let elements: String
}
actor SearchEngine {
    private let groups: [Category: [SearchRecord]]
    init(entries: [Entry], armors: [Int: ArmorInfo], weapons: [Int: WeaponInfo] = [:]) {
        let order = Dictionary(uniqueKeysWithValues: entries.sorted { $0.name.localizedStandardCompare($1.name) == .orderedAscending }.enumerated().map { ($0.element.id, $0.offset) })
        groups = Dictionary(grouping: entries.map { entry in
            SearchRecord(entry: entry, text: Self.normalize(entry.searchText + " " + (armors[entry.id.id]?.summary ?? "")), name: Self.normalize(entry.name), hunter: armors[entry.id.id]?.hunter ?? 2, nameOrder: order[entry.id] ?? 0, elements: weapons[entry.id.id]?.elements ?? "")
        }, by: { $0.entry.destination.category })
    }
    nonisolated static func normalize(_ text: String) -> String {
        text.folding(options: [.caseInsensitive, .diacriticInsensitive, .widthInsensitive], locale: Locale(identifier: "zh_CN")).lowercased()
    }
    func search(_ request: SearchRequest) -> [Entry] {
        let terms = Self.normalize(request.text).split(whereSeparator: { $0.isWhitespace }).map(String.init)
        let candidates = request.category == .favorites ? groups.values.flatMap { $0 } : groups[request.category] ?? []
        var result: [SearchRecord] = []
        for (offset, record) in candidates.enumerated() {
            if offset % 128 == 0 && Task.isCancelled { return [] }
            let entry = record.entry
            guard request.category != .favorites || request.favorites.contains(entry.id),
                  request.scope == "all" || entry.filter == request.scope,
                  !request.finalOnly || request.category != .weapons || entry.final,
                  request.category != .armor || request.hunter == -1 || record.hunter == 2 || record.hunter == request.hunter,
                  request.rarity == 0 || entry.rarity == request.rarity,
                  request.category != .weapons || request.element == "all" || (request.element == "none" ? record.elements.isEmpty : record.elements.contains(request.element)),
                  terms.allSatisfy({ record.text.contains($0) }) else { continue }
            result.append(record)
        }
        switch request.sort {
        case "name": result.sort { $0.nameOrder < $1.nameOrder }
        case "rarity": result.sort { $0.entry.rarity == $1.entry.rarity ? $0.entry.id.id < $1.entry.id.id : $0.entry.rarity > $1.entry.rarity }
        case "value": result.sort { $0.entry.value == $1.entry.value ? $0.entry.id.id < $1.entry.id.id : $0.entry.value > $1.entry.value }
        default: break
        }
        return result.map(\.entry)
    }
}
actor DetailRepository {
    var database: DexDatabase?
    private var cache: [Destination: ItemDetail] = [:]
    private var recency: [Destination] = []
    func detail(_ destination: Destination) throws -> ItemDetail {
        if let cached = cache[destination] { return cached }
        if database == nil { database = try DexDatabase() }
        let value = try database!.detail(for: destination)
        cache[destination] = value
        recency.append(destination)
        if recency.count > 100 { cache.removeValue(forKey: recency.removeFirst()) }
        return value
    }
}
