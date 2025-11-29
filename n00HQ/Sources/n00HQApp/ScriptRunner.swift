import Foundation

@MainActor
final class ScriptRunner: ObservableObject {
    @Published var lastOutput: String = ""
    @Published var lastStatus: Int32 = 0

    func run(command: String, workingDir: URL? = WorkspaceLocator.workspaceRoot()) async {
        guard let work = workingDir else {
            lastOutput = "Workspace root not found"; lastStatus = -1; return
        }
        let process = Process()
        process.currentDirectoryURL = work
        process.executableURL = URL(fileURLWithPath: "/bin/bash")
        process.arguments = ["-c", command]

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe

        do {
            try process.run()
            let data = try await pipe.fileHandleForReading.readToEnd() ?? Data()
            process.waitUntilExit()
            lastStatus = process.terminationStatus
            lastOutput = String(decoding: data, as: UTF8.self)
        } catch {
            lastOutput = "Failed: \(error)"; lastStatus = -1
        }
    }
}
