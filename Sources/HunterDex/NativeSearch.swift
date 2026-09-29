import SwiftUI
import AppKit

struct NativeSearchField: NSViewRepresentable {
    @Binding var text: String
    var placeholder: String
    var submit: () -> Void
    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeNSView(context: Context) -> NSSearchField {
        let field = NSSearchField()
        field.placeholderString = placeholder
        field.delegate = context.coordinator
        field.sendsSearchStringImmediately = true
        field.sendsWholeSearchString = false
        field.target = context.coordinator
        field.action = #selector(Coordinator.action(_:))
        field.setAccessibilityIdentifier("catalog-search")
        context.coordinator.field = field
        return field
    }
    func updateNSView(_ field: NSSearchField, context: Context) {
        context.coordinator.parent = self; field.placeholderString = placeholder
        if !((field.currentEditor() as? NSTextView)?.hasMarkedText() ?? false) && field.stringValue != text { field.stringValue = text }
    }
    @MainActor final class Coordinator: NSObject, NSSearchFieldDelegate {
        var parent: NativeSearchField
        weak var field: NSSearchField?
        var observer: NSObjectProtocol?
        init(_ parent: NativeSearchField) {
            self.parent = parent
            super.init()
            observer = NotificationCenter.default.addObserver(forName: .dexFocusSearch, object: nil, queue: .main) { [weak self] _ in
                MainActor.assumeIsolated { if let field = self?.field, field.window != nil { field.window?.makeFirstResponder(field) } }
            }
        }
        func controlTextDidChange(_ obj: Notification) {
            guard let field, !((field.currentEditor() as? NSTextView)?.hasMarkedText() ?? false) else { return }
            parent.text = field.stringValue
        }
        @objc func action(_ sender: NSSearchField) {
            guard !((sender.currentEditor() as? NSTextView)?.hasMarkedText() ?? false) else { return }
            parent.text = sender.stringValue
            if NSApp.currentEvent?.type == .keyDown && NSApp.currentEvent?.keyCode == 36 { parent.submit() }
        }
        func dispose() { if let observer { NotificationCenter.default.removeObserver(observer) }; observer = nil }
    }
    static func dismantleNSView(_ nsView: NSSearchField, coordinator: Coordinator) { coordinator.dispose() }
}
