import SwiftUI
import AppKit

enum Dashboard {
    struct Log {
        static func debug(_ message: String) { print("[DEBUG] \(message)") }
        static func info(_ message: String) { print("[INFO] \(message)") }
        static func warn(_ message: String) { print("[WARN] \(message)") }
        static func error(_ message: String) { print("[ERROR] \(message)") }
    }

    actor FileIO {
        func readData(from url: URL) throws -> Data {
            return try Data(contentsOf: url)
        }
        func fileSize(at url: URL) -> Int64? {
            if let number = (try? FileManager.default.attributesOfItem(atPath: url.path()))?[.size] as? NSNumber {
                return number.int64Value
            }
            return nil
        }
    }

    @MainActor
    final class ViewModel: ObservableObject {
        enum Selection: Hashable {
            case chat
            case metaCheck
            case dependencies
            case overrides
            case agents
        }

        private let selectionDefaultsKey = "Dashboard.Selection"
        @Published var selection: Selection = .chat {
            didSet {
                UserDefaults.standard.set(selection.storageKey, forKey: selectionDefaultsKey)
            }
        }

        @Published var isLoadingMetaCheck = false
        @Published var isLoadingDependencies = false
        @Published var isLoadingOverrides = false
        @Published var isLoadingAgentRuns = false
        @Published var isLoadingCapabilities = false
        @Published var isRefreshing = false
        @Published var reduceMotion: Bool = UserDefaults.standard.object(forKey: "Dashboard.ReduceMotion") as? Bool ?? false {
            didSet { UserDefaults.standard.set(reduceMotion, forKey: "Dashboard.ReduceMotion") }
        }

        @Published var animateStatusDot: Bool = UserDefaults.standard.object(forKey: "Dashboard.AnimateStatusDot") as? Bool ?? true {
            didSet { UserDefaults.standard.set(animateStatusDot, forKey: "Dashboard.AnimateStatusDot") }
        }
        @Published var refreshDetailText: String? = nil
        @Published var capabilities: [Capability] = []
        @Published var capabilityError: String?
        @Published var messages: [ChatMessage] = ChatMessage.defaultTranscript
        @Published var isExecutingCapability = false
        @Published var activeCapabilityId: String?

        var refreshStatusText: String? {
            guard isRefreshing else { return nil }
            return refreshDetailText ?? "Refreshing…"
        }

        enum StatusIndicator: String, Codable {
            case ok
            case warning
            case failed
            case skipped
            case informational
            case unknown

            var label: String {
                rawValue.capitalized
            }

            var color: Color {
                switch self {
                case .ok: return .green
                case .warning: return .orange
                case .failed: return .red
                case .skipped: return .gray
                case .informational: return .blue
                case .unknown: return .secondary
                }
            }

            private var priority: Int {
                switch self {
                case .failed: return 0
                case .warning: return 1
                case .informational: return 2
                case .ok: return 3
                case .skipped: return 4
                case .unknown: return 5
                }
            }

            static func dominant(_ lhs: StatusIndicator, _ rhs: StatusIndicator) -> StatusIndicator {
                return lhs.priority <= rhs.priority ? lhs : rhs
            }

            init(statusCode: Dashboard.StatusCode) {
                switch statusCode {
                case .ok, .succeeded: self = .ok
                case .drift, .warning, .moderate, .partial: self = .warning
                case .failed, .critical: self = .failed
                case .skipped: self = .skipped
                case .informational: self = .informational
                }
            }
        }

        struct MetaCheckState {
            struct Check: Identifiable {
                let id: String
                let description: String
                let status: StatusIndicator
                let durationSeconds: Int
                let notes: String?
            }

            var statusIndicator: StatusIndicator
            var summary: String
            var lastRun: Date?
            var logPath: String?
            var checks: [Check]

            static var empty: MetaCheckState {
                MetaCheckState(
                    statusIndicator: .unknown,
                    summary: "No meta-check run detected yet.",
                    lastRun: nil,
                    logPath: nil,
                    checks: []
                )
            }
        }

        struct Capability: Identifiable, Hashable {
            let id: String
            let summary: String
            let entrypoint: URL
            let supportsCheck: Bool
            let origin: String
        }

        enum ChatRole: String, Codable {
            case system
            case user
            case assistant
            case event
        }

        enum StreamChannel: String, Codable {
            case transcript
            case stdout
            case stderr
        }

        struct ChatMessage: Identifiable, Codable {
            let id: UUID
            let role: ChatRole
            let text: String
            let timestamp: Date
            let status: StatusIndicator?
            let capabilityId: String?
            let stream: StreamChannel

            static var defaultTranscript: [ChatMessage] {
                [ChatMessage(role: .system,
                             text: "Welcome to n00t Control Centre. Pick a capability from the panel or free-type a request to orchestrate workspace automation.",
                             status: .informational,
                             capabilityId: nil,
                             stream: .transcript)]
            }

            init(id: UUID = UUID(),
                 role: ChatRole,
                 text: String,
                 timestamp: Date = Date(),
                 status: StatusIndicator?,
                 capabilityId: String?,
                 stream: StreamChannel = .transcript) {
                self.id = id
                self.role = role
                self.text = text
                self.timestamp = timestamp
                self.status = status
                self.capabilityId = capabilityId
                self.stream = stream
            }

            func appending(_ text: String) -> ChatMessage {
                let combined = self.text + text
                return ChatMessage(id: id,
                                   role: role,
                                   text: combined,
                                   timestamp: Date(),
                                   status: status,
                                   capabilityId: capabilityId,
                                   stream: stream)
            }
        }

        struct DependencyDashboard {
            struct Risk: Identifiable {
                let id = UUID()
                let name: String
                let severity: StatusIndicator
                let summary: String
            }

            var status: StatusIndicator
            var repositoryCount: Int
            var pendingPRs: Int?
            var findings: [String]
            var risks: [Risk]

            static var empty: DependencyDashboard {
                DependencyDashboard(status: .unknown, repositoryCount: 0, pendingPRs: nil, findings: [], risks: [])
            }
        }

        struct OverrideSummary: Identifiable {
            struct Entry: Identifiable {
                let id = UUID()
                let tool: String
                let version: String
                let reason: String?
                let expires: Date?
                let status: StatusIndicator
            }

            let id = UUID()
            let project: String
            let summary: String?
            let entries: [Entry]
        }

        struct AgentRun: Identifiable {
            let id: UUID
            let capability: String
            let status: StatusIndicator
            let summary: String
            let started: Date
            let logPath: String?
        }

        @Published var metaCheckState: MetaCheckState = .empty
        @Published var dependencyDashboard: DependencyDashboard = .empty
        @Published var overrideSummaries: [OverrideSummary] = []
        @Published var agentRuns: [AgentRun] = []
        @Published var workspaceWarning: String?

        private let decoder: JSONDecoder
        private let isoDayDecoder: JSONDecoder
        private let transcriptDecoder: JSONDecoder
        private var workspacePaths: Paths?
        private let fileIO = FileIO()
        private let maxFileSizeBytes: Int64 = 25 * 1024 * 1024 // 25 MB safety threshold
        private var activeProcess: Process?

        // MARK: - Workspace management helpers
        var currentRootPath: String? {
            workspacePaths?.root.path(percentEncoded: false)
        }

