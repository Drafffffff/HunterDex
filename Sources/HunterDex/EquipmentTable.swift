import SwiftUI
import AppKit

// AppKit owns row reuse, scrolling and keyboard expansion. SwiftUI owns the surrounding workspace.
struct EquipmentTable: NSViewRepresentable {
    @ObservedObject var store: DexStore
    func makeCoordinator() -> Coordinator { Coordinator(store: store) }
    func makeNSView(context: Context) -> NSScrollView {
        let scroll = NSScrollView()
        scroll.hasVerticalScroller = true; scroll.hasHorizontalScroller = true
        scroll.autohidesScrollers = true
        let table = ConnectedOutlineView()
        table.style = .fullWidth
        table.rowHeight = 60; table.intercellSpacing = NSSize(width: 10, height: 3)
        table.indentationPerLevel = 7
        table.usesAlternatingRowBackgroundColors = true
        table.allowsMultipleSelection = false
        table.columnAutoresizingStyle = .noColumnAutoresizing
        table.delegate = context.coordinator; table.dataSource = context.coordinator
        table.setAccessibilityIdentifier("equipment-table")
        scroll.documentView = table
        context.coordinator.table = table
        scroll.contentView.postsBoundsChangedNotifications = true
        NotificationCenter.default.addObserver(context.coordinator, selector: #selector(Coordinator.didScroll(_:)), name: NSView.boundsDidChangeNotification, object: scroll.contentView)
        context.coordinator.update(store)
        return scroll
    }
    func updateNSView(_ view: NSScrollView, context: Context) { context.coordinator.update(store) }

    static func dismantleNSView(_ view: NSScrollView, coordinator: Coordinator) {
        NotificationCenter.default.removeObserver(coordinator)
    }

    @MainActor final class Node: NSObject {
        let entry: Entry
        var children: [Node] = []
        init(_ entry: Entry) { self.entry = entry }
    }
    @MainActor final class Coordinator: NSObject, NSOutlineViewDataSource, NSOutlineViewDelegate {
        var store: DexStore
        weak var table: NSOutlineView?
        var nodes: [Int: Node] = [:]
        var roots: [Node] = []
        var contextKey = ""
        var lastIDs: [Destination] = []
        var lastMode = false
        var lastSharp = -1
        var lastSelection: Destination?
        var updating = false
        var currentCategory: Category?
        var lastScope = ""
        init(store: DexStore) { self.store = store }
        @objc func didScroll(_ notification: Notification) {
            guard !updating, let table, let node = table.item(atRow: max(0, table.rows(in: table.visibleRect).location)) as? Node else { return }
            store.scrollID = node.entry.id.id
        }
        func columns(_ category: Category, ranged: Bool) {
            guard let table else { return }
            table.columnAutoresizingStyle = [.weapons, .armor].contains(category) ? .noColumnAutoresizing : .firstColumnOnlyAutoresizingStyle
            let definitions: [(String, String, CGFloat)] = category == .weapons ? [
                ("name", "武器 / 强化等级", 250), ("attack", "攻击", 48), ("sharp", ranged ? "武器特性" : "斩味 · \(["通常", "匠 +1", "匠 +2"][store.sharpnessMode])", 128), ("element", "属性", 65), ("affinity", "会心", 42), ("slots", "孔位", 42)
            ] : category == .armor ? [("name", "防具 / 技能点贡献", 270), ("defense", "初始 → 满强化", 108), ("slots", "孔位", 48), ("resists", "火 / 水 / 雷 / 冰 / 龙", 154)] : [("name", "名称", 300)]
            // NSOutlineView retains its outline column when asked to remove it.
            // Reconfigure columns in place so category changes cannot duplicate it.
            while table.tableColumns.count > definitions.count { table.removeTableColumn(table.tableColumns.last!) }
            while table.tableColumns.count < definitions.count { table.addTableColumn(NSTableColumn(identifier: NSUserInterfaceItemIdentifier("column-\(table.tableColumns.count)"))) }
            for (index, definition) in definitions.enumerated() {
                let (id, title, width) = definition
                let column = table.tableColumns[index]
                column.identifier = NSUserInterfaceItemIdentifier(id)
                column.title = title; column.minWidth = id == "name" ? 200 : 40; column.width = width
                column.resizingMask = .userResizingMask
            }
            table.outlineTableColumn = table.tableColumns.first
        }
        func update(_ newStore: DexStore) {
            store = newStore
            guard let table, let db = store.database else { return }
            let tree = store.category == .weapons && store.treeMode
            let ids = store.visible.map(\.id)
            let changedContext = contextKey != store.contextKey
            let structure = changedContext || ids != lastIDs || tree != lastMode
            updating = true
            defer { updating = false }
            if currentCategory != store.category || lastScope != store.scope {
                columns(store.category, ranged: ["Bow", "Light Bowgun", "Heavy Bowgun"].contains(store.scope))
                currentCategory = store.category; lastScope = store.scope
            }
            if structure {
                if !changedContext, let node = table.item(atRow: max(0, table.rows(in: table.visibleRect).location)) as? Node { store.scrollID = node.entry.id.id }
                nodes = [:]; roots = []
                var included = Set(ids.map(\.id))
                if tree {
                    // Retain ancestors as context when filtering; never invent a shortened edge.
                    for id in Array(included) {
                        var parent = db.weapons[id]?.parent
                        var visited: Set<Int> = []
                        while let value = parent, visited.insert(value).inserted, let weapon = db.weapons[value], store.scope == "all" || weapon.type == store.scope {
                            included.insert(value); parent = weapon.parent
                        }
                    }
                    if let selected = store.selection, selected.category == .weapons, let entry = db.index[selected], store.scope == "all" || entry.filter == store.scope {
                        included.insert(selected.id)
                        var parent = db.weapons[selected.id]?.parent
                        var seen: Set<Int> = []
                        while let id = parent, seen.insert(id).inserted { included.insert(id); parent = db.weapons[id]?.parent }
                    }
                }
                let ordered: [Entry] = tree ? included.sorted().compactMap { db.index[Destination(category: .weapons, id: $0)] } : store.visible
                for entry in ordered { nodes[entry.id.id] = Node(entry) }
                for entry in ordered {
                    guard let node = nodes[entry.id.id] else { continue }
                    if tree, let parent = db.weapons[entry.id.id]?.parent, let parentNode = nodes[parent] { parentNode.children.append(node) }
                    else { roots.append(node) }
                }
                contextKey = store.contextKey; lastIDs = ids; lastMode = tree
                table.reloadData()
                let expand = store.expanded
                func expandBranch(_ node: Node) {
                    if expand.contains(node.entry.id.id) {
                        table.expandItem(node)
                        for child in node.children { expandBranch(child) }
                    }
                }
                for node in roots { expandBranch(node) }
                if let scrollID = store.scrollID, let node = nodes[scrollID], table.row(forItem: node) >= 0 { table.scrollRowToVisible(table.row(forItem: node)) }
            }
            if lastSharp != store.sharpnessMode {
                lastSharp = store.sharpnessMode
                if store.category == .weapons {
                    table.tableColumns.first(where: { $0.identifier.rawValue == "sharp" })?.title = ["Bow", "Light Bowgun", "Heavy Bowgun"].contains(store.scope) ? "武器特性" : "斩味 · \(["通常", "匠 +1", "匠 +2"][store.sharpnessMode])"
                    table.reloadData(forRowIndexes: IndexSet(integersIn: 0..<table.numberOfRows), columnIndexes: IndexSet(integer: 2))
                }
            }
            if tree {
                func restore(_ node: Node) {
                    if store.expanded.contains(node.entry.id.id) {
                        table.expandItem(node)
                        for child in node.children { restore(child) }
                    } else { table.collapseItem(node, collapseChildren: true) }
                }
                for root in roots { restore(root) }
            }
            if let selected = store.selection, let node = nodes[selected.id] {
                let row = table.row(forItem: node)
                if row >= 0 {
                    table.selectRowIndexes(IndexSet(integer: row), byExtendingSelection: false)
                    if selected != lastSelection { table.scrollRowToVisible(row) }
                }
            } else { table.deselectAll(nil) }
            lastSelection = store.selection
        }
        func outlineView(_ outlineView: NSOutlineView, numberOfChildrenOfItem item: Any?) -> Int { (item as? Node)?.children.count ?? roots.count }
        func outlineView(_ outlineView: NSOutlineView, isItemExpandable item: Any) -> Bool { !((item as? Node)?.children.isEmpty ?? true) }
        func outlineView(_ outlineView: NSOutlineView, child index: Int, ofItem item: Any?) -> Any { (item as? Node)?.children[index] ?? roots[index] }
        func outlineViewSelectionDidChange(_ notification: Notification) {
            guard !updating, let table, let node = table.item(atRow: table.selectedRow) as? Node else { return }
            if let top = table.item(atRow: max(0, table.rows(in: table.visibleRect).location)) as? Node { store.scrollID = top.entry.id.id }
            store.navigate(node.entry.id)
        }
        func outlineViewItemDidExpand(_ notification: Notification) {
            guard !updating, let node = notification.userInfo?["NSObject"] as? Node else { return }; store.setBranchExpanded(true, root: node.entry.id.id)
        }
        func outlineViewItemDidCollapse(_ notification: Notification) {
            guard !updating, let node = notification.userInfo?["NSObject"] as? Node else { return }; store.setBranchExpanded(false, root: node.entry.id.id)
        }
        func outlineView(_ outlineView: NSOutlineView, viewFor tableColumn: NSTableColumn?, item: Any) -> NSView? {
            guard let node = item as? Node, let column = tableColumn, let db = store.database else { return nil }
            let entry = node.entry
            let weapon = db.weapons[entry.id.id]; let armor = db.armors[entry.id.id]
            let key = column.identifier.rawValue
            if key == "sharp", let weapon, !weapon.ranged {
                let view = (outlineView.makeView(withIdentifier: column.identifier, owner: self) as? NativeSharpnessView) ?? NativeSharpnessView()
                view.identifier = column.identifier
                view.values = weapon.sharpness.indices.contains(store.sharpnessMode) ? weapon.sharpness[store.sharpnessMode] : []
                view.needsDisplay = true
                view.toolTip = view.values.isEmpty ? "未收录斩味" : zip(["红", "橙", "黄", "绿", "蓝", "白", "紫"], view.values).map { "\($0.0) \($0.1)" }.joined(separator: " · ") + "（数据库段长）"
                view.setAccessibilityLabel(view.toolTip)
                return view
            }
            let reuseID = NSUserInterfaceItemIdentifier("text-" + key)
            let cell = (outlineView.makeView(withIdentifier: reuseID, owner: self) as? EquipmentTextCell) ?? EquipmentTextCell()
            cell.identifier = reuseID
            var title = ""; var subtitle = ""
            switch key {
            case "name":
                title = entry.name
                subtitle = entry.subtitle + (entry.rarity > 0 ? " · R\(entry.rarity)" : "")
                if let weapon { subtitle = "R\(entry.rarity)" + (entry.final ? " · 最终强化" : "") + (weapon.creationCost > 0 ? " · 可生产" : "") }
                if let armor { subtitle = armor.summary.isEmpty ? "无技能点 · \(armor.hunterLabel)" : armor.summary }
            case "attack": title = "\(weapon?.attack ?? 0)"
            case "element": title = weapon?.elements.isEmpty == false ? weapon!.elements : "—"
            case "affinity": title = (weapon?.affinity ?? "0") + "%"
            case "slots": let n = weapon?.slots ?? armor?.slots ?? 0; title = n == 0 ? "无孔" : String(repeating: "●", count: n); subtitle = n > 0 ? "\(n) 孔" : ""
            case "sharp": title = weapon?.special.isEmpty == false ? weapon!.special : "见详情"
            case "defense": title = "\(armor?.defense ?? 0) → \(armor?.maximum ?? 0)"
            case "resists": title = armor?.resistances.map(signed).joined(separator: "   ") ?? ""
            default: break
            }
            cell.configure(title: title, subtitle: subtitle, numeric: key != "name" && key != "element" && key != "sharp")
            cell.title.textColor = key == "name" && store.category == .weapons && !store.visible.contains(where: { $0.id == entry.id }) ? .secondaryLabelColor : .labelColor
            cell.icon.image = key == "name" && ![Category.weapons, .armor].contains(store.category) ? ArtworkCache.shared.image(entry.iconName) : nil
            cell.needsLayout = true
            cell.toolTip = key == "name" ? entry.name + "\n" + entry.english + "\n" + subtitle : title
            return cell
        }
    }
}

final class EquipmentTextCell: NSTableCellView {
    let title = NSTextField(labelWithString: "")
    let subtitle = NSTextField(labelWithString: "")
    let icon = NSImageView()
    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        title.lineBreakMode = .byTruncatingTail; title.maximumNumberOfLines = 2
        title.cell?.wraps = true; title.cell?.isScrollable = false
        subtitle.font = .systemFont(ofSize: 10); subtitle.textColor = .secondaryLabelColor
        subtitle.lineBreakMode = .byTruncatingTail
        addSubview(title); addSubview(subtitle); addSubview(icon)
        textField = title
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    func configure(title: String, subtitle: String, numeric: Bool) {
        self.title.stringValue = title; self.subtitle.stringValue = subtitle
        self.title.font = numeric ? .monospacedDigitSystemFont(ofSize: 12, weight: .regular) : .systemFont(ofSize: 12, weight: .medium)
        self.subtitle.isHidden = subtitle.isEmpty
        needsLayout = true
    }
    override func layout() {
        super.layout()
        let leading: CGFloat = icon.image == nil ? 0 : 36
        icon.frame = NSRect(x: 0, y: 12, width: 28, height: 28)
        title.frame = NSRect(x: leading, y: subtitle.isHidden ? 14 : 24, width: bounds.width - leading, height: 30)
        subtitle.frame = NSRect(x: leading, y: 9, width: bounds.width - leading, height: 14)
    }
}
final class NativeSharpnessView: NSView {
    var values: [Int] = []
    override func draw(_ dirtyRect: NSRect) {
        let bar = NSRect(x: 1, y: (bounds.height - 11) / 2, width: max(1, bounds.width - 7), height: 11)
        NSColor.quaternaryLabelColor.setFill(); NSBezierPath(roundedRect: bar, xRadius: 2, yRadius: 2).fill()
        let colors: [NSColor] = [.systemRed, .systemOrange, .systemYellow, .systemGreen, .systemBlue, .white, .systemPurple]
        var x = bar.minX
        for (index, value) in values.prefix(7).enumerated() {
            let width = bar.width * CGFloat(max(0, value)) / 45
            colors[index].setFill(); NSRect(x: x, y: bar.minY, width: width, height: bar.height).fill(); x += width
        }
        NSColor.separatorColor.setStroke(); NSBezierPath(rect: bar).stroke()
    }
}

final class ConnectedOutlineView: NSOutlineView {
    override func drawBackground(inClipRect clipRect: NSRect) {
        super.drawBackground(inClipRect: clipRect)
        let visible = rows(in: clipRect)
        guard visible.location != NSNotFound else { return }
        NSColor.separatorColor.setStroke()
        let path = NSBezierPath(); path.lineWidth = 1
        for row in visible.location..<min(numberOfRows, visible.location + visible.length) {
            guard let node = item(atRow: row), let parent = parent(forItem: node) else { continue }
            let depth = level(forItem: node)
            let frame = rect(ofRow: row)
            let parentRow = self.row(forItem: parent)
            let parentY = parentRow >= 0 ? rect(ofRow: parentRow).midY : clipRect.minY
            let x = CGFloat(depth) * indentationPerLevel + 8
            path.move(to: NSPoint(x: x, y: max(parentY, clipRect.minY)))
            path.line(to: NSPoint(x: x, y: frame.midY))
            path.line(to: NSPoint(x: x + 5, y: frame.midY))
        }
        path.stroke()
    }
}
