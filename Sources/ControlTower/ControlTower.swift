import Foundation

@main
struct ControlTower {
    private static let packageRoot: URL = {
        // .../Sources/ControlTower/ControlTower.swift -> repo root
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent() // ControlTower.swift
            .deletingLastPathComponent() // ControlTower
            .deletingLastPathComponent() // Sources
    }()

    private static let cortexRoot = packageRoot.appendingPathComponent("n00-cortex")

    private static let commands: [String: String] = [
        "status": "Show detected workspace paths",
        "validate-cortex": "Run pnpm schema/data validation in n00-cortex",
        "graph-live": "Rebuild catalog graph with live workspace inputs",
        "graph-stub": "Rebuild catalog graph using in-repo assets only",
        "sync-n00menon": "Pull docs updates from n00menon into the workspace",
        "help": "Show available commands",
    ]

    static func main() {
        let args = CommandLine.arguments.dropFirst()
        guard let command = args.first else {
            printUsage()
            return
        }

        switch command {
        case "status":
            printStatus()
        case "validate-cortex":
            runCortex(["npx", "pnpm@10.23.0", "run", "validate:schemas"])
        case "graph-live":
            runCortex(["node", "scripts/build-graph.mjs"])
        case "graph-stub":
            runCortex(["node", "scripts/build-graph.mjs", "--stub"])
        case "sync-n00menon":
            runWorkspace(["pnpm", "run", "docs:sync-n00menon", "--write"])
        case "help", "-h", "--help":
            printUsage()
        default:
            print("Unknown command: \(command)\n")
            printUsage()
        }
    }

    @discardableResult
    private static func runWorkspace(_ arguments: [String]) -> Int32 {
        return runCommand(workingDirectory: packageRoot, arguments: arguments)
    }

    private static func printUsage() {
        print("""
        ControlTower - superproject control CLI

        Usage: control-tower <command>

        Commands:
        \(commands.sorted { $0.key < $1.key }.map { "  \($0.key.padding(toLength: 16, withPad: " ", startingAt: 0)) \($0.value)" }.joined(separator: "\n"))

        Examples:
          control-tower status
          control-tower validate-cortex
          control-tower graph-stub
        """)
    }

    private static func printStatus() {
        let fm = FileManager.default
        let exists = fm.fileExists(atPath: cortexRoot.path)
        print("Workspace root: \(packageRoot.path)")
        print("cortex path:    \(cortexRoot.path) \(exists ? "(found)" : "(missing)")")
    }

    @discardableResult
    private static func runCortex(_ arguments: [String]) -> Int32 {
        guard FileManager.default.fileExists(atPath: cortexRoot.path) else {
            print("n00-cortex not found at \(cortexRoot.path)")
            return 1
        }

        let status = runCommand(
            workingDirectory: cortexRoot,
            arguments: arguments
        )
        if status != 0 {
            print("command exited with status \(status)")
        }
        return status
    }

    @discardableResult
    private static func runCommand(workingDirectory: URL, arguments: [String]) -> Int32 {
        let process = Process()
        process.currentDirectoryURL = workingDirectory
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = arguments
        process.standardOutput = FileHandle.standardOutput
        process.standardError = FileHandle.standardError

        do {
            try process.run()
            process.waitUntilExit()
            return process.terminationStatus
        } catch {
            fputs("Failed to run command \(arguments.joined(separator: " ")): \(error)\n", stderr)
            return 1
        }
    }
}