        func setWorkspaceRoot(_ url: URL) {
            UserDefaults.standard.set(url.path(percentEncoded: false), forKey: "Dashboard.RootPath")
            Dashboard.Log.info("Workspace root set to: \(url.path(percentEncoded: false))")
            self.workspacePaths = Paths(root: url)
            self.workspaceWarning = nil
            self.loadTranscript(for: self.workspacePaths)
        }

        func resetWorkspaceRoot() {
            UserDefaults.standard.removeObject(forKey: "Dashboard.RootPath")
            Dashboard.Log.info("Workspace root reset to auto-detect")
            self.workspacePaths = Paths.resolve()
            if self.workspacePaths == nil {
                self.workspaceWarning = "Unable to locate the workspace root. Launch the dashboard from inside any repo within n00tropic-cerebrum."
            } else {
                self.workspaceWarning = nil
                self.loadTranscript(for: self.workspacePaths)
            }
        }

        func useCurrentDirectoryAsRoot() {
            let cwdPath = FileManager.default.currentDirectoryPath
            let url = URL(fileURLWithPath: cwdPath, isDirectory: true)
            setWorkspaceRoot(url)
        }

        init() {
            self.decoder = JSONDecoder()
            self.decoder.dateDecodingStrategy = .iso8601

            self.isoDayDecoder = JSONDecoder()
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"
            formatter.timeZone = TimeZone(secondsFromGMT: 0)
            self.isoDayDecoder.dateDecodingStrategy = .formatted(formatter)

            self.transcriptDecoder = JSONDecoder()
            self.transcriptDecoder.dateDecodingStrategy = .iso8601

            self.workspacePaths = Paths.resolve()
            if workspacePaths == nil {
                workspaceWarning = "Unable to locate the workspace root. Launch the dashboard from inside any repo within n00tropic-cerebrum."
            }

            let stored = UserDefaults.standard.string(forKey: selectionDefaultsKey)
            self.selection = Selection(storageKey: stored ?? Selection.chat.storageKey)
            self.loadTranscript(for: self.workspacePaths)
        }

        func refresh() async {
            // Re-resolve workspace on each refresh in case user configured it
            self.workspacePaths = Paths.resolve()
            if self.workspacePaths == nil {
                await MainActor.run { self.workspaceWarning = "Unable to locate the workspace root. Launch the dashboard from inside any repo within n00tropic-cerebrum." }
                return
            } else {
                await MainActor.run { self.workspaceWarning = nil }
            }
            guard workspacePaths != nil else { return }
            if Task.isCancelled { return }
            await MainActor.run { 
                self.isRefreshing = true
                self.refreshDetailText = "Refreshing…"
            }
            Dashboard.Log.info("Refresh started")
            guard let paths = workspacePaths else { await MainActor.run { self.isRefreshing = false }; return }
            await withTaskGroup(of: Void.self) { group in
                group.addTask { [weak self] in
                    guard let self, !Task.isCancelled else { return }
                    await MainActor.run { self.refreshDetailText = "Refreshing capabilities…" }
                    Dashboard.Log.debug("Refreshing capabilities manifest…")
                    await self.fetchCapabilities(paths: paths)
                    await MainActor.run { if self.isRefreshing { self.refreshDetailText = nil } }
                }
                group.addTask { [weak self] in
                    guard let self, !Task.isCancelled else { return }
                    await MainActor.run { self.refreshDetailText = "Refreshing meta-checks…" }
                    Dashboard.Log.debug("Fetching meta-check…")
                    await self.fetchMetaCheck(paths: paths)
                    await MainActor.run { if self.isRefreshing { self.refreshDetailText = nil } }
                    Dashboard.Log.debug("Fetched meta-check")
                }
                group.addTask { [weak self] in
                    guard let self, !Task.isCancelled else { return }
                    await MainActor.run { self.refreshDetailText = "Refreshing dependencies…" }
                    Dashboard.Log.debug("Fetching dependencies…")
                    await self.fetchDependencies(paths: paths)
                    await MainActor.run { if self.isRefreshing { self.refreshDetailText = nil } }
                    Dashboard.Log.debug("Fetched dependencies")
                }
                group.addTask { [weak self] in
                    guard let self, !Task.isCancelled else { return }
                    await MainActor.run { self.refreshDetailText = "Refreshing overrides…" }
                    Dashboard.Log.debug("Fetching overrides…")
                    await self.fetchOverrides(paths: paths)
                    await MainActor.run { if self.isRefreshing { self.refreshDetailText = nil } }
                    Dashboard.Log.debug("Fetched overrides")
                }
                group.addTask { [weak self] in
                    guard let self, !Task.isCancelled else { return }
                    await MainActor.run { self.refreshDetailText = "Refreshing agent runs…" }
                    Dashboard.Log.debug("Fetching agent runs…")
                    await self.fetchAgentRuns(paths: paths)
                    await MainActor.run { if self.isRefreshing { self.refreshDetailText = nil } }
                    Dashboard.Log.debug("Fetched agent runs")
                }
            }
            if Task.isCancelled {
                await MainActor.run { self.isRefreshing = false }
                Dashboard.Log.warn("Refresh cancelled")
                return
            }
            await MainActor.run {
                self.refreshDetailText = nil
                self.isRefreshing = false
            }
            Dashboard.Log.info("Refresh finished")
        }

        private func fetchMetaCheck(paths: Paths) async {
            if Task.isCancelled {
                Dashboard.Log.warn("Meta-check load cancelled")
                return
            }
            await MainActor.run { self.isLoadingMetaCheck = true }
            defer {
                Task { @MainActor in
                    self.isLoadingMetaCheck = false
                }
            }
            Dashboard.Log.debug("Loading meta-check report…")
            do {
                let start = Date()
                if let size = await fileIO.fileSize(at: paths.metaCheckReport), size > maxFileSizeBytes {
                    Dashboard.Log.warn("Meta-check report is large: \(size) bytes")
                }
                let data = try await fileIO.readData(from: paths.metaCheckReport)
                if Task.isCancelled {
                    Dashboard.Log.warn("Meta-check load cancelled")
                    return
                }
                let report = try decoder.decode(MetaCheckReport.self, from: data)
                Dashboard.Log.debug("Meta-check read+decode took \(Date().timeIntervalSince(start))s")
                if Task.isCancelled {
                    Dashboard.Log.warn("Meta-check load cancelled")
                    return
                }
                let checks = report.checks.map {
                    MetaCheckState.Check(
                        id: $0.id,
                        description: $0.description,
                        status: StatusIndicator(statusCode: $0.status),
                        durationSeconds: $0.durationSeconds,
                        notes: $0.notes
                    )
                }
                let state = MetaCheckState(
                    statusIndicator: StatusIndicator(statusCode: report.status),
                    summary: report.summary,
                    lastRun: report.completed,
                    logPath: report.logPath,
                    checks: checks
                )
                Dashboard.Log.debug("Meta-check decoded: \(checks.count) checks, status: \(state.statusIndicator.label)")
                await MainActor.run {
                    if Task.isCancelled { return }
                    self.metaCheckState = state
                }
            } catch {
                Dashboard.Log.error("Meta-check load failed: \(error)")
                await MainActor.run {
                    if Task.isCancelled { return }
                    self.metaCheckState = .empty
                }
            }
        }

