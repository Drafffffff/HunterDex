import Foundation

@MainActor
enum SelfChecks {
    static func testCatalogCoverageAndTranslation() throws {
        let db = try DexDatabase()
        try XCTAssertEqual(db.entries.filter { $0.destination.category == .weapons }.count, 10877)
        try XCTAssertEqual(db.entries.filter { $0.destination.category == .armor }.count, 5637)
        try XCTAssertEqual(db.entries.filter { $0.destination.category == .quests }.count, 1355)
        try XCTAssertEqual(db.index.count, db.entries.count)
        try XCTAssertEqual(db.zh("monsters", "Rathalos"), "雄火龙")
        try XCTAssertEqual(db.zh("items", "Untranslated item"), "Untranslated item")
        try XCTAssertEqual(try db.query("PRAGMA integrity_check").first?.str("integrity_check"), "ok")
    }

    static func testUpgradeTreeMatchesDatabaseParents() throws {
        let db = try DexDatabase()
        let tree = try db.weaponTree(65794)
        try XCTAssertEqual(tree.first?.destination?.id, 65793)
        try XCTAssertEqual(tree.first?.depth, 0)
        try XCTAssertTrue(tree.contains { $0.destination?.id == 65794 && $0.depth == 1 })
        try XCTAssertEqual(Set(tree.compactMap(\.destination)).count, tree.count)
        let depths = Dictionary(uniqueKeysWithValues: tree.compactMap { row -> (Int, Int)? in row.destination.map { ($0.id, row.depth) } })
        for row in tree where row.depth > 0 {
            let weapon = try db.query("SELECT parent_id FROM weapons WHERE _id=?", [row.destination!.id]).first!
            try XCTAssertEqual(depths[weapon.int("parent_id")], row.depth - 1)
        }
    }

    static func testWeaponMaterialQuestRoundTrip() throws {
        let db = try DexDatabase()
        let weapon = try db.detail(for: Destination(category: .weapons, id: 65793))
        let recipes = weapon.sections.filter { $0.title.contains("素材") }.flatMap(\.rows)
        try XCTAssertFalse(recipes.isEmpty)
        var verifiedQuest = false
        for material in recipes.compactMap(\.destination) {
            let detail = try db.detail(for: material)
            try XCTAssertTrue(detail.sections.contains { $0.title == "用于制作" && $0.rows.contains { $0.destination == weapon.entry.destination } })
            if let quest = detail.sections.first(where: { $0.title == "任务报酬" })?.rows.first?.destination {
                let questDetail = try db.detail(for: quest)
                try XCTAssertTrue(questDetail.sections.flatMap(\.rows).contains { $0.destination == material })
                verifiedQuest = true
            }
        }
        try XCTAssertTrue(verifiedQuest)
    }

    static func testRepresentativeDetailsHaveResolvableLinks() throws {
        let db = try DexDatabase()
        var destinations = [Destination(category: .items, id: 1202), Destination(category: .items, id: 318), Destination(category: .items, id: 2638)]
        for category in Category.allCases where category != .favorites {
            let entries = db.entries.filter { $0.destination.category == category }
            destinations += [entries.first!, entries[entries.count / 2], entries.last!].map(\.destination)
        }
        for destination in destinations {
            let detail = try db.detail(for: destination)
            for link in detail.sections.flatMap(\.rows) + detail.tree {
                if let target = link.destination { try XCTAssertNotNil(db.index[target], "Broken link: \(target)") }
            }
        }
    }

