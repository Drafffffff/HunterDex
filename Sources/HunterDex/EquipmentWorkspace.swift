import SwiftUI

struct EquipmentWorkspace: View {
    @ObservedObject var store: DexStore
    @State private var armorSets = false
    private var isWeapon: Bool { store.category == .weapons }
    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 14) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(isWeapon ? (store.database?.zh("weapon_types", store.scope) ?? "武器") : "防具工坊").font(.title2.bold())
                    Text(isWeapon ? "沿派生路线选择，直接比较性能" : "技能点、孔位与强化收益").font(.caption).foregroundStyle(.secondary)
                }
                Spacer(minLength: 5)
                NativeSearchField(text: $store.search, placeholder: isWeapon ? "搜索当前武器类型 · 中 / 英文" : "搜索防具或技能名称", submit: store.submitSearch).frame(minWidth: 170, maxWidth: 280)
                Button { store.inspectorVisible.toggle() } label: { Image(systemName: "sidebar.right") }.help("显示 / 收起详情")
            }.padding(.horizontal, 20).padding(.vertical, 16)
            HStack(spacing: 12) {
                if isWeapon {
                    Picker("视图", selection: $store.treeMode) { Text("派生树").tag(true); Text("性能列表").tag(false) }.pickerStyle(.segmented).labelsHidden().frame(width: 155)
                    Toggle("最终强化", isOn: $store.finalOnly).toggleStyle(.checkbox)
                    Menu {
                        Picker("属性", selection: $store.element) {
                            Text("全部属性").tag("all"); Text("无属性").tag("none")
                            ForEach(["火", "水", "雷", "冰", "龙", "毒", "麻痹", "睡眠", "爆破"], id: \.self) { Text($0).tag($0) }
                        }
                        Picker("稀有度", selection: $store.rarity) {
                            Text("全部稀有度").tag(0)
                            ForEach(1...11, id: \.self) { Text("R\($0)").tag($0) }
                        }
                    } label: { Label(store.element == "all" && store.rarity == 0 ? "属性 / 稀有度" : "\(store.element == "all" ? "全部属性" : store.element == "none" ? "无属性" : store.element) · \(store.rarity == 0 ? "全部稀有度" : "R\(store.rarity)")", systemImage: "line.3.horizontal.decrease") }.fixedSize()
                    if !["Bow", "Light Bowgun", "Heavy Bowgun"].contains(store.scope) {
                        Picker("斩味", selection: $store.sharpnessMode) { Text("通常").tag(0); Text("匠 +1").tag(1); Text("匠 +2").tag(2) }.frame(width: 140)
                    }
                } else {
                    Picker("视图", selection: $armorSets) { Text("按部位").tag(false); Text("同系列").tag(true) }.pickerStyle(.segmented).labelsHidden().frame(width: 145)
                    Picker("部位", selection: $store.scope) { Text("全部").tag("all"); ForEach(store.filters, id: \.0) { Text($0.1).tag($0.0) } }.frame(width: 100)
                    Picker("类型", selection: $store.hunter) { Text("全部类型").tag(-1); Text("剑士 / 通用").tag(0); Text("射手 / 通用").tag(1) }.labelsHidden().frame(width: 125)
                }
                Spacer(minLength: 0)
                if !isWeapon || !store.treeMode {
                    Menu {
                        Picker("排序", selection: $store.sort) {
                            Text("图鉴顺序").tag("database"); Text("名称").tag("name"); Text("稀有度优先").tag("rarity"); Text(isWeapon ? "攻击力优先" : "初始防御优先").tag("value")
                        }
                    } label: { Label("排序", systemImage: "arrow.up.arrow.down") }.fixedSize()
                }
            }.font(.system(size: 12)).padding(.horizontal, 20).padding(.bottom, 12)
            Divider()
            HSplitView {
                VStack(spacing: 0) {
                    if !isWeapon && armorSets { ArmorFamilyBrowser(store: store) }
                    else if store.visible.isEmpty && !store.searching {
                        ContentUnavailableView {
                            Label("没有匹配的装备", systemImage: "magnifyingglass")
                        } description: { Text("检查当前类型与筛选条件，也可以尝试英文名称。") } actions: {
                            Button("清除搜索与筛选") { store.search = ""; store.finalOnly = false; store.hunter = -1; store.element = "all"; store.rarity = 0; if !isWeapon { store.scope = "all" } }
                        }.frame(maxHeight: .infinity)
                    } else { EquipmentTable(store: store) }
                    Divider()
                    HStack {
                        if isWeapon && store.treeMode {
                            Button("展开当前派生") { store.setBranchExpanded(true) }
                            Button("收起当前派生") { store.setBranchExpanded(false) }
                            Divider().frame(height: 12)
                        }
                        Text("\(store.visible.count.formatted()) 个匹配")
                        if store.searching { Text("正在筛选…").foregroundStyle(.secondary) }
                        Spacer()
                        Text(isWeapon && store.treeMode ? "仅作用于当前武器及其后续派生" : "同一列直接比较 · 可拖动列宽")
                    }.font(.system(size: 10)).foregroundStyle(.secondary).padding(10)
                }.frame(minWidth: 460)
                if store.inspectorVisible {
                    EquipmentInspector(store: store).id(store.selection).frame(minWidth: 280, idealWidth: 320, maxWidth: 430)
                }
            }
        }
    }
}

