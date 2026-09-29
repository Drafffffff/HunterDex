import SwiftUI
import AppKit

@main
struct HunterDexApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var delegate
    @StateObject private var store = DexStore()

    init() {
        if CommandLine.arguments.contains("--self-test") {
            Task { @MainActor in
                do { try await SelfChecks.run(); exit(0) }
                catch { print("FAIL: \(error.localizedDescription)"); exit(1) }
            }
            dispatchMain()
        }
    }

    var body: some Scene {
        WindowGroup("猎人手册 · MHXX / MHGU") {
            ContentView(store: store)
                .frame(minWidth: 1040, minHeight: 660)
                .tint(.dexAccent)
        }
        .defaultSize(width: 1320, height: 860)
        .commands {
            CommandGroup(after: .textEditing) {
                Button("搜索当前分类") { NotificationCenter.default.post(name: .dexFocusSearch, object: nil) }
                    .keyboardShortcut("f", modifiers: .command)
            }
            CommandMenu("浏览") {
                Button("后退") { store.back() }.keyboardShortcut("[", modifiers: .command).disabled(!store.canGoBack)
                Button("前进") { store.forward() }.keyboardShortcut("]", modifiers: .command).disabled(!store.canGoForward)
                Divider()
                Button("收藏 / 取消收藏") { if let selected = store.selection { store.toggleFavorite(selected) } }
                    .keyboardShortcut("d", modifiers: .command).disabled(store.selection == nil)
            }
        }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

extension Notification.Name { static let dexFocusSearch = Notification.Name("dexFocusSearch") }
extension Color {
    static let dexAccent = Color(red: 0.17, green: 0.57, blue: 0.51)
    static let dexSurface = Color(nsColor: .controlBackgroundColor)
}
