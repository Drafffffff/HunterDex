import SwiftUI

struct BrowseContext {
    var category: Category = .weapons
    var search = ""
    var scope = "Great Sword"
    var finalOnly = false
    var sort = "database"
    var hunter = -1
    var element = "all"
    var rarity = 0
    var selection: Destination?
    var expanded: Set<Int> = []
    var scrollID: Int?
    var treeMode = true
}

@MainActor
final class DexStore: ObservableObject {
    @Published var category: Category = .weapons
    @Published var search = "" { didSet { if search != oldValue { scheduleSearch() } } }
    @Published var scope = "Great Sword" { didSet { if scope != oldValue { scheduleSearch(immediate: true) } } }
    @Published var finalOnly = false { didSet { if finalOnly != oldValue { scheduleSearch(immediate: true) } } }
    @Published var sort = "database" { didSet { if sort != oldValue { scheduleSearch(immediate: true) } } }
    @Published var hunter = -1 { didSet { if hunter != oldValue { scheduleSearch(immediate: true) } } }
    @Published var element = "all" { didSet { if element != oldValue { scheduleSearch(immediate: true) } } }
    @Published var rarity = 0 { didSet { if rarity != oldValue { scheduleSearch(immediate: true) } } }
    @Published var treeMode = true
    @Published var sharpnessMode = 0
    @Published var inspectorVisible = true
    @Published var armorBaseline: Int?
    @Published var routeStart: Int?
    @Published var weaponRoute: WeaponRoute?
    @Published var routeError: String?
    @Published var routeLoading = false
    private var routeTask: Task<Void, Never>?
    @Published private(set) var visible: [Entry] = []
    @Published private(set) var selection: Destination?
    @Published private(set) var detail: ItemDetail?
    @Published private(set) var searching = false
    @Published private(set) var loadingDetail = false
    @Published private(set) var favorites: Set<Destination> = []
    @Published private(set) var history: [Destination] = []
    @Published private(set) var historyPosition = -1
    @Published var error: String?
    private(set) var database: DexDatabase?
    @Published var expanded: Set<Int> = []
    var scrollID: Int?
    private let defaults: UserDefaults
    private var engine: SearchEngine?
    private let repository = DetailRepository()
    private var queryTask: Task<Void, Never>?
    private var detailTask: Task<Void, Never>?
    private var generation = 0
    private var batching = false
    private var counts: [Category: Int] = [:]
    private var contexts: [String: BrowseContext] = [:]
    private var historyContexts: [BrowseContext] = []
    private var lastWeaponType = "Great Sword"
    private var preferredSelections: [String: Destination] = [:]

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        if let data = defaults.data(forKey: "favorites"), let saved = try? JSONDecoder().decode(Set<Destination>.self, from: data) { favorites = saved }
        lastWeaponType = defaults.string(forKey: "weaponType") ?? "Great Sword"
        if !DexDatabase.weaponTypes.contains(lastWeaponType) { lastWeaponType = "Great Sword" }
        scope = lastWeaponType
        do {
            let db = try DexDatabase(); database = db
            counts = Dictionary(grouping: db.entries, by: { $0.id.category }).mapValues(\.count)
            engine = SearchEngine(entries: db.entries, armors: db.armors, weapons: db.weapons)
            visible = db.entries.filter { $0.id.category == .weapons && $0.filter == scope }
            if let first = visible.first { navigate(first.id) }
        } catch { self.error = error.localizedDescription }
    }
    var canGoBack: Bool { historyPosition > 0 }
    var canGoForward: Bool { historyPosition + 1 < history.count }
    var total: Int { count(category) }
    func count(_ category: Category) -> Int { category == .favorites ? favorites.count : counts[category] ?? 0 }
    var contextKey: String { category == .weapons ? "weapons:\(scope)" : category.rawValue }
    var context: BrowseContext { BrowseContext(category: category, search: search, scope: scope, finalOnly: finalOnly, sort: sort, hunter: hunter, element: element, rarity: rarity, selection: selection, expanded: expanded, scrollID: scrollID, treeMode: treeMode) }
    var filters: [(String, String)] {
        switch category {
        case .weapons: return DexDatabase.weaponTypes.map { ($0, database?.zh("weapon_types", $0) ?? $0) }
        case .armor: return ["Head", "Body", "Arms", "Waist", "Legs"].map { ($0, DexDatabase.slotName($0)) }
        case .quests: return [("LR", "下位"), ("HR", "上位"), ("G", "G位")]
        case .items: return [("Item", "道具 / 素材"), ("Materials", "素材点数类别"), ("Decoration", "装饰品"), ("Palico Weapon", "随从武器"), ("Palico Armor", "随从防具")]
        default: return []
        }
    }
    func setBranchExpanded(_ expand: Bool, root: Int? = nil) {
        guard let db = database, let root = root ?? selection?.id, db.weapons[root] != nil else { return }
        let children = Dictionary(grouping: db.weapons.values.filter { $0.parent != nil }, by: { $0.parent! })
        var branch: Set<Int> = []
        var pending = [root]
        while let id = pending.popLast(), branch.insert(id).inserted {
            pending.append(contentsOf: (children[id] ?? []).map(\.id))
        }
        if expand {
            expanded.formUnion(branch)
            revealAncestors(of: [root])
        } else { expanded.subtract(branch) }
    }
    private func revealAncestors(of ids: [Int]) {
        var result = expanded
        for id in ids {
            var current = database?.weapons[id]?.parent
            var visited: Set<Int> = []
            while let parent = current, visited.insert(parent).inserted {
                result.insert(parent); current = database?.weapons[parent]?.parent
            }
        }
        if result != expanded { expanded = result }
    }
    func refresh() { scheduleSearch(immediate: true) }
    func submitSearch() { scheduleSearch(immediate: true) }
    private func scheduleSearch(immediate: Bool = false, revealMatches: Bool = true) {
        guard !batching, let engine else { return }
        queryTask?.cancel(); generation += 1
        let token = generation
        let request = SearchRequest(category: category, text: search, scope: scope, finalOnly: finalOnly, sort: sort, hunter: hunter, favorites: favorites, element: element, rarity: rarity)
        searching = true
        queryTask = Task { [weak self] in
            if !immediate && !request.text.isEmpty { try? await Task.sleep(for: .milliseconds(120)) }
            guard !Task.isCancelled else { return }
            let result = await engine.search(request)
            guard !Task.isCancelled, let self, self.generation == token else { return }
            if revealMatches && request.category == .weapons && (!request.text.isEmpty || request.finalOnly || request.element != "all" || request.rarity != 0) { self.revealAncestors(of: result.map { $0.id.id }) }
            self.visible = result
            self.searching = false
        }
    }
    func waitForIdle() async { await queryTask?.value; await detailTask?.value }
    private func saveContext() {
        contexts[contextKey] = context
        if historyContexts.indices.contains(historyPosition) { historyContexts[historyPosition] = context }
    }
    private func apply(_ value: BrowseContext) {
        batching = true
        category = value.category; search = value.search; scope = value.scope
        finalOnly = value.finalOnly; sort = value.sort; hunter = value.hunter; element = value.element; rarity = value.rarity
        expanded = value.expanded; scrollID = value.scrollID; treeMode = value.treeMode
        batching = false
        // Keep unrelated results from briefly appearing under the new category title.
        visible = []
        scheduleSearch(immediate: true, revealMatches: false)
    }
    func switchCategory(_ next: Category) {
        guard next != category else { return }
        saveContext()
        let key = next == .weapons ? "weapons:\(lastWeaponType)" : next.rawValue
        let value = contexts[key] ?? BrowseContext(category: next, scope: next == .weapons ? lastWeaponType : "all")
        apply(value)
        if let destination = value.selection ?? database?.entries.first(where: { $0.id.category == next && (value.scope == "all" || $0.filter == value.scope) })?.id { navigate(destination, reveal: false) }
        else { selection = nil; detail = nil; detailTask?.cancel(); loadingDetail = false }
    }
    func chooseWeaponType(_ type: String) {
        guard category != .weapons || scope != type else { return }
        saveContext(); lastWeaponType = type; defaults.set(type, forKey: "weaponType")
        let value = contexts["weapons:\(type)"] ?? BrowseContext(scope: type)
        apply(value)
        if let destination = value.selection ?? database?.entries.first(where: { $0.id.category == .weapons && $0.filter == type })?.id { navigate(destination, reveal: false) }
    }
    func navigate(_ destination: Destination, record: Bool = true, reveal: Bool = true) {
        guard let entry = database?.index[destination] else { return }
        if selection == destination && detail?.entry.id == destination { return }
        if record { saveContext() }
        if category != destination.category && !(category == .favorites && favorites.contains(destination)) {
            let key = destination.category == .weapons ? "weapons:\(entry.filter)" : destination.category.rawValue
            var value = contexts[key] ?? BrowseContext(category: destination.category, scope: destination.category == .weapons ? entry.filter : "all")
            value.selection = destination; apply(value)
        } else if category == .weapons && scope != "all" && scope != entry.filter {
            var value = contexts["weapons:\(entry.filter)"] ?? BrowseContext(scope: entry.filter)
            value.selection = destination; apply(value)
        }
        selection = destination
        weaponRoute = nil; routeError = nil; routeTask?.cancel(); routeLoading = false
        if destination.category == .weapons {
            if reveal { revealAncestors(of: [destination.id]) }
            lastWeaponType = entry.filter
        }
        detailTask?.cancel(); loadingDetail = true
        detail = nil
        detailTask = Task { [weak self, repository] in
            do {
                let value = try await repository.detail(destination)
                guard !Task.isCancelled, let self, self.selection == destination else { return }
                self.detail = value; self.loadingDetail = false; self.error = nil
            } catch {
                guard !Task.isCancelled, let self else { return }
                self.error = error.localizedDescription; self.loadingDetail = false
            }
        }
        if record {
            history = Array(history.prefix(historyPosition + 1)); historyContexts = Array(historyContexts.prefix(historyPosition + 1))
            history.append(destination); historyContexts.append(context); historyPosition = history.count - 1
        }
    }
    func back() {
        guard canGoBack else { return }; saveContext(); historyPosition -= 1
        apply(historyContexts[historyPosition]); navigate(history[historyPosition], record: false, reveal: false)
    }
    func forward() {
        guard canGoForward else { return }; saveContext(); historyPosition += 1
        apply(historyContexts[historyPosition]); navigate(history[historyPosition], record: false, reveal: false)
    }
    func calculateRoute(to target: Int) {
        guard let start = routeStart else { return }
        routeTask?.cancel(); routeLoading = true; routeError = nil
        routeTask = Task { [weak self, repository] in
            do {
                let route = try await repository.route(from: start, to: target)
                guard !Task.isCancelled, let self, self.routeStart == start else { return }
                self.weaponRoute = route; self.routeLoading = false
            } catch {
                guard !Task.isCancelled, let self else { return }
                self.routeError = error.localizedDescription; self.routeLoading = false
            }
        }
    }
    func toggleFavorite(_ destination: Destination) {
        if favorites.contains(destination) { favorites.remove(destination) } else { favorites.insert(destination) }
        if let data = try? JSONEncoder().encode(favorites) { defaults.set(data, forKey: "favorites") }
        if category == .favorites { refresh() }
    }
}