    static func testSearchFiltersHistoryAndFavoritePersistence() async throws {
        let suite = "HunterDexTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = DexStore(defaults: defaults)
        try XCTAssertNil(store.error)
        store.scope = "Great Sword"
        await store.waitForIdle()
        store.finalOnly = true
        await store.waitForIdle()
        try XCTAssertFalse(store.visible.isEmpty)
        try XCTAssertTrue(store.visible.allSatisfy { $0.filter == "Great Sword" && $0.final })
        store.switchCategory(.monsters)
        await store.waitForIdle()
        store.search = "雄火龙"
        await store.waitForIdle()
        try XCTAssertFalse(store.visible.isEmpty)
        let monster = store.visible.first { $0.english == "Rathalos" }!
        store.navigate(monster.destination)
        await store.waitForIdle()
        store.toggleFavorite(monster.destination)
        let restored = DexStore(defaults: defaults)
        try XCTAssertTrue(restored.favorites.contains(monster.destination))
        store.navigate(Destination(category: .items, id: 1202))
        await store.waitForIdle()
        try XCTAssertEqual(store.category, .items)
        try XCTAssertEqual(store.search, "")
        store.back()
        await store.waitForIdle()
        try XCTAssertEqual(store.selection, monster.destination)
        try XCTAssertEqual(store.search, "雄火龙")
        store.forward()
        await store.waitForIdle()
        try XCTAssertEqual(store.selection, Destination(category: .items, id: 1202))
        store.search = "no_such_item_9382948"
        await store.waitForIdle()
        try XCTAssertTrue(store.visible.isEmpty)
        store.switchCategory(.favorites)
        await store.waitForIdle()
        try XCTAssertEqual(store.visible.count, 1)
    }

    static func run() async throws {
        try testCatalogCoverageAndTranslation()
        print("PASS: catalog coverage, translation and database integrity")
        try testUpgradeTreeMatchesDatabaseParents()
        print("PASS: upgrade branches match parent relationships")
        try testWeaponMaterialQuestRoundTrip()
        print("PASS: weapon → material → quest → material round trip")
        try testRepresentativeDetailsHaveResolvableLinks()
        print("PASS: representative detail pages and cross-category links")
        let db = try DexDatabase()
        let materialCategory = try db.detail(for: Destination(category: .items, id: 1966084))
        try XCTAssertTrue(materialCategory.sections.contains { $0.title == "可用素材" && $0.rows.contains { $0.destination?.id == 318 && $0.trailing == "1 点 / 个" } })
        print("PASS: material category points and contributing items")
        try await testSearchFiltersHistoryAndFavoritePersistence()
        print("PASS: filters, Chinese search, history and persistent favorites")
        try await testChineseNamesAndArtwork()
        print("PASS: Chinese equipment names, species identities, artwork and Chinese/English search")
        try await testAsyncSearchAndEquipment()
    }