struct EquipmentInspector: View {
    @ObservedObject var store: DexStore
    var body: some View {
        ScrollView {
            if let entry = store.selection.flatMap({ store.database?.index[$0] }) {
                VStack(alignment: .leading, spacing: 16) {
                    HStack(alignment: .top, spacing: 10) {
                        EntryArtwork(entry: entry, size: 28)
                        VStack(alignment: .leading, spacing: 5) {
                            Text(entry.name).font(.system(size: 21, weight: .semibold)).fixedSize(horizontal: false, vertical: true)
                            if entry.name != entry.english { Text(entry.english).font(.caption).foregroundStyle(.secondary).textSelection(.enabled) }
                        }
                    }
                    if let weapon = store.database?.weapons[entry.id.id], entry.id.category == .weapons { WeaponInspector(store: store, entry: entry, weapon: weapon) }
                    if let armor = store.database?.armors[entry.id.id], entry.id.category == .armor { ArmorInspector(store: store, entry: entry, armor: armor) }
                    if store.loadingDetail { ProgressView("读取素材…").controlSize(.small) }
                    if let detail = store.detail {
                        if !detail.description.isEmpty { DisclosureGroup("原文说明") { Text(detail.description).font(.caption).foregroundStyle(.secondary).textSelection(.enabled) }.font(.caption) }
                    }
                }.padding(20)
            } else { ContentUnavailableView("选择装备", systemImage: "cursorarrow.click", description: Text("从表格选中一项，查看性能与制作材料。")) }
        }.background(Color(nsColor: .controlBackgroundColor).opacity(0.4))
    }
}

struct EquipmentRecipes: View {
    @ObservedObject var store: DexStore
    var body: some View {
        if let detail = store.detail {
            VStack(alignment: .leading, spacing: 14) {
                        ForEach(detail.sections.filter { $0.title.contains("素材") }.sorted { $0.title == "强化素材" && $1.title != "强化素材" }) { section in
                            VStack(alignment: .leading, spacing: 10) {
                                Text(section.title).font(.headline)
                                ForEach(section.rows) { row in
                                    if let destination = row.destination {
                                        Button { store.navigate(destination) } label: {
                                            HStack(spacing: 8) {
                                                if let item = store.database?.index[destination] { EntryArtwork(entry: item, size: 20) }
                                                Text(row.title).multilineTextAlignment(.leading)
                                                Spacer(minLength: 4)
                                                Text(row.trailing).monospacedDigit()
                                                Image(systemName: "chevron.right").font(.system(size: 9))
                                            }.font(.system(size: 12)).padding(.vertical, 5).contentShape(Rectangle())
                                        }.buttonStyle(.plain)
                                    }
                                }
                            }
                            Divider()
                        }
            }
        }
    }
}

