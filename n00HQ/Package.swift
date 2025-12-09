// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "n00HQ",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "n00hq", targets: ["n00HQApp"])
    ],
    targets: [
        .executableTarget(
            name: "n00HQApp",
            resources: [.process("Resources"), .process("AppIcon.xcassets")]
        ),
        .testTarget(
            name: "n00HQAppTests",
            dependencies: ["n00HQApp"]
        )
    ]
)