        private func fetchDependencies(paths: Paths) async {
            if Task.isCancelled {
                Dashboard.Log.warn("Dependencies load cancelled")
                return
            }
            await MainActor.run { self.isLoadingDependencies = true }
            defer {
                Task { @MainActor in
                    self.isLoadingDependencies = false
                }
            }
            Dashboard.Log.debug("Loading dependencies dashboard…")
            var repositoryCount = 0
            do {
                let s = Date()
                if let size = await fileIO.fileSize(at: paths.toolchainManifest), size > maxFileSizeBytes {
                    Dashboard.Log.warn("Toolchain manifest large: \(size) bytes")
                }
                let manifestData = try await fileIO.readData(from: paths.toolchainManifest)
                if let manifest = try? decoder.decode(ToolchainManifest.self, from: manifestData) {
                    repositoryCount = manifest.repos?.count ?? 0
                }
                Dashboard.Log.debug("Toolchain manifest read+decode took \(Date().timeIntervalSince(s))s")
            } catch {
                Dashboard.Log.error("Toolchain manifest read failed: \(error)")
            }

            if Task.isCancelled {
                Dashboard.Log.warn("Dependencies load cancelled")
                return
            }
            var findings: [String] = []
            var status: StatusIndicator = .unknown
            do {
                let s = Date()
                if let size = await fileIO.fileSize(at: paths.crossRepoReport), size > maxFileSizeBytes {
                    Dashboard.Log.warn("Cross-repo report large: \(size) bytes")
                }
                let crossData = try await fileIO.readData(from: paths.crossRepoReport)
                if let cross = try? decoder.decode(CrossRepoReport.self, from: crossData) {
                    findings = cross.findings
                    status = cross.statusIndicator
                    if repositoryCount == 0, let repos = cross.metadata?.repositories {
                        repositoryCount = repos
                    }
                }
                Dashboard.Log.debug("Cross-repo report read+decode took \(Date().timeIntervalSince(s))s")
            } catch {
                Dashboard.Log.warn("Cross-repo report load failed: \(error)")
            }

            if Task.isCancelled {
                Dashboard.Log.warn("Dependencies load cancelled")
                return
            }
            var pendingPRs: Int?
            var risks: [DependencyDashboard.Risk] = []
            do {
                let s = Date()
                if let size = await fileIO.fileSize(at: paths.renovateDashboard), size > maxFileSizeBytes {
                    Dashboard.Log.warn("Renovate dashboard large: \(size) bytes")
                }
                let renovateData = try await fileIO.readData(from: paths.renovateDashboard)
                if let dashboard = try? decoder.decode(RenovateDashboard.self, from: renovateData) {
                    if let prCount = dashboard.pendingPRs {
                        pendingPRs = prCount
                    }

                    if let repoList = dashboard.repositories {
                        repositoryCount = max(repositoryCount, repoList.count)
                        let repoFindings: [String] = repoList.compactMap { repo in
                            if let repoStatus = repo.status {
                                let indicator = StatusIndicator(statusCode: repoStatus)
                                guard indicator != .ok else { return nil }
                                let message = repo.message ?? "status \(repoStatus.rawValue)"
                                return "\(repo.name): \(message)"
                            }
                            return nil
                        }
                        findings.append(contentsOf: repoFindings)
                        if pendingPRs == nil {
                            let aggregated = repoList.reduce(0) { $0 + ($1.pendingPRs ?? 0) }
                            pendingPRs = aggregated
                        }
                    }

                    if let errors = dashboard.errors {
                        findings.append(contentsOf: errors)
                    }

                    if let dashStatus = dashboard.status {
                        let indicator = StatusIndicator(statusCode: dashStatus)
                        status = StatusIndicator.dominant(status, indicator)
                    }

                    if let topRisks = dashboard.topRisks, !topRisks.isEmpty {
                        risks = topRisks.map {
                            DependencyDashboard.Risk(
                                name: $0.name,
                                severity: StatusIndicator(statusCode: $0.severity),
                                summary: $0.summary
                            )
                        }
                    }
                }
                Dashboard.Log.debug("Renovate dashboard read+decode took \(Date().timeIntervalSince(s))s")
            } catch {
                Dashboard.Log.warn("Renovate dashboard load failed: \(error)")
            }

            if risks.isEmpty, !findings.isEmpty {
                risks = findings.map {
                    DependencyDashboard.Risk(
                        name: "Policy drift",
                        severity: .warning,
                        summary: $0
                    )
                }
            }

            let summary = DependencyDashboard(
                status: status,
                repositoryCount: repositoryCount,
                pendingPRs: pendingPRs,
                findings: findings,
                risks: risks
            )
            Dashboard.Log.debug("Dependencies summary ready: repos=\(repositoryCount), findings=\(findings.count), risks=\(risks.count)")
            await MainActor.run {
                if Task.isCancelled { return }
                self.dependencyDashboard = summary
            }
        }

        private func fetchOverrides(paths: Paths) async {
            if Task.isCancelled {
                Dashboard.Log.warn("Overrides load cancelled")
                return
            }
            await MainActor.run { self.isLoadingOverrides = true }
            defer {
                Task { @MainActor in
                    self.isLoadingOverrides = false
                }
            }
            Dashboard.Log.debug("Loading overrides…")
            var summaries: [OverrideSummary] = []
            let enumerator = FileManager.default.enumerator(at: paths.overrideDirectory, includingPropertiesForKeys: nil)
            while let file = enumerator?.nextObject() as? URL {
                if Task.isCancelled {
                    Dashboard.Log.warn("Overrides load cancelled")
                    return
                }
                guard file.pathExtension == "json" else { continue }
                do {
                    if let size = await fileIO.fileSize(at: file), size > maxFileSizeBytes {
                        Dashboard.Log.warn("Override file large: \(file.lastPathComponent) size=\(size) bytes")
                    }
                    let s = Date()
                    let data = try await fileIO.readData(from: file)
                    if let manifest = try? isoDayDecoder.decode(OverrideManifest.self, from: data) {
                        let entries: [OverrideSummary.Entry] = manifest.overrides.map { key, value in
                            let status: StatusIndicator = value.expires == nil ? .warning : .ok
                            return OverrideSummary.Entry(
                                tool: key,
                                version: value.version,
                                reason: value.reason,
                                expires: value.expires,
                                status: status
                            )
                        }
                        summaries.append(
                            OverrideSummary(
                                project: manifest.project,
                                summary: manifest.summary,
                                entries: entries.sorted(by: { $0.tool < $1.tool })
                            )
                        )
                    } else {
                        Dashboard.Log.error("Failed to decode override manifest: \(file.lastPathComponent)")
                    }
                    Dashboard.Log.debug("Override \(file.lastPathComponent) read+decode took \(Date().timeIntervalSince(s))s")
                } catch {
                    Dashboard.Log.error("Failed to read override file: \(file.lastPathComponent) error=\(error)")
                    continue
                }
            }
            Dashboard.Log.debug("Overrides loaded: \(summaries.count) projects")
            await MainActor.run {
                if Task.isCancelled { return }
                self.overrideSummaries = summaries.sorted { $0.project < $1.project }
            }
        }