struct WeaponInspector: View {
    @ObservedObject var store: DexStore
    let entry: Entry
    let weapon: WeaponInfo
    @State private var routeOpen = false
    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack { Text("R\(entry.rarity)"); Text(weapon.slots == 0 ? "无孔" : "\(weapon.slots) 孔"); if entry.final { Text("最终强化").foregroundStyle(Color.dexAccent) } }.font(.caption).foregroundStyle(.secondary)
            HStack(alignment: .firstTextBaseline) {
                Text("\(weapon.attack)").font(.system(size: 30, weight: .semibold, design: .rounded))
                Text("攻击").foregroundStyle(.secondary)
                Spacer()
                Text("会心 \(weapon.affinity)%").monospacedDigit()
            }.font(.caption)
            if !weapon.elements.isEmpty { Text(weapon.elements).font(.subheadline.weight(.medium)) }
            if !weapon.ranged {
                VStack(spacing: 9) {
                    ForEach(Array(weapon.sharpness.prefix(3).enumerated()), id: \.offset) { offset, values in
                        HStack {
                            Text(["通常", "匠 +1", "匠 +2"][offset]).font(.caption).foregroundStyle(.secondary).frame(width: 42, alignment: .leading)
                            SharpnessBar(values: values, scale: 45).frame(height: 9)
                        }
                    }
                }
            }
            if !weapon.special.isEmpty { Text(weapon.special).font(.caption).foregroundStyle(.secondary) }
            Divider()
            if let parent = weapon.parent, let previous = store.database?.index[Destination(category: .weapons, id: parent)] {
                VStack(alignment: .leading, spacing: 8) {
                    Text("从上一级强化").font(.headline)
                    equipmentLink(previous, store: store)
                    if weapon.upgradeCost > 0 { Text("本次强化 \(weapon.upgradeCost.formatted()) z").font(.caption).foregroundStyle(.secondary) }
                }
            }
            if weapon.creationCost > 0 { Label("可直接生产 · \(weapon.creationCost.formatted()) z", systemImage: "hammer").font(.caption) }
            EquipmentRecipes(store: store)
            let children = (store.database?.weapons.values.filter { $0.parent == weapon.id } ?? []).sorted { $0.id < $1.id }
            if !children.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("继续派生").font(.headline)
                    ForEach(children, id: \.id) { child in
                        if let next = store.database?.index[Destination(category: .weapons, id: child.id)] { equipmentLink(next, store: store) }
                    }
                }
            }
            if !store.treeMode { Button("定位派生树") { store.treeMode = true; store.setBranchExpanded(true) } }
            Divider()
            DisclosureGroup("累计整条路线材料", isExpanded: $routeOpen) {
              VStack(alignment: .leading, spacing: 10) {
                if let start = store.routeStart, let first = store.database?.index[Destination(category: .weapons, id: start)] {
                    Text("起点：\(first.name)").font(.caption).foregroundStyle(.secondary)
                    Text("累计后续强化需求，不含起点生产。").font(.system(size: 10)).foregroundStyle(.secondary)
                    HStack {
                        Button("计算到当前武器") { store.calculateRoute(to: weapon.id) }.disabled(start == weapon.id || store.routeLoading)
                        Button("清除") { store.routeStart = nil; store.weaponRoute = nil; store.routeError = nil }
                    }.font(.caption)
                }
                Button("以这把武器为起点") { store.routeStart = weapon.id; store.weaponRoute = nil; store.routeError = nil }.font(.caption)
                if store.routeLoading { ProgressView().controlSize(.small) }
                if let error = store.routeError { Text(error).font(.caption).foregroundStyle(.orange) }
                if let route = store.weaponRoute, route.target.id.id == weapon.id {
                    Text("\(route.steps.count) 次强化 · \(route.cost.formatted()) z").font(.caption.weight(.semibold))
                    ForEach(route.materials) { material in
                        Button { store.navigate(material.entry.id) } label: {
                            HStack { Text(material.entry.name).multilineTextAlignment(.leading); Spacer(); Text("\(material.quantity)" + (material.points ? " 点" : " 个")).monospacedDigit() }.font(.caption).padding(.vertical, 3)
                        }.buttonStyle(.plain).foregroundStyle(Color.dexAccent)
                    }
                }
            }
            }.font(.caption).onAppear { routeOpen = store.routeStart != nil }
        }
    }
}