    static func testChineseNamesAndArtwork() async throws {
        let db = try DexDatabase()
        let first = try db.detail(for: Destination(category: .weapons, id: 65793))
        try XCTAssertEqual(first.entry.name, "贝鲁纳大剑 Lv.1")
        try XCTAssertEqual(first.tree.first?.title, first.entry.name)
        try XCTAssertTrue(first.sections.flatMap(\.rows).contains { $0.title == "铁矿石" && $0.destination?.id == 318 })
        try XCTAssertEqual(db.index[Destination(category: .armor, id: 1310721)]?.name, "皮制头饰")
        try XCTAssertTrue(db.entries.filter { $0.destination.category == .weapons && $0.name != $0.english }.count >= 9000)
        try XCTAssertTrue(db.entries.filter { $0.destination.category == .armor && $0.name != $0.english }.count >= 4800)
        try XCTAssertEqual(db.zh("monsters", "Basarios"), "岩龙")
        try XCTAssertEqual(db.zh("monsters", "Diablos"), "角龙")
        try XCTAssertEqual(db.zh("monsters", "Khezu"), "白电龙")
        try XCTAssertEqual(db.zh("monsters", "Astalos"), "电龙")
        try XCTAssertEqual(db.zh("weapon_types", "Switch Axe"), "斩击斧")
        try XCTAssertEqual(db.zh("weapon_types", "Charge Blade"), "盾斧")
        for entry in db.entries where !entry.iconName.isEmpty && entry.iconName != "icon_sprout" {
            try XCTAssertNotNil(ArtworkCache.shared.image(entry.iconName), "Missing icon: \(entry.iconName)")
        }
        let portraits = db.entries.filter { !$0.portraitName.isEmpty }
        try XCTAssertTrue(portraits.count >= 90)
        for entry in portraits {
            try XCTAssertNotNil(ArtworkCache.shared.image(entry.portraitName), "Missing portrait: \(entry.name)")
        }
        let suite = "HunterDexChineseTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = DexStore(defaults: defaults)
        store.search = "贝鲁纳大剑"
        await store.waitForIdle()
        try XCTAssertFalse(store.visible.isEmpty)
        try XCTAssertTrue(store.visible.contains { $0.destination.id == 65793 })
        store.search = "Petrified Blade"
        await store.waitForIdle()
        try XCTAssertTrue(store.visible.contains { $0.destination.id == 65793 })
    }
    static func testAsyncSearchAndEquipment() async throws {
        let suite = "HunterDexAsyncTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = DexStore(defaults: defaults)
        await store.waitForIdle()
        let db = store.database!
        try XCTAssertEqual(db.weapons.count, 10877)
        try XCTAssertEqual(db.armors.count, 5637)
        try XCTAssertNil(db.weapons[65793]?.parent)
        try XCTAssertTrue(db.weapons.values.allSatisfy { $0.parent == nil || db.weapons[$0.parent!] != nil })
        try XCTAssertEqual(db.weapons[65793]?.sharpness.first, [9, 4, 2, 0, 0, 0, 0])
        store.search = "火"; store.search = "不存在9382948"; store.search = "Petrified Blade"
        await store.waitForIdle()
        try XCTAssertFalse(store.visible.isEmpty)
        try XCTAssertTrue(store.visible.allSatisfy { $0.english.contains("Petrified Blade") })
        store.expanded = [65793, 65794]; store.scrollID = 65794
        store.navigate(Destination(category: .items, id: 318))
        await store.waitForIdle()
        store.back(); await store.waitForIdle()
        try XCTAssertEqual(store.search, "Petrified Blade")
        try XCTAssertTrue(store.expanded.contains(65794))
        try XCTAssertEqual(store.scrollID, 65794)
        store.chooseWeaponType("Long Sword"); await store.waitForIdle()
        try XCTAssertTrue(store.visible.allSatisfy { $0.filter == "Long Sword" })
        store.chooseWeaponType("Great Sword"); await store.waitForIdle()
        try XCTAssertEqual(store.search, "Petrified Blade")
        store.switchCategory(.armor); store.search = "反复无常"; store.hunter = 0
        await store.waitForIdle()
        try XCTAssertFalse(store.visible.isEmpty)
        try XCTAssertTrue(store.visible.allSatisfy { entry in
            let armor = db.armors[entry.id.id]!
            return armor.skills.contains { $0.name.contains("反复无常") } && armor.hunter != 1
        })
        store.chooseWeaponType("Great Sword"); await store.waitForIdle()
        store.navigate(Destination(category: .weapons, id: 65793)); await store.waitForIdle()
        let unrelated = db.weapons.values.first { $0.type == "Great Sword" && $0.parent == nil && $0.id != 65793 }!.id
        store.expanded = [unrelated]
        store.setBranchExpanded(true)
        let expectedBranch = Set(try db.query("WITH RECURSIVE branch(id) AS (SELECT _id FROM weapons WHERE _id=65793 UNION ALL SELECT w._id FROM weapons w JOIN branch b ON w.parent_id=b.id) SELECT id FROM branch").map { $0.int("id") })
        try XCTAssertEqual(store.expanded, expectedBranch.union([unrelated]))
        store.setBranchExpanded(false)
        try XCTAssertEqual(store.expanded, [unrelated])
        store.setBranchExpanded(true, root: 65794)
        try XCTAssertTrue(store.expanded.contains(65793)) // Ancestor revealed, sibling routes untouched.
        store.setBranchExpanded(false, root: 65794)
        try XCTAssertEqual(store.expanded, [65793, unrelated])
        store.chooseWeaponType("Long Sword"); await store.waitForIdle()
        store.chooseWeaponType("Great Sword"); await store.waitForIdle()
        try XCTAssertEqual(store.expanded, [65793, unrelated])
        store.navigate(Destination(category: .weapons, id: 65795)); await store.waitForIdle()
        try XCTAssertTrue(store.expanded.contains(65794))
        store.setBranchExpanded(false, root: 65793)
        store.chooseWeaponType("Long Sword"); await store.waitForIdle()
        store.chooseWeaponType("Great Sword"); await store.waitForIdle()
        try XCTAssertEqual(store.expanded, [unrelated])
        let sections = ["用于制作", "任务报酬", "狩猎获取", "地图采集"].map { DetailSection(title: $0, rows: []) }
        try XCTAssertEqual(DetailHierarchy.ordered(sections, category: .items).map(\.title), ["狩猎获取", "地图采集", "任务报酬", "用于制作"])
        let first = db.armors[1310721]!
        try XCTAssertEqual(first.skills.first?.name, "反复无常")
        try XCTAssertEqual(db.zh("skill_trees", "Handicraft"), "匠")
        try XCTAssertEqual(db.zh("skill_trees", "Destroyer"), "重击")
        try XCTAssertEqual(first.defense, 1); try XCTAssertEqual(first.maximum, 25)
        try XCTAssertTrue(db.armorFamilies[first.family]?.contains(first.id) == true)
        let route = try db.route(from: 65793, to: 65795)
        try XCTAssertEqual(route.steps.map(\.id.id), [65794, 65795])
        try XCTAssertEqual(route.cost, (db.weapons[65794]?.upgradeCost ?? 0) + (db.weapons[65795]?.upgradeCost ?? 0))
        try XCTAssertEqual(route.materials.first(where: { $0.entry.id.id == 1966084 })?.quantity, 10)
        try XCTAssertEqual(route.materials.first(where: { $0.entry.id.id == 321 })?.quantity, 2)
        try XCTAssertTrue(route.materials.allSatisfy { $0.entry.id.category == .items })
        do { _ = try db.route(from: 65795, to: 65793); throw DexError.message("Reverse route was accepted") }
        catch { try XCTAssertTrue(error.localizedDescription.contains("派生路线")) }
        try XCTAssertTrue(db.entries.filter { $0.id.category == .quests && $0.name != $0.english }.count >= 880)
        try XCTAssertEqual(db.index[Destination(category: .items, id: 100)]?.name, "通常弹 Lv.1")
        try XCTAssertEqual(db.zh("locations", "Jurassic Frontier"), "古代林")
        try XCTAssertEqual(db.zh("goals", "Wound Zinogre's head & front legs"), "破坏雷狼龙的头部、前脚")
        let engine = SearchEngine(entries: db.entries, armors: db.armors)
        var elapsed: [Double] = []
        for term in ["火龙", "r", "ra", "rath", "贝鲁纳", "does_not_exist", "", "雷狼", "王牙", "大剑"] {
            let start = Date()
            _ = await engine.search(SearchRequest(category: .weapons, text: term, scope: "all", finalOnly: false, sort: "name", hunter: -1, favorites: []))
            elapsed.append(Date().timeIntervalSince(start) * 1000)
        }
        print("PASS: async latest-query wins, context restoration, armor skill search, weapon types")
        print(String(format: "BENCHMARK: indexed query median %.2f ms, max %.2f ms (without UI / debounce)", elapsed.sorted()[elapsed.count / 2], elapsed.max()!))
    }
    static func XCTAssertEqual<T: Equatable>(_ lhs: T, _ rhs: T) throws {
        guard lhs == rhs else { throw DexError.message("Expected \(rhs), got \(lhs)") }
    }
    static func XCTAssertTrue(_ value: Bool) throws {
        guard value else { throw DexError.message("Expected true") }
    }
    static func XCTAssertFalse(_ value: Bool) throws { try XCTAssertTrue(!value) }
    static func XCTAssertNil<T>(_ value: T?) throws { try XCTAssertTrue(value == nil) }
    static func XCTAssertNotNil<T>(_ value: T?, _ message: String = "Expected non-nil value") throws {
        guard value != nil else { throw DexError.message(message) }
    }
}
