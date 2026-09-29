import SwiftUI
import AppKit

struct ContentView: View {
    @ObservedObject var store: DexStore
    @FocusState private var searchFocused: Bool
    @State private var showAbout = false

    var body: some View {
        NavigationSplitView {
            sidebar.navigationSplitViewColumnWidth(min: 165, ideal: 190, max: 235)
        } detail: {
            if store.category == .weapons || store.category == .armor {
                EquipmentWorkspace(store: store)
            } else {
                HSplitView {
                    catalog.frame(minWidth: 260, idealWidth: 310, maxWidth: 380)
                    if let selected = store.selection, [.weapons, .armor].contains(selected.category) {
                        EquipmentInspector(store: store).id(selected)
                    } else if let detail = store.detail {
                        DetailView(detail: detail, store: store).id(detail.entry.id)
                    } else if store.loadingDetail {
                        ProgressView("读取资料…").frame(maxWidth: .infinity, maxHeight: .infinity)
                    } else {
                        ContentUnavailableView("选择一个条目", systemImage: "book.closed", description: Text("从列表查看资料与关联来源。"))
                    }
                }
            }
        }
        .navigationTitle("")
        .toolbar {
            ToolbarItemGroup(placement: .navigation) {
                Button(action: store.back) { Image(systemName: "chevron.left") }.disabled(!store.canGoBack).help("后退 ⌘[")
                Button(action: store.forward) { Image(systemName: "chevron.right") }.disabled(!store.canGoForward).help("前进 ⌘]")
            }
            ToolbarItem(placement: .principal) {
                HStack(spacing: 7) {
                    Text("MHXX / MHGU").font(.system(size: 12, weight: .semibold, design: .rounded))
                    Text("猎人手册").foregroundStyle(.secondary).font(.system(size: 12))
                }
            }
            ToolbarItemGroup(placement: .primaryAction) {
                if let destination = store.selection {
                    Button { store.toggleFavorite(destination) } label: {
                        Image(systemName: store.favorites.contains(destination) ? "star.fill" : "star")
                    }.help("收藏 / 取消收藏 ⌘D")
                }
                Button { showAbout = true } label: { Image(systemName: "info.circle") }.help("数据来源与版本")
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .dexFocusSearch)) { _ in searchFocused = true }
        .alert("读取数据时遇到问题", isPresented: Binding(get: { store.error != nil }, set: { if !$0 { store.error = nil } })) {
            Button("好") { store.error = nil }
        } message: { Text(store.error ?? "") }
        .sheet(isPresented: $showAbout) { about }
    }

    private var sidebar: some View {
        VStack(spacing: 0) {
            HStack(spacing: 11) {
                Image(systemName: "book.closed.fill").font(.system(size: 26)).foregroundStyle(Color.dexAccent)
                VStack(alignment: .leading, spacing: 4) {
                    Text("猎人手册").font(.system(size: 19, weight: .bold))
                    Text("FIELD NOTES / XX").font(.system(size: 8, weight: .semibold, design: .monospaced)).tracking(0.9).foregroundStyle(.secondary).lineLimit(1)
                }
                Spacer(minLength: 0)
            }.padding(.horizontal, 18).padding(.vertical, 28)
            List(selection: Binding<Category?>(get: { store.category }, set: { if let category = $0 { store.switchCategory(category) } })) {
                Section("图鉴") {
                    ForEach(Category.allCases.filter { $0 != .favorites }) { category in
                        sidebarRow(category)
                        if category == .weapons && store.category == .weapons {
                            ForEach(DexDatabase.weaponTypes, id: \.self) { type in
                                Button { store.chooseWeaponType(type) } label: {
                                    HStack {
                                        Text(store.database?.zh("weapon_types", type) ?? type)
                                        Spacer()
                                        if store.scope == type { Image(systemName: "circle.fill").font(.system(size: 5)).foregroundStyle(Color.dexAccent) }
                                    }.font(.system(size: 12)).padding(.leading, 24).padding(.vertical, 2).contentShape(Rectangle())
                                }.buttonStyle(.plain)
                            }
                        }
                    }
                }
                Section("狩猎笔记") { sidebarRow(.favorites) }
            }
            .listStyle(.sidebar)
            Spacer(minLength: 0)
            VStack(alignment: .leading, spacing: 9) {
                Label("离线资料库", systemImage: "checkmark.circle.fill").font(.system(size: 11, weight: .medium)).foregroundStyle(Color.dexAccent)
                Text("MHXX · GENERATIONS ULTIMATE").font(.system(size: 8, weight: .medium, design: .monospaced)).foregroundStyle(.secondary)
                Text("数据快照 2018.12.13").font(.system(size: 10)).foregroundStyle(.tertiary)
            }.frame(maxWidth: .infinity, alignment: .leading).padding(20)
        }
    }