        private func fetchAgentRuns(paths: Paths) async {
            if Task.isCancelled {
                Dashboard.Log.warn("Agent runs load cancelled")
                return
            }
            await MainActor.run { self.isLoadingAgentRuns = true }
            defer {
                Task { @MainActor in
                    self.isLoadingAgentRuns = false
                }
            }
            Dashboard.Log.debug("Loading agent runs…")
            do {
                if let size = await fileIO.fileSize(at: paths.agentRuns), size > maxFileSizeBytes {
                    Dashboard.Log.warn("Agent runs file large: \(size) bytes")
                }
                let s = Date()
                let data = try await fileIO.readData(from: paths.agentRuns)
                Dashboard.Log.debug("Agent runs read took \(Date().timeIntervalSince(s))s")
                if Task.isCancelled {
                    Dashboard.Log.warn("Agent runs load cancelled")
                    return
                }
                guard let entries = try? decoder.decode([AgentRunEntry].self, from: data) else {
                    await MainActor.run {
                        if Task.isCancelled { return }
                        self.agentRuns = []
                    }
                    Dashboard.Log.warn("Agent runs missing or failed to decode")
                    return
                }
                if Task.isCancelled {
                    Dashboard.Log.warn("Agent runs load cancelled")
                    return
                }
                let runs = entries.map {
                    AgentRun(
                        id: $0.id,
                        capability: $0.capability,
                        status: StatusIndicator(statusCode: $0.status),
                        summary: $0.summary,
                        started: $0.started,
                        logPath: $0.logPath
                    )
                }
                await MainActor.run {
                    if Task.isCancelled { return }
                    self.agentRuns = runs.sorted { $0.started > $1.started }
                }
            } catch {
                await MainActor.run {
                    if Task.isCancelled { return }
                    self.agentRuns = []
                }
                Dashboard.Log.error("Failed to read agent runs: \(error)")
                return
            }
        }

        private func fetchCapabilities(paths: Paths) async {
            if Task.isCancelled {
                Dashboard.Log.warn("Capability load cancelled")
                return
            }
            await MainActor.run {
                self.isLoadingCapabilities = true
                self.capabilityError = nil
            }
            defer {
                Task { @MainActor in
                    self.isLoadingCapabilities = false
                }
            }

            let manifestURL = paths.capabilitiesManifest
            let manifestPath = manifestURL.path(percentEncoded: false)
            guard FileManager.default.fileExists(atPath: manifestPath) else {
                Dashboard.Log.warn("Capabilities manifest not found at \(manifestPath)")
                await MainActor.run {
                    self.capabilities = []
                    self.capabilityError = "Capability manifest not found at \(manifestPath)."
                }
                return
            }

            do {
                if let size = await fileIO.fileSize(at: manifestURL), size > maxFileSizeBytes {
                    Dashboard.Log.warn("Capabilities manifest is large: \(size) bytes")
                }
                let data = try await fileIO.readData(from: manifestURL)
                if Task.isCancelled {
                    Dashboard.Log.warn("Capability load cancelled")
                    return
                }
                let manifest = try decoder.decode(CapabilityManifest.self, from: data)
                let baseURL = manifestURL.deletingLastPathComponent()
                let mapped: [Capability] = manifest.capabilities.compactMap { entry in
                    let resolved = URL(fileURLWithPath: entry.entrypoint, relativeTo: baseURL).standardizedFileURL
                    return Capability(
                        id: entry.id,
                        summary: entry.summary ?? entry.id,
                        entrypoint: resolved,
                        supportsCheck: entry.inputs?.properties["check"] != nil,
                        origin: entry.entrypoint
                    )
                }
                await MainActor.run {
                    if Task.isCancelled { return }
                    self.capabilities = mapped.sorted { $0.id < $1.id }
                    if self.messages.isEmpty {
                        self.messages = ChatMessage.defaultTranscript
                    }
                }
            } catch {
                Dashboard.Log.error("Failed to load capabilities: \(error)")
                await MainActor.run {
                    if Task.isCancelled { return }
                    self.capabilityError = error.localizedDescription
                }
            }
        }

        private struct CapabilityManifest: Decodable {
            struct CapabilityEntry: Decodable {
                struct Inputs: Decodable {
                    let properties: [String: Property]
                }

                struct Property: Decodable {
                    let type: String?
                }

                let id: String
                let summary: String?
                let entrypoint: String
                let inputs: Inputs?
            }

            let capabilities: [CapabilityEntry]
        }

        @MainActor
        func clearChat() {
            messages = ChatMessage.defaultTranscript
            persistTranscript()
        }

        @MainActor
        func sendChat(text: String, capability: Capability?, runCheck: Bool) {
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            if trimmed.isEmpty && capability == nil {
                return
            }

            appendMessage(role: .user, text: trimmed.isEmpty ? "(No prompt provided)" : trimmed, status: nil, capabilityId: capability?.id)

            guard let capability else {
                appendMessage(role: .assistant, text: "Message noted. No automation executed.", status: .informational, capabilityId: nil)
                return
            }

            if isExecutingCapability {
                appendMessage(role: .assistant, text: "Another capability is already running. Please wait for it to finish before launching \(capability.id).", status: .warning, capabilityId: capability.id)
                return
            }

            guard let paths = workspacePaths else {
                appendMessage(role: .assistant, text: "Workspace root unresolved. Choose the workspace from Settings before running capabilities.", status: .warning, capabilityId: capability.id)
                return
            }

            let launchDescriptor = capability.supportsCheck && runCheck ? "Launching \(capability.id) (check mode)…" : "Launching \(capability.id)…"
            appendMessage(role: .event, text: launchDescriptor, status: .informational, capabilityId: capability.id)

            Task {
                await self.executeCapability(paths: paths, capability: capability, userPrompt: trimmed, runCheck: runCheck)
            }
        }

        @MainActor
        func cancelActiveExecution() {
            let capabilityId = activeCapabilityId
            guard let process = activeProcess, process.isRunning else { return }
            Dashboard.Log.warn("User requested cancellation of capability \(activeCapabilityId ?? "unknown")")
            process.terminate()
            appendMessage(role: .event, text: "Cancellation requested…", status: .warning, capabilityId: capabilityId)
        }

        @MainActor
        private func appendMessage(role: ChatRole, text: String, status: StatusIndicator?, capabilityId: String?) {
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else { return }
            messages.append(ChatMessage(role: role, text: trimmed, status: status, capabilityId: capabilityId, stream: .transcript))
            persistTranscript()
        }

        @MainActor
        private func appendStream(_ text: String, capabilityId: String, channel: StreamChannel, status: StatusIndicator) {
            let sanitized = text.replacingOccurrences(of: "\r", with: "")
            guard !sanitized.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return }
            if let index = messages.lastIndex(where: { $0.capabilityId == capabilityId && $0.stream == channel }) {
                messages[index] = messages[index].appending(sanitized)
            } else {
                messages.append(ChatMessage(role: .assistant, text: sanitized, status: status, capabilityId: capabilityId, stream: channel))
            }
            persistTranscript()
        }

        private func transcriptURL(for paths: Paths?) -> URL? {
            let fileManager = FileManager.default
            guard let support = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else {
                Dashboard.Log.warn("Unable to resolve application support directory for transcripts")
                return nil
            }
            let directory = support.appendingPathComponent("n00t", isDirectory: true)
            do {
                try fileManager.createDirectory(at: directory, withIntermediateDirectories: true)
            } catch {
                Dashboard.Log.warn("Failed to create transcript directory: \(error)")
            }
            let slug = paths?.root.lastPathComponent.trimmingCharacters(in: .whitespacesAndNewlines)
            let workspace = slug?.isEmpty == false ? slug! : "default"
            return directory.appendingPathComponent("\(workspace)-transcript.json", isDirectory: false)
        }