@MainActor
func equipmentLink(_ entry: Entry, store: DexStore) -> some View {
    Button { store.navigate(entry.id) } label: {
        HStack { Text(entry.name).multilineTextAlignment(.leading); Spacer(minLength: 5); Image(systemName: "chevron.right").font(.system(size: 9)) }.font(.system(size: 12)).padding(.vertical, 4).contentShape(Rectangle())
    }.buttonStyle(.plain).foregroundStyle(Color.dexAccent)
}

struct ArmorInspector: View {
    @ObservedObject var store: DexStore
    let entry: Entry
    let armor: ArmorInfo
    @State private var expandedSkill: Int?
    private var baseline: ArmorInfo? { store.armorBaseline.flatMap { store.database?.armors[$0] } }
    private var comparable: Bool { baseline.map { $0.slot == armor.slot && ($0.hunter == armor.hunter || $0.hunter == 2 || armor.hunter == 2) && ($0.gender == armor.gender || $0.gender == 2 || armor.gender == 2) } ?? false }
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("\(DexDatabase.slotName(armor.slot)) · \(armor.hunterLabel) · \(armor.genderLabel) · R\(entry.rarity)").font(.caption).foregroundStyle(.secondary)
            VStack(alignment: .leading, spacing: 12) {
                HStack { Text("技能点贡献").font(.headline); Spacer(); Text(armor.slots == 0 ? "无孔" : String(repeating: "●", count: armor.slots) + "  \(armor.slots) 孔").font(.caption).foregroundStyle(Color.dexAccent) }
                if armor.skills.isEmpty { Text("这件防具没有技能点").font(.caption).foregroundStyle(.secondary) }
                ForEach(armor.skills) { skill in
                    VStack(alignment: .leading, spacing: 7) {
                        Button { expandedSkill = expandedSkill == skill.id ? nil : skill.id } label: {
                            HStack {
                                Text(skill.name); Spacer()
                                Text(signed(skill.points)).monospacedDigit().foregroundStyle(skill.points < 0 ? Color.orange : Color.dexAccent)
                                Image(systemName: expandedSkill == skill.id ? "chevron.up" : "chevron.down").font(.system(size: 9)).foregroundStyle(.secondary)
                            }.font(.system(size: 14, weight: .medium)).padding(.vertical, 4).contentShape(Rectangle())
                        }.buttonStyle(.plain)
                        if expandedSkill == skill.id {
                            ForEach(Array(skill.effects.enumerated()), id: \.offset) { _, effect in
                                HStack { Text(effect.name); Spacer(); Text("\(signed(effect.threshold)) 点") }.font(.caption).foregroundStyle(.secondary)
                            }
                            Text("发动条件按整套装备累计计算，以上是单件贡献。").font(.system(size: 10)).foregroundStyle(.secondary)
                        }
                    }
                }
            }
            if let baseline {
                VStack(alignment: .leading, spacing: 9) {
                    HStack { Text("与基准的差异").font(.headline); Spacer(); Button("清除") { store.armorBaseline = nil }.font(.caption) }
                    if let baseEntry = store.database?.index[Destination(category: .armor, id: baseline.id)] { Text(baseEntry.name).font(.caption).foregroundStyle(.secondary) }
                    if comparable {
                        Text(baseline.id == armor.id ? "当前装备就是比较基准" : "只列出变化的属性").font(.system(size: 10)).foregroundStyle(.secondary)
                        comparison("初始防御", armor.defense - baseline.defense)
                        comparison("满强化防御", armor.maximum - baseline.maximum)
                        comparison("孔位", armor.slots - baseline.slots)
                        ForEach(Array(Set(armor.skills.map(\.id) + baseline.skills.map(\.id))).sorted(), id: \.self) { id in
                            let current = armor.skills.first { $0.id == id }; let previous = baseline.skills.first { $0.id == id }
                            comparison(current?.name ?? previous?.name ?? "技能", (current?.points ?? 0) - (previous?.points ?? 0))
                        }
                        ForEach(0..<5, id: \.self) { index in comparison(["火耐性", "水耐性", "雷耐性", "冰耐性", "龙耐性"][index], armor.resistances[index] - baseline.resistances[index]) }
                    } else { Text("请选择同部位、适用类型兼容的装备进行比较。").font(.caption).foregroundStyle(.secondary) }
                }
            }
            Button(store.armorBaseline == armor.id ? "当前比较基准" : "设为比较基准") { store.armorBaseline = armor.id }.disabled(store.armorBaseline == armor.id)
            Divider()
            VStack(alignment: .leading, spacing: 9) {
                Text("防御强化").font(.headline)
                HStack(alignment: .firstTextBaseline, spacing: 10) {
                    Text("\(armor.defense)").font(.title2.monospacedDigit())
                    Image(systemName: "arrow.right").foregroundStyle(.tertiary)
                    Text("\(armor.maximum)").font(.title2.monospacedDigit().weight(.semibold))
                    Spacer(); Text("+\(armor.maximum - armor.defense)").font(.caption).foregroundStyle(.secondary)
                }
                Text("初始 → 满强化").font(.caption).foregroundStyle(.secondary)
            }
            VStack(alignment: .leading, spacing: 12) {
                Text("属性耐性").font(.headline)
                HStack(spacing: 0) {
                    ForEach(0..<5, id: \.self) { index in
                        VStack(spacing: 8) {
                            Text(["火", "水", "雷", "冰", "龙"][index]).font(.caption).foregroundStyle(.secondary)
                            Text(signed(armor.resistances[index])).font(.system(size: 15, weight: .medium, design: .rounded)).foregroundStyle(armor.resistances[index] < 0 ? Color.orange : armor.resistances[index] == 0 ? Color.secondary : Color.primary)
                        }.frame(maxWidth: .infinity)
                    }
                }
            }
            Divider()
            EquipmentRecipes(store: store)
            let family = store.database?.armorFamilies[armor.family] ?? []
            if !family.isEmpty {
                DisclosureGroup("同系列部位") {
                  VStack(alignment: .leading, spacing: 8) {
                    ForEach(family, id: \.self) { id in
                        if let piece = store.database?.index[Destination(category: .armor, id: id)] { equipmentLink(piece, store: store) }
                    }
                  }
                }.font(.caption)
            }
        }
    }
    func comparison(_ title: String, _ difference: Int) -> some View {
        Group {
            if difference != 0 { HStack { Text(title); Spacer(); Text(signed(difference)).monospacedDigit().foregroundStyle(difference < 0 ? Color.orange : Color.dexAccent) }.font(.caption) }
        }
    }
}