    private func sidebarRow(_ category: Category) -> some View {
        HStack(spacing: 10) {
            Image(systemName: category.icon).frame(width: 20).foregroundStyle(category == store.category ? Color.dexAccent : .secondary)
            Text(category.title)
            Spacer(minLength: 2)
            Text(store.count(category).formatted(.number.notation(.compactName))).font(.system(size: 10, design: .rounded)).foregroundStyle(.tertiary)
        }.padding(.vertical, 6).tag(category)
    }

    private var catalog: some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 15) {
                HStack(alignment: .firstTextBaseline) {
                    Text(store.category.title).font(.system(size: 25, weight: .bold))
                    Spacer()
                    Text("\(store.visible.count.formatted()) 条").font(.system(size: 11, design: .monospaced)).foregroundStyle(.secondary)
                }
                NativeSearchField(text: $store.search, placeholder: "搜索名称、类别或编号", submit: store.submitSearch)
                HStack {
                    if !store.filters.isEmpty {
                        Picker("筛选", selection: $store.scope) {
                            Text("全部类型").tag("all")
                            ForEach(store.filters, id: \.0) { Text($0.1).tag($0.0) }
                        }.labelsHidden().frame(maxWidth: 160)
                    }
                    Spacer(minLength: 4)
                    Menu {
                        Picker("排序方式", selection: $store.sort) {
                            Text("图鉴顺序").tag("database")
                            Text("名称").tag("name")
                            Text("稀有度从高到低").tag("rarity")
                            if [.weapons, .armor, .quests].contains(store.category) { Text(store.category == .quests ? "星级从高到低" : store.category == .armor ? "防御力从高到低" : "攻击力从高到低").tag("value") }
                        }
                    } label: { Image(systemName: "arrow.up.arrow.down") }.menuStyle(.borderlessButton).fixedSize().help("排序")
                }
                if store.category == .weapons {
                    Toggle("仅最终强化", isOn: $store.finalOnly).toggleStyle(.checkbox).font(.system(size: 11)).foregroundStyle(.secondary)
                }
            }.padding(20)
            Divider()
            if store.visible.isEmpty {
                ContentUnavailableView("没有匹配的条目", systemImage: "magnifyingglass", description: Text(store.category == .favorites ? "还没有收藏，或当前搜索没有匹配项。" : "试试英文名、中文名，或调整筛选条件。"))
                    .frame(maxHeight: .infinity)
            } else {
                EquipmentTable(store: store)
            }
            Divider()
            HStack {
                Text("\(store.visible.count.formatted()) / \(store.total.formatted())")
                Spacer()
                Text("支持中英文检索")
            }.font(.system(size: 10)).foregroundStyle(.secondary).padding(.horizontal, 18).padding(.vertical, 10)
        }.background(Color(nsColor: .controlBackgroundColor).opacity(0.4))
    }

    private var about: some View {
        VStack(alignment: .leading, spacing: 18) {
            Label("猎人手册", systemImage: "book.closed.fill").font(.title.bold()).foregroundStyle(Color.dexAccent)
            Text("macOS 原生 · MHXX / MHGU 离线百科\n预览版 0.3.0 · 搜索与装备工作台").foregroundStyle(.secondary)
            Text("数据来自 MHGenDatabase 的本地快照（2018-12-13）。现有中文覆盖 9,090 条武器等级、4,803 件防具、1,562 条普通道具、277 类强化素材、242 颗装饰珠和 882 个任务名，保留英文检索。社区名称通过装备数值、掉落记录或任务信息的唯一对应关系核验；未核实的译名继续显示英文。")
            Text("本版提供武器、防具、素材、怪物和任务查询，以及强化树、关联跳转和本地收藏。尚未实现自动配装；弩弹详细表、猫饭和狩技等内容待补充。")
            Link("HunterDex · 开源项目与更新", destination: URL(string: "https://github.com/Drafffffff/HunterDex")!)
            Link("MHGenDatabase · 数据来源", destination: URL(string: "https://github.com/gatheringhallstudios/MHGenDatabase")!)
            Link("jestar719/mhgu · 社区中文资料", destination: URL(string: "https://github.com/jestar719/mhgu")!)
            Text("内置 91 张怪物插画和 205 个图标，来源为 MHGenDatabase 及 monster-hunter-web-data。武器与防具目前使用类别 / 部位图标，尚未收录逐件外观图；片手剑和狩猎笛的中文名仍有较多缺口。")
                .font(.footnote).foregroundStyle(.secondary)
            Text("这是独立开发的非官方工具，与 Ping’s Dex 及 CAPCOM 无隶属关系。未使用 Ping’s Dex 的程序或资源。游戏相关名称的权利归各自所有者。")
                .font(.footnote).foregroundStyle(.secondary)
            HStack { Spacer(); Button("开始狩猎") { showAbout = false }.keyboardShortcut(.defaultAction) }
        }.padding(32).frame(width: 480).fixedSize(horizontal: false, vertical: true)
    }
}