        @MainActor
        private func loadTranscript(for paths: Paths?) {
            guard let url = transcriptURL(for: paths), FileManager.default.fileExists(atPath: url.path) else {
                messages = ChatMessage.defaultTranscript
                persistTranscript(for: paths)
                return
            }
            do {
                let data = try Data(contentsOf: url)
                let stored = try transcriptDecoder.decode([ChatMessage].self, from: data)
                if stored.isEmpty {
                    messages = ChatMessage.defaultTranscript
                } else {
                    messages = stored
                }
            } catch {
                Dashboard.Log.warn("Failed to load chat transcript: \(error)")
                messages = ChatMessage.defaultTranscript
            }
            persistTranscript(for: paths)
        }

        @MainActor
        private func persistTranscript(for paths: Paths? = nil) {
            let targetPaths = paths ?? workspacePaths
            guard let url = transcriptURL(for: targetPaths) else { return }
            let snapshot = messages
            Task.detached(priority: .utility) {
                do {
                    let encoder = JSONEncoder()
                    encoder.dateEncodingStrategy = .iso8601
                    let data = try encoder.encode(snapshot)
                    let directory = url.deletingLastPathComponent()
                    try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
                    try data.write(to: url, options: .atomic)
                } catch {
                    Dashboard.Log.warn("Failed to persist chat transcript: \(error)")
                }
            }
        }

