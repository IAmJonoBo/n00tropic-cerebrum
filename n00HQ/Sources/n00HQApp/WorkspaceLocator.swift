import Foundation

enum WorkspaceLocator {
    static func workspaceRoot() -> URL? {
        // Heuristic: climb from bundle to find n00tropic-cerebrum marker files
        var url = Bundle.main.bundleURL
        let markers = ["scripts", "package.json", ".dev", "pnpm-workspace.yaml"]
        for _ in 0..<8 {
            let markerHits = markers.filter { FileManager.default.fileExists(atPath: url.appendingPathComponent($0).path) }
            if !markerHits.isEmpty { return url }
            url.deleteLastPathComponent()
        }
        return nil
    }
}
