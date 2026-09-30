// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "HunterDex",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "HunterDex", targets: ["HunterDex"])],
    targets: [
        .systemLibrary(name: "CSQLite"),
        .executableTarget(name: "HunterDex", dependencies: ["CSQLite"], resources: [.copy("Resources/mhgu.db"), .copy("Resources/zh.json"), .copy("Resources/localization.json"), .copy("Resources/linked-localization.json"), .copy("Resources/description-localization.json"), .copy("Resources/artwork.json"), .copy("Resources/Artwork"), .copy("Resources/MHGenDatabase-LICENSE.txt"), .copy("Resources/CommunityData-LICENSE.txt")])
    ]
)