struct CatalogRow: View {
    let entry: Entry
    let favorite: Bool
    var body: some View {
        HStack(alignment: .center, spacing: 11) {
            EntryArtwork(entry: entry, size: 31)
            VStack(alignment: .leading, spacing: 5) {
                HStack(spacing: 4) {
                    Text(entry.name).font(.system(size: 12, weight: .medium)).lineLimit(1)
                    if favorite { Image(systemName: "star.fill").font(.system(size: 8)).foregroundStyle(.orange) }
                }
                Text(entry.subtitle + (entry.rarity > 0 ? "  ·  R\(entry.rarity)" : "")).font(.system(size: 10)).foregroundStyle(.secondary).lineLimit(1)
            }
            Spacer(minLength: 2)
            if [.weapons, .armor].contains(entry.destination.category) {
                Text(entry.value.formatted()).font(.system(size: 12, weight: .medium, design: .monospaced)).foregroundStyle(.secondary)
            }
        }.frame(height: 44).help(entry.name == entry.english ? entry.name : "\(entry.name) · \(entry.english)")
    }
}

struct DetailView: View {
    let detail: ItemDetail
    @ObservedObject var store: DexStore
    @State private var openSections: Set<String> = []
    private var entry: Entry { detail.entry }
    private var sections: [DetailSection] { DetailHierarchy.ordered(detail.sections, category: entry.id.category) }
    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    header.id("top")
                    if entry.id.category == .quests {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("主要目标").font(.caption).foregroundStyle(.secondary)
                            Text(detail.description).font(.system(size: 17, weight: .semibold)).fixedSize(horizontal: false, vertical: true)
                            HStack(spacing: 20) {
                                ForEach(detail.metrics.filter { $0.label == "星级" || $0.label == "限制时间" }) { metric in
                                    Text("\(metric.label)  \(metric.value)").font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                    ForEach(sections) { section in
                        DetailSectionPreview(section: section, store: store, secondary: DetailHierarchy.isSecondary(section.title) && sections.contains { !DetailHierarchy.isSecondary($0.title) }, expanded: Binding(get: { openSections.contains(section.id) }, set: { if $0 { openSections.insert(section.id) } else { openSections.remove(section.id) } }))
                            .id(section.id)
                    }
                    DisclosureGroup("补充资料与原文") {
                        VStack(alignment: .leading, spacing: 10) {
                            ForEach(detail.metrics.filter { entry.id.category != .quests || ($0.label != "星级" && $0.label != "限制时间") }) { metric in
                                HStack { Text(metric.label).foregroundStyle(.secondary); Spacer(); Text(metric.value).monospacedDigit() }
                            }
                            if entry.id.category != .quests && entry.id.category != .monsters && !detail.description.isEmpty { Text(detail.description).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true) }
                            Text("编号 \(entry.id.id) · MHGenDatabase 离线快照").foregroundStyle(.tertiary)
                        }.font(.caption).padding(.top, 8)
                    }.font(.caption)
                }.padding(22).frame(maxWidth: 900, alignment: .leading).frame(maxWidth: .infinity)
            }
            .safeAreaInset(edge: .top, spacing: 0) {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 16) {
                        Button("概览") { proxy.scrollTo("top", anchor: .top) }
                        ForEach(sections) { section in Button(section.title) { openSections.insert(section.id); proxy.scrollTo(section.id, anchor: .top) } }
                    }.font(.system(size: 11)).buttonStyle(.plain).foregroundStyle(Color.dexAccent).padding(.horizontal, 22).padding(.vertical, 11)
                }.background(Color(nsColor: .controlBackgroundColor)).overlay(alignment: .bottom) { Divider() }
            }
        }.background(Color(nsColor: .windowBackgroundColor)).textSelection(.enabled)
    }
    private var header: some View {
        HStack(alignment: .center, spacing: 14) {
            EntryArtwork(entry: entry, size: entry.id.category == .monsters ? 70 : 36, portrait: entry.id.category == .monsters)
            VStack(alignment: .leading, spacing: 5) {
                Text(entry.name).font(.system(size: 23, weight: .semibold)).fixedSize(horizontal: false, vertical: true)
                if entry.name != entry.english { Text(entry.english).font(.caption).foregroundStyle(.secondary) }
                Text(entry.id.category == .quests ? entry.subtitle.components(separatedBy: " · ").prefix(2).joined(separator: " · ") : entry.subtitle).font(.caption).foregroundStyle(.secondary)
            }
            Spacer(minLength: 0)
        }
    }
}