        private func executeCapability(paths: Paths, capability: Capability, userPrompt: String, runCheck: Bool) async {
            await MainActor.run {
                self.isExecutingCapability = true
                self.activeCapabilityId = capability.id
            }

            var process: Process?
            let stdoutPipe = Pipe()
            let stderrPipe = Pipe()

            await withTaskCancellationHandler {
                var environment = ProcessInfo.processInfo.environment
                environment["WORKSPACE_ROOT"] = paths.root.path(percentEncoded: false)
                var payload: [String: Any] = [:]
                if !userPrompt.isEmpty {
                    payload["input"] = userPrompt
                }
                if capability.supportsCheck {
                    payload["check"] = runCheck
                }
                if !payload.isEmpty,
                   let data = try? JSONSerialization.data(withJSONObject: payload, options: []),
                   let string = String(data: data, encoding: .utf8) {
                    environment["CAPABILITY_PAYLOAD"] = string
                }

                let candidate = Process()
                candidate.executableURL = capability.entrypoint
                candidate.currentDirectoryURL = paths.root
                candidate.environment = environment
                candidate.standardOutput = stdoutPipe
                candidate.standardError = stderrPipe

                let stdoutHandle = stdoutPipe.fileHandleForReading
                let stderrHandle = stderrPipe.fileHandleForReading

                stdoutHandle.readabilityHandler = { [weak self] handle in
                    let data = handle.availableData
                    guard !data.isEmpty,
                          let text = String(data: data, encoding: .utf8),
                          !text.isEmpty else { return }
                    Task { @MainActor [weak self] in
                        self?.appendStream(text, capabilityId: capability.id, channel: .stdout, status: .informational)
                    }
                }

                stderrHandle.readabilityHandler = { [weak self] handle in
                    let data = handle.availableData
                    guard !data.isEmpty,
                          let text = String(data: data, encoding: .utf8),
                          !text.isEmpty else { return }
                    Task { @MainActor [weak self] in
                        self?.appendStream(text, capabilityId: capability.id, channel: .stderr, status: .warning)
                    }
                }

                do {
                    try candidate.run()
                } catch {
                    stdoutHandle.readabilityHandler = nil
                    stderrHandle.readabilityHandler = nil
                    Dashboard.Log.error("Failed to launch capability \(capability.id): \(error)")
                    await MainActor.run {
                        self.appendMessage(role: .assistant, text: "Failed to launch \(capability.id): \(error.localizedDescription)", status: .failed, capabilityId: capability.id)
                        self.isExecutingCapability = false
                        self.activeCapabilityId = nil
                        self.activeProcess = nil
                    }
                    return
                }

                process = candidate
                await MainActor.run { self.activeProcess = candidate }

                await withCheckedContinuation { continuation in
                    candidate.terminationHandler = { _ in
                        stdoutHandle.readabilityHandler = nil
                        stderrHandle.readabilityHandler = nil
                        continuation.resume()
                    }
                }
            } onCancel: {
                Task { @MainActor in
                    if let current = process, current.isRunning {
                        Dashboard.Log.warn("Terminating capability \(capability.id) after cancellation request")
                        current.terminate()
                        self.appendMessage(role: .event, text: "\(capability.id) cancellation requested.", status: .warning, capabilityId: capability.id)
                    }
                }
            }

            guard let process else {
                return
            }

            let stdoutRemainder = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
            if let text = String(data: stdoutRemainder, encoding: .utf8), !text.isEmpty {
                await MainActor.run {
                    self.appendStream(text, capabilityId: capability.id, channel: .stdout, status: process.terminationStatus == 0 ? .ok : .failed)
                }
            }
            let stderrRemainder = stderrPipe.fileHandleForReading.readDataToEndOfFile()
            if let text = String(data: stderrRemainder, encoding: .utf8), !text.isEmpty {
                await MainActor.run {
                    self.appendStream(text, capabilityId: capability.id, channel: .stderr, status: .warning)
                }
            }

            let exitCode = process.terminationStatus
            let indicator: StatusIndicator = exitCode == 0 ? .ok : .failed

            await MainActor.run {
                self.appendMessage(role: .event, text: "\(capability.id) finished with status \(exitCode)", status: indicator, capabilityId: capability.id)
                self.isExecutingCapability = false
                self.activeCapabilityId = nil
                self.activeProcess = nil
            }
        }
    }

    struct Paths {
        let root: URL

        var metaCheckReport: URL {
            root.appending(path: ".dev/automation/artifacts/meta-check/latest.json")
        }

        var crossRepoReport: URL {
            root.appending(path: ".dev/automation/artifacts/dependencies/cross-repo.json")
        }

        var renovateDashboard: URL {
            root.appending(path: ".dev/automation/artifacts/dependencies/renovate-dashboard.json")
        }

        var toolchainManifest: URL {
            root.appending(path: "n00-cortex/data/toolchain-manifest.json")
        }

        var capabilitiesManifest: URL {
            root.appending(path: "n00t/capabilities/manifest.json")
        }

        var overrideDirectory: URL {
            root.appending(path: "n00-cortex/data/dependency-overrides", directoryHint: .isDirectory)
        }

        var agentRuns: URL {
            root.appending(path: ".dev/automation/artifacts/automation/agent-runs.json")
        }

        static func resolve() -> Paths? {
            let fileManager = FileManager.default

            // 1) Allow environment variable override
            if let envRoot = ProcessInfo.processInfo.environment["DASHBOARD_ROOT"], !envRoot.isEmpty {
                let url = URL(fileURLWithPath: envRoot, isDirectory: true)
                if fileManager.fileExists(atPath: url.path(percentEncoded: false)) {
                    Dashboard.Log.info("Using workspace root from DASHBOARD_ROOT: \(url.path(percentEncoded: false))")
                    return Paths(root: url)
                } else {
                    Dashboard.Log.warn("DASHBOARD_ROOT set but path does not exist: \(envRoot)")
                }
            }

            // 2) Allow UserDefaults override
            if let stored = UserDefaults.standard.string(forKey: "Dashboard.RootPath"), !stored.isEmpty {
                let url = URL(fileURLWithPath: stored, isDirectory: true)
                if fileManager.fileExists(atPath: url.path(percentEncoded: false)) {
                    Dashboard.Log.info("Using workspace root from UserDefaults: \(url.path(percentEncoded: false))")
                    return Paths(root: url)
                } else {
                    Dashboard.Log.warn("Dashboard.RootPath set but path does not exist: \(stored)")
                }
            }

            // 3) Try current working directory if app launched from a shell
            let cwdPath = fileManager.currentDirectoryPath
            let cwdURL = URL(fileURLWithPath: cwdPath, isDirectory: true)
            if let resolved = resolve(from: cwdURL) {
                return resolved
            }

            // 4) Fallback: walk up from the app bundle location
            let candidate = Bundle.main.bundleURL.deletingLastPathComponent().deletingLastPathComponent()
            Dashboard.Log.debug("Workspace root detection starting at \(candidate.path(percentEncoded: false))")
            return resolve(from: candidate)
        }

        // Helper that walks up parent directories looking for known markers
        private static func resolve(from start: URL) -> Paths? {
            let fileManager = FileManager.default
            var candidate = start
            var iterations = 0
            while iterations < 128 {
                let cortex = candidate.appending(path: "n00-cortex")
                let automationScripts = candidate.appending(path: ".dev/automation/scripts")
                let cortexPath = cortex.path(percentEncoded: false)
                let automationPath = automationScripts.path(percentEncoded: false)
                if fileManager.fileExists(atPath: cortexPath) && fileManager.fileExists(atPath: automationPath) {
                    Dashboard.Log.debug("Workspace root resolved at \(candidate.path(percentEncoded: false)) after \(iterations) iteration(s)")
                    return Paths(root: candidate)
                }
                let parent = candidate.deletingLastPathComponent()
                let candidatePath = candidate.path(percentEncoded: false)
                let parentPath = parent.path(percentEncoded: false)
                if parentPath == candidatePath {
                    Dashboard.Log.warn("Unable to resolve workspace root; last candidate \(candidatePath)")
                    return nil
                }
                candidate = parent
                iterations += 1
            }
            Dashboard.Log.error("Workspace root resolution exceeded iteration limit")
            return nil
        }
    }

    struct RootView: View {
        @ObservedObject var viewModel: ViewModel
        @State private var refreshTask: Task<Void, Never>? = nil
        @State private var didInitialRefresh = false

        var body: some View {
            NavigationSplitView {
                List(selection: $viewModel.selection) {
                    Section("Orchestrator") {
                        NavigationLink(value: ViewModel.Selection.chat) {
                            Label("Chat Console", systemImage: "message.and.bubble.left.and.bubble.right.fill")
                        }
                    }
                    Section("Dashboard") {
                        NavigationLink(value: ViewModel.Selection.metaCheck) {
                            Label("Meta Check", systemImage: "checkmark.seal")
                        }
                        NavigationLink(value: ViewModel.Selection.dependencies) {
                            Label("Dependencies", systemImage: "shippingbox")
                        }
                        NavigationLink(value: ViewModel.Selection.overrides) {
                            Label("Overrides", systemImage: "slider.horizontal.3")
                        }
                        NavigationLink(value: ViewModel.Selection.agents) {
                            Label("Agents", systemImage: "bolt.fill")
                        }
                    }
                }
                .navigationTitle("Dashboard")
                .onAppear {
                    guard !didInitialRefresh else { return }
                    didInitialRefresh = true
                    refreshTask?.cancel()
                    refreshTask = Task { await viewModel.refresh() }
                }
                .onDisappear {
                    refreshTask?.cancel()
                    Dashboard.Log.debug("RootView disappeared; refresh task cancelled")
                    refreshTask = nil
                }
                .toolbar {
                    ToolbarItem(placement: .primaryAction) {
                        Button {
                            refreshTask?.cancel()
                            Dashboard.Log.info("Manual refresh triggered")
                            refreshTask = Task { await viewModel.refresh() }
                        } label: {
                            HStack(spacing: 6) {
                                if viewModel.isRefreshing {
                                    ProgressView()
                                        .scaleEffect(0.8)
                                }
                                Label(viewModel.isRefreshing ? "Refreshing…" : "Refresh", systemImage: "arrow.clockwise")
                            }
                        }
                        .help("Refresh data")
                        .disabled(viewModel.isRefreshing)
                        .keyboardShortcut("r", modifiers: [.command])
                    }
                    ToolbarItem(placement: .automatic) {
                        if #available(macOS 14.0, *) {
                            SettingsLink {
                                Label("Settings", systemImage: "gearshape")
                            }
                            .help("Open Settings")
                        } else {
                            // Fallback on earlier versions
                        }
                    }
                    ToolbarItem(placement: .automatic) {
                        StatusDot(isOK: !viewModel.isRefreshing, animate: viewModel.animateStatusDot && !viewModel.reduceMotion)
                            .help(viewModel.isRefreshing ? "Refreshing" : "Idle")
                    }
                    ToolbarItem(placement: .automatic) {
                        if let text = viewModel.refreshStatusText {
                            Text(text)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            } detail: {
                Group {
                    if let warning = viewModel.workspaceWarning {
                        WorkspaceWarning(message: warning)
                    } else {
                        switch viewModel.selection {
                        case .chat:
                            ChatConsoleView().environmentObject(viewModel)
                        case .metaCheck:
                            MetaCheck(state: viewModel.metaCheckState).environmentObject(viewModel)
                        case .dependencies:
                            DependencyDashboardView(dashboard: viewModel.dependencyDashboard).environmentObject(viewModel)
                        case .overrides:
                            OverridesView(overrides: viewModel.overrideSummaries).environmentObject(viewModel)
                        case .agents:
                            AgentRunsView(runs: viewModel.agentRuns).environmentObject(viewModel)
                        }
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .background(Color(nsColor: .windowBackgroundColor))
            }
        }
    }

    struct WorkspaceWarning: View {
        @EnvironmentObject var viewModel: ViewModel
        let message: String

        var body: some View {
            VStack(spacing: 16) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 48))
                    .foregroundStyle(.orange)
                Text("Workspace Not Detected")
                    .font(.title).bold()
                Text(message)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                Button {
                    let panel = NSOpenPanel()
                    panel.canChooseFiles = false
                    panel.canChooseDirectories = true
                    panel.allowsMultipleSelection = false
                    panel.prompt = "Choose"
                    panel.message = "Select the root of your n00tropic-cerebrum workspace"
                    if panel.runModal() == .OK, let url = panel.url {
                        viewModel.setWorkspaceRoot(url)
                        Task { await viewModel.refresh() }
                    }
                } label: {
                    Label("Choose Workspace Root…", systemImage: "folder")
                }
                .buttonStyle(.borderedProminent)
                .padding(.top, 8)
            }
            .padding()
        }
    }

    struct MetaCheck: View {
        @EnvironmentObject var viewModel: ViewModel
        let state: ViewModel.MetaCheckState

        var body: some View {
            VStack(alignment: .leading, spacing: 20) {
                HStack(alignment: .firstTextBaseline, spacing: 12) {
                    Text("Meta Check")
                        .font(.largeTitle)
                        .bold()
                    StatusBadge(status: state.statusIndicator)
                }
                Text(state.summary)
                    .font(.title3)
                if let lastRun = state.lastRun {
                    Text("Completed \(lastRun.formatted(date: .abbreviated, time: .standard))")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                if let logPath = state.logPath {
                    Text("Log: \(logPath)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Divider()
                if viewModel.isLoadingMetaCheck {
                    HStack { Spacer(); ProgressView("Loading…"); Spacer() }
                }
                List(state.checks) { check in
                    HStack(alignment: .firstTextBaseline, spacing: 12) {
                        StatusBadge(status: check.status)
                        VStack(alignment: .leading, spacing: 4) {
                            Text(check.description)
                                .font(.headline)
                            if let notes = check.notes {
                                Text(notes)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        Spacer()
                        if check.durationSeconds > 0 {
                            Text("\(check.durationSeconds)s")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .listStyle(.plain)
                Spacer()
            }
            .padding()
        }
    }

    struct DependencyDashboardView: View {
        @EnvironmentObject var viewModel: ViewModel
        let dashboard: ViewModel.DependencyDashboard

        var body: some View {
            VStack(alignment: .leading, spacing: 16) {
                HStack(spacing: 12) {
                    Text("Dependency Posture")
                        .font(.largeTitle)
                        .bold()
                    StatusBadge(status: dashboard.status)
                }
                Text("Canonical policy covers \(dashboard.repositoryCount) repositories.")
                    .font(.title3)
                if let pending = dashboard.pendingPRs {
                    Text("\(pending) Renovate pull requests currently open.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                } else {
                    Text("Renovate dashboard not connected; populate `.dev/automation/artifacts/dependencies/renovate-dashboard.json` to surface PR metrics.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                Divider()
                if viewModel.isLoadingDependencies {
                    HStack { Spacer(); ProgressView("Loading…"); Spacer() }
                }
                if dashboard.findings.isEmpty {
                    Label("No cross-repo drift detected.", systemImage: "checkmark.circle")
                        .foregroundStyle(.green)
                } else {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Active Findings")
                            .font(.headline)
                        ForEach(dashboard.findings, id: \.self) { finding in
                            Label(finding, systemImage: "exclamationmark.triangle.fill")
                                .foregroundStyle(.orange)
                        }
                    }
                }
                if !dashboard.risks.isEmpty {
                    Divider()
                    Text("Highlighted Risks")
                        .font(.headline)
                    ForEach(dashboard.risks) { risk in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text(risk.name)
                                    .font(.headline)
                                Spacer()
                                StatusBadge(status: risk.severity)
                            }
                            Text(risk.summary)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                Spacer()
            }
            .padding()
        }
    }

    struct OverridesView: View {
        @EnvironmentObject var viewModel: ViewModel
        let overrides: [ViewModel.OverrideSummary]

        var body: some View {
            VStack(alignment: .leading, spacing: 16) {
                Text("Policy Overrides")
                    .font(.largeTitle)
                    .bold()
                Text("Source of truth: n00-cortex/data/dependency-overrides.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Divider()
                if viewModel.isLoadingOverrides {
                    HStack { Spacer(); ProgressView("Loading…"); Spacer() }
                }
                if overrides.isEmpty {
                    HStack {
                        Spacer()
                        Label("No active overrides.", systemImage: "checkmark.shield")
                            .foregroundStyle(.green)
                        Spacer()
                    }
                } else {
                    List(overrides) { override in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(override.project)
                                .font(.headline)
                            if let summary = override.summary {
                                Text(summary)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            ForEach(override.entries) { entry in
                                VStack(alignment: .leading, spacing: 4) {
                                    HStack {
                                        Text("\(entry.tool.uppercased()) → \(entry.version)")
                                            .font(.subheadline)
                                        Spacer()
                                        StatusBadge(status: entry.status)
                                    }
                                    if let reason = entry.reason {
                                        Text(reason)
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                    if let expires = entry.expires {
                                        Text("Expires \(expires.formatted(date: .abbreviated, time: .omitted))")
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                        }
                        .padding(.vertical, 4)
                    }
                    .listStyle(.inset)
                }
                Spacer()
            }
            .padding()
        }
    }

    struct AgentRunsView: View {
        @EnvironmentObject var viewModel: ViewModel
        let runs: [ViewModel.AgentRun]

        var body: some View {
            VStack(alignment: .leading, spacing: 16) {
                Text("Capability Runs")
                    .font(.largeTitle)
                    .bold()
                Text("Captured from .dev/automation/artifacts/automation/agent-runs.json.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Divider()
                if viewModel.isLoadingAgentRuns {
                    HStack { Spacer(); ProgressView("Loading…"); Spacer() }
                }
                if runs.isEmpty {
                    HStack {
                        Spacer()
                        Label("No recorded capability runs yet.", systemImage: "clock")
                            .foregroundStyle(.secondary)
                        Spacer()
                    }
                } else {
                    List(runs) { run in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack(alignment: .firstTextBaseline, spacing: 8) {
                                Text(run.capability)
                                    .font(.headline)
                                StatusBadge(status: run.status)
                                Spacer()
                                Text(run.started.formatted(date: .abbreviated, time: .standard))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Text(run.summary)
                                .font(.caption)
                            if let log = run.logPath {
                                Text("Log: \(log)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                    .listStyle(.plain)
                }
                Spacer()
            }
            .padding()
        }
    }

    struct SettingsView: View {
        @EnvironmentObject var viewModel: ViewModel
        @State private var draftPath: String = ""
        @State private var showSetSuccess: Bool = false

        var body: some View {
            Form {
                Section("Workspace Root") {
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 8) {
                            Image(systemName: "externaldrive")
                                .foregroundStyle(.tint)
                            Text("Detected Root:")
                                .font(.headline)
                            Spacer()
                            StatusDot(isOK: viewModel.workspaceWarning == nil, animate: viewModel.animateStatusDot && !viewModel.reduceMotion)
                        }
                        HStack(alignment: .firstTextBaseline, spacing: 8) {
                            Text(viewModel.currentRootPath ?? "Not set")
                                .font(.system(.body, design: .monospaced))
                                .lineLimit(2)
                                .textSelection(.enabled)
                                .padding(8)
                                .background(.quaternary.opacity(0.4))
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                            Spacer()
                            Button {
                                if let path = viewModel.currentRootPath {
                                    NSPasteboard.general.clearContents()
                                    NSPasteboard.general.setString(path, forType: .string)
                                }
                            } label: {
                                Image(systemName: "doc.on.doc")
                            }
                            .help("Copy path")
                            Button {
                                if let path = viewModel.currentRootPath {
                                    NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: path)])
                                }
                            } label: {
                                Image(systemName: "magnifyingglass")
                            }
                            .help("Reveal in Finder")
                        }
                        if let warning = viewModel.workspaceWarning {
                            Label(warning, systemImage: "exclamationmark.triangle.fill")
                                .foregroundStyle(.orange)
                                .font(.caption)
                        }
                    }
                    HStack(spacing: 8) {
                        Button {
                            let panel = NSOpenPanel()
                            panel.canChooseFiles = false
                            panel.canChooseDirectories = true
                            panel.allowsMultipleSelection = false
                            panel.prompt = "Choose"
                            panel.message = "Select the root of your n00tropic-cerebrum workspace"
                            if panel.runModal() == .OK, let url = panel.url {
                                viewModel.setWorkspaceRoot(url)
                                Task { await viewModel.refresh() }
                                withAnimation { showSetSuccess = true }
                                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { withAnimation { showSetSuccess = false } }
                            }
                        } label: {
                            Label("Browse…", systemImage: "folder")
                        }
                        Button {
                            viewModel.useCurrentDirectoryAsRoot()
                            Task { await viewModel.refresh() }
                        } label: {
                            Label("Use Current Directory", systemImage: "terminal")
                        }
                        Button(role: .destructive) {
                            viewModel.resetWorkspaceRoot()
                            Task { await viewModel.refresh() }
                        } label: {
                            Label("Reset to Auto", systemImage: "arrow.counterclockwise")
                        }
                        Spacer()
                        if showSetSuccess {
                            Label("Saved", systemImage: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                                .transition(.opacity)
                        }
                    }
                }

                Section("Automation Tips") {
                    VStack(alignment: .leading, spacing: 6) {
                        Label("You can set the DASHBOARD_ROOT environment variable to force a root.", systemImage: "info.circle")
                        Label("Or set Dashboard.RootPath in User Defaults for persistent configuration.", systemImage: "gearshape")
                        Text("Example:")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text("defaults write $(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' \"\(Bundle.main.bundlePath)/Contents/Info.plist\") Dashboard.RootPath \"/Volumes/APFS Space/n00tropic-cerebrum\"")
                            .font(.system(.caption, design: .monospaced))
                            .textSelection(.enabled)
                    }
                }

                Section("Appearance") {
                    Toggle("Animate status indicator", isOn: $viewModel.animateStatusDot)
                    Toggle("Reduce motion (disable animations)", isOn: $viewModel.reduceMotion)
                }

                Section("Actions") {
                    HStack(spacing: 8) {
                        Button {
                            Task { await viewModel.refresh() }
                        } label: {
                            Label("Test Now", systemImage: "play.circle")
                        }
                        .keyboardShortcut(.defaultAction)
                        .disabled(viewModel.isRefreshing)
                    }
                }
            }
            .padding()
        }
    }

    struct StatusDot: View {
        let isOK: Bool
        let animate: Bool
        @State private var pulse = false

        var body: some View {
            HStack(spacing: 6) {
                Circle()
                    .fill(isOK ? Color.green : Color.orange)
                    .frame(width: 10, height: 10)
                    .scaleEffect(isOK || !animate ? 1.0 : (pulse ? 1.08 : 0.92))
                    .opacity(isOK || !animate ? 1.0 : (pulse ? 1.0 : 0.85))
                    .animation((isOK || !animate) ? .default : .easeInOut(duration: 0.9).repeatForever(autoreverses: true), value: pulse)
                    .onAppear {
                        if !isOK && animate {
                            pulse = true
                        }
                    }
                    .onChange(of: isOK) { newValue in
                        if newValue || !animate {
                            pulse = false
                        } else {
                            pulse = true
                        }
                    }
                    .onChange(of: animate) { newValue in
                        if !newValue {
                            pulse = false
                        } else if !isOK {
                            pulse = true
                        }
                    }
                Text(isOK ? "Ready" : "Needs Configuration")
                    .font(.caption)
                    .foregroundStyle(isOK ? .green : .orange)
            }
        }
    }

    struct StatusBadge: View {
        let status: ViewModel.StatusIndicator

        var body: some View {
            Text(status.label)
                .font(.caption)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(status.color.opacity(0.2))
                .foregroundStyle(status.color)
                .clipShape(Capsule())
        }
    }

    // MARK: - Codable glue

    private struct MetaCheckReport: Decodable {
        struct Check: Decodable {
            let id: String
            let description: String
            let status: Dashboard.StatusCode
            let durationSeconds: Int
            let notes: String?
        }

        let generated: Date
        let started: Date
        let completed: Date
        let status: Dashboard.StatusCode
        let summary: String
        let logPath: String?
        let checks: [Check]
    }

    private struct ToolchainManifest: Decodable {
        let repos: [String: [String: String]]?
    }

    private struct CrossRepoReport: Decodable {
        struct Metadata: Decodable {
            let repositories: Int?
        }

        let generated: Date
        let status: Dashboard.StatusCode
        let findingCount: Int
        let findings: [String]
        let metadata: Metadata?

        var statusIndicator: Dashboard.ViewModel.StatusIndicator {
            switch status {
            case .ok: return .ok
            case .drift: return .warning
            default: return .unknown
            }
        }
    }

    private struct RenovateDashboard: Decodable {
        struct Repo: Decodable {
            let name: String
            let status: Dashboard.StatusCode?
            let pendingPRs: Int?
            let path: String?
            let message: String?
        }

        struct Risk: Decodable {
            let name: String
            let severity: Dashboard.StatusCode
            let summary: String
        }

        let status: Dashboard.StatusCode?
        let pendingPRs: Int?
        let repositories: [Repo]?
        let topRisks: [Risk]?
        let errors: [String]?
    }

    private struct OverrideManifest: Decodable {
        struct Entry: Decodable {
            let version: String
            let reason: String?
            let expires: Date?
        }

        let project: String
        let summary: String?
        let overrides: [String: Entry]
    }

    private struct AgentRunEntry: Decodable {
        let id: UUID
        let capability: String
        let status: Dashboard.StatusCode
        let summary: String
        let started: Date
        let completed: Date?
        let logPath: String?
        let metadata: [String: JSONValue]?
    }

    enum StatusCode: String, Decodable {
        case ok
        case drift
        case succeeded
        case failed
        case skipped
        case warning
        case critical
        case moderate
        case informational
        case partial
    }

    private enum JSONValue: Decodable {
        case string(String)
        case number(Double)
        case bool(Bool)
        case object([String: JSONValue])
        case array([JSONValue])
        case null

        init(from decoder: Decoder) throws {
            let container = try decoder.singleValueContainer()
            if container.decodeNil() {
                self = .null
            } else if let string = try? container.decode(String.self) {
                self = .string(string)
            } else if let bool = try? container.decode(Bool.self) {
                self = .bool(bool)
            } else if let double = try? container.decode(Double.self) {
                self = .number(double)
            } else if let array = try? container.decode([JSONValue].self) {
                self = .array(array)
            } else if let object = try? container.decode([String: JSONValue].self) {
                self = .object(object)
            } else {
                throw DecodingError.dataCorruptedError(in: container, debugDescription: "Unsupported JSON value")
            }
        }
    }
}

extension Dashboard.ViewModel.Selection {
    fileprivate var storageKey: String {
        switch self {
        case .chat: return "chat"
        case .metaCheck: return "metaCheck"
        case .dependencies: return "dependencies"
        case .overrides: return "overrides"
        case .agents: return "agents"
        }
    }
    fileprivate init(storageKey: String) {
        switch storageKey {
        case "chat": self = .chat
        case "dependencies": self = .dependencies
        case "overrides": self = .overrides
        case "agents": self = .agents
        default: self = .chat
        }
    }
}

@main
struct MainApp: App {
    @StateObject private var viewModel = Dashboard.ViewModel()

    init() {
        print("Dashboard app started")
    }

    var body: some Scene {
        WindowGroup {
            Dashboard.RootView(viewModel: viewModel)
                .environmentObject(viewModel)
                .frame(minWidth: 1024, minHeight: 640)
        }
        Settings {
            Dashboard.SettingsView()
                .environmentObject(viewModel)
                .frame(minWidth: 520)
        }
    }
}
