import SwiftUI
import AppKit

@MainActor
final class ArtworkCache {
    static let shared = ArtworkCache()
    private var images: [String: NSImage] = [:]
    private var missing: Set<String> = []
    private let bundle: Bundle

    private init() {
        bundle = Bundle.main.resourceURL.flatMap { Bundle(url: $0.appendingPathComponent("HunterDex_HunterDex.bundle")) } ?? Bundle.module
    }

    func image(_ name: String) -> NSImage? {
        guard !name.isEmpty, !missing.contains(name) else { return nil }
        if let cached = images[name] { return cached }
        let resourceName = name == "icon_question_mark" ? "question_mark_grey" : name
        let file = resourceName.hasSuffix(".png") ? resourceName : resourceName + ".png"
        guard let url = bundle.resourceURL?.appendingPathComponent("Artwork").appendingPathComponent(file),
              let image = NSImage(contentsOf: url) else { missing.insert(name); return nil }
        images[name] = image
        return image
    }
}

struct EntryArtwork: View {
    let entry: Entry
    var size: CGFloat = 34
    var portrait = false

    private var tint: Color {
        // Preserve the grayscale shading and black outlines when applying the source palette.
        if entry.iconColor == 0 { return .white }
        let palette: [UInt32] = [0xffffff, 0xf85858, 0x70c888, 0x90b0f8, 0xf8d058, 0xb890c0, 0x98d8f0, 0xf89858, 0xe890a0, 0xc6f29f, 0xa0a0a0, 0xe2a626, 0x5cccff, 0x639929, 0xaa3c3c, 0x4066bb, 0x803a8e]
        let rgb = palette.indices.contains(entry.iconColor) ? palette[entry.iconColor] : 0x70c888
        return Color(red: Double((rgb >> 16) & 255) / 255, green: Double((rgb >> 8) & 255) / 255, blue: Double(rgb & 255) / 255)
    }

    var body: some View {
        Group {
            if portrait, let art = ArtworkCache.shared.image(entry.portraitName) {
                Image(nsImage: art).resizable().interpolation(.high).scaledToFit()
            } else if let icon = ArtworkCache.shared.image(entry.iconName) {
                if entry.destination.category == .monsters {
                    Image(nsImage: icon).resizable().interpolation(.high).scaledToFit()
                } else {
                    Image(nsImage: icon).resizable().renderingMode(.original).scaledToFit().colorMultiply(tint)
                }
            } else {
                Image(systemName: entry.destination.category.icon).resizable().scaledToFit().foregroundStyle(Color.dexAccent.opacity(0.7)).padding(size * 0.2)
            }
        }.frame(width: size, height: size)
            .accessibilityLabel(entry.name + (portrait && !entry.portraitName.isEmpty ? "插画" : "图标"))
            .help(entry.destination.category == .weapons || entry.destination.category == .armor ? "武器类别 / 防具部位图标；逐件外观图待补充" : entry.name)
    }
}