enum DetailHierarchy {
    static func ordered(_ sections: [DetailSection], category: Category) -> [DetailSection] {
        let priority: [String] = category == .items ? ["可用素材", "狩猎获取", "地图采集", "任务报酬", "用于制作", "可计入素材类别"] : category == .quests ? ["任务信息", "出现怪物"] : []
        return sections.enumerated().sorted {
            let left = priority.firstIndex(of: $0.element.title) ?? priority.count
            let right = priority.firstIndex(of: $1.element.title) ?? priority.count
            return left == right ? $0.offset < $1.offset : left < right
        }.map(\.element)
    }
    static func isSecondary(_ title: String) -> Bool { ["用于制作", "可计入素材类别"].contains(title) }
}

struct DetailSectionPreview: View {
    let section: DetailSection
    @ObservedObject var store: DexStore
    var secondary = false
    @Binding var expanded: Bool
    @State private var showAll = false
    @State private var rank = "全部"
    private var ranks: [String] { ["下位", "上位", "G位"].filter { value in section.rows.contains { $0.subtitle.components(separatedBy: " · ").contains(value) } } }
    private var rows: [DetailLink] { rank == "全部" ? section.rows : section.rows.filter { $0.subtitle.components(separatedBy: " · ").contains(rank) } }
    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            if secondary {
                DisclosureGroup(isExpanded: $expanded) { contents } label: { heading }
            } else { heading; contents }
            Divider()
        }
    }
    private var heading: some View {
        HStack(spacing: 8) {
            Text(section.title).font(.system(size: 14, weight: .semibold))
            if !section.title.hasPrefix("属性弱点") { Text(rank == "全部" ? "\(section.rows.count)" : "\(rows.count) / \(section.rows.count)").font(.caption).foregroundStyle(.secondary) }
            Spacer()
        }
    }
    @ViewBuilder private var contents: some View {
        if ranks.count > 1 {
            Picker("位阶", selection: $rank) {
                Text("全部").tag("全部")
                ForEach(ranks, id: \.self) { Text($0).tag($0) }
            }.pickerStyle(.segmented).labelsHidden().frame(maxWidth: 270).onChange(of: rank) { _, _ in showAll = false }
        }
        if !section.note.isEmpty { Text(section.note).font(.system(size: 11)).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true) }
        if section.title.hasPrefix("属性弱点") {
            HStack {
                ForEach(section.rows) { row in
                    VStack(spacing: 6) { Text(row.title).font(.caption).foregroundStyle(.secondary); Text(row.trailing).font(.system(size: 17, weight: .medium)).monospacedDigit() }.frame(maxWidth: .infinity)
                }
            }.padding(.vertical, 5)
        } else {
            LazyVStack(spacing: 0) {
                ForEach(showAll ? rows : Array(rows.prefix(6))) { row in
                    if let destination = row.destination {
                        Button { store.navigate(destination) } label: { rowContent(row, navigable: true) }.buttonStyle(LinkButtonStyle())
                    } else { rowContent(row, navigable: false) }
                }
            }
            if rows.count > 6 {
                Button(showAll ? "收起列表" : "查看全部 \(rows.count) 条") { showAll.toggle() }.font(.caption).padding(.top, 4)
            }
        }
    }
    private func rowContent(_ row: DetailLink, navigable: Bool) -> some View {
        HStack(spacing: 9) {
            if let destination = row.destination, let linked = store.database?.index[destination] { EntryArtwork(entry: linked, size: 22) }
            VStack(alignment: .leading, spacing: 3) {
                Text(row.title).font(.system(size: 12, weight: .medium)).foregroundStyle(navigable ? Color.dexAccent : .primary).fixedSize(horizontal: false, vertical: true)
                if !row.subtitle.isEmpty { Text(row.subtitle).font(.system(size: 11)).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true) }
            }
            Spacer(minLength: 8)
            if !row.trailing.isEmpty { Text(row.trailing).font(.system(size: 12, weight: .medium)).monospacedDigit().multilineTextAlignment(.trailing) }
            if navigable { Image(systemName: "chevron.right").font(.system(size: 9)).foregroundStyle(.tertiary) }
        }.padding(.vertical, 8).frame(maxWidth: .infinity, alignment: .leading).contentShape(Rectangle())
    }
}

struct LinkButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.background(configuration.isPressed ? Color.dexAccent.opacity(0.1) : Color.clear)
    }
}

struct SharpnessBar: View {
    let values: [Int]
    let scale: Int
    private let colors: [Color] = [.red, .orange, .yellow, .green, .blue, .white, .purple]
    var body: some View {
        GeometryReader { geometry in
            HStack(spacing: 0) {
                ForEach(Array(values.prefix(7).enumerated()), id: \.offset) { index, value in
                    colors[index].frame(width: geometry.size.width * CGFloat(max(0, value)) / CGFloat(scale))
                }
                Spacer(minLength: 0)
            }.background(.black.opacity(0.15)).clipShape(RoundedRectangle(cornerRadius: 2))
                .overlay(RoundedRectangle(cornerRadius: 2).stroke(.gray.opacity(0.25), lineWidth: 0.5))
        }.accessibilityLabel("斩味：\(zip(["红", "橙", "黄", "绿", "蓝", "白", "紫"], values).map { "\($0.0) \($0.1)" }.joined(separator: "，"))")
    }
}
