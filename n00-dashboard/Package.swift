// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "n00Dashboard",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "DashboardApp", targets: ["DashboardApp"])
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "DashboardApp",
            path: "Sources/DashboardApp"
        ),
        .testTarget(
            name: "DashboardAppTests",
            dependencies: ["DashboardApp"],
            path: "Tests/DashboardAppTests"
        )
    ]
)