struct ArmorFamilyBrowser: View {
    @ObservedObject var store: DexStore
    var groups: [(Int, [Entry])] {
        Dictionary(grouping: store.visible, by: { store.database?.armors[$0.id.id]?.family ?? $0.id.id }).sorted { $0.key < $1.key }.map { ($0.key, $0.value) }
    }
    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 22) {
                ForEach(groups, id: \.0) { family, entries in
                    VStack(alignment: .leading, spacing: 9) {
                        HStack { Text("同系列 · \(entries.count) 个匹配部位").font(.caption.weight(.semibold)); Spacer(); Text("R\(entries.first?.rarity ?? 0)").font(.caption).foregroundStyle(.secondary) }
                        ForEach(entries) { entry in
                            if let armor = store.database?.armors[entry.id.id] {
                                Button { store.navigate(entry.id) } label: {
                                    HStack {
                                        Text(DexDatabase.slotName(armor.slot)).foregroundStyle(.secondary).frame(width: 35)
                                        VStack(alignment: .leading, spacing: 4) { Text(entry.name); Text(armor.summary).font(.caption).foregroundStyle(.secondary) }
                                        Spacer(); Text("\(armor.defense) → \(armor.maximum)").monospacedDigit(); Text("\(armor.slots) 孔")
                                    }.font(.system(size: 12)).padding(10).background(store.selection == entry.id ? Color.dexAccent.opacity(0.12) : .clear, in: RoundedRectangle(cornerRadius: 5)).contentShape(Rectangle())
                                }.buttonStyle(.plain)
                            }
                        }
                        Divider()
                    }
                }
            }.padding(18)
        }
    }
}
