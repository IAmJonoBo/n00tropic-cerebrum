import Foundation

enum DataSource: String, CaseIterable, Identifiable {
    case local
    case remote

    var id: String { rawValue }
    var title: String { rawValue.capitalized }
}

@MainActor
final class DataRepository: ObservableObject {
    @Published var graph: WorkspaceGraph = WorkspaceGraph(nodes: [], edges: [])
    @Published var capabilityHealth: CapabilityHealthReport = CapabilityHealthReport(generated_at: nil, capabilities: [])
    @Published var tokenDrift: TokenDriftReport = TokenDriftReport(generated_at: nil, drift: nil, validation: nil, validation_reason: nil)
    @Published var runs: [AgentRunEntry] = []
    @Published var remoteStatus: String = "local"
    @Published var dataSource: DataSource = .local
    @Published var remoteBaseURL: URL?
    @Published var pipelineSummary: PipelineValidationSummary?

    func loadAll() {
        loadLocalArtifacts()
        loadHistory()
        loadPipelineSummary()
    }

    func loadLocalArtifacts() {
        dataSource = .local
        remoteStatus = "local"
        let artifacts = workspaceArtifactsRoot()
        graph = loadGraph(from: artifacts) ?? loadJSON(named: "graph", as: WorkspaceGraph.self) ?? WorkspaceGraph(nodes: [], edges: [])
        capabilityHealth = loadCapabilityHealth(from: artifacts) ?? loadJSON(named: "capability-health", as: CapabilityHealthReport.self) ?? CapabilityHealthReport(generated_at: nil, capabilities: [])
        tokenDrift = loadTokenDrift(from: artifacts) ?? loadJSON(named: "token-drift", as: TokenDriftReport.self) ?? tokenDrift
        runs = loadRuns(fromArtifacts: artifacts) ?? loadRunsFromBundle()
        loadPipelineSummary()
    }

    // Simple persistence for guard run history (used in ManagementView)
    func saveHistory(_ history: [GuardRun]) {
        let key = "guardHistory"
        let encoder = JSONEncoder()
        if let data = try? encoder.encode(history) {
            UserDefaults.standard.set(data, forKey: key)
        }
    }

    private func loadHistory() {
        let key = "guardHistory"
        if let data = UserDefaults.standard.data(forKey: key) {
            let decoder = JSONDecoder()
            if let decoded = try? decoder.decode([GuardRun].self, from: data) {
                self.guardHistory = decoded
            }
        }
    }

    @Published var guardHistory: [GuardRun] = []

    func fetchRemote(baseURL: URL) async {
        remoteStatus = "fetching"
        dataSource = .remote
        remoteBaseURL = baseURL
        defer { if remoteStatus == "fetching" { remoteStatus = "error" } }
        do {
            let g = try await fetchJSON(baseURL.appendingPathComponent("graph.json"), as: WorkspaceGraph.self)
            let h = try await fetchJSON(baseURL.appendingPathComponent("capability-health.json"), as: CapabilityHealthReport.self)
            let t = try await fetchJSON(baseURL.appendingPathComponent("token-drift.json"), as: TokenDriftReport.self)
            let r = try await fetchRuns(baseURL: baseURL)
            self.graph = g
            self.capabilityHealth = h
            self.tokenDrift = t
            self.runs = r
            remoteStatus = "ok"
        } catch {
            remoteStatus = "error"
            print("[data] Remote fetch failed: \(error)")
        }
    }

    private func fetchJSON<T: Decodable>(_ url: URL, as type: T.Type) async throws -> T {
        let (data, resp) = try await URLSession.shared.data(from: url)
        guard let http = resp as? HTTPURLResponse, 200..<300 ~= http.statusCode else {
            throw URLError(.badServerResponse)
        }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(T.self, from: data)
    }

    private func fetchRuns(baseURL: URL) async throws -> [AgentRunEntry] {
        // Prefer JSONL if present
        do {
            let url = baseURL.appendingPathComponent("run-envelopes.jsonl")
            let (data, resp) = try await URLSession.shared.data(from: url)
            guard let http = resp as? HTTPURLResponse, 200..<300 ~= http.statusCode else { throw URLError(.badServerResponse) }
            let text = String(decoding: data, as: UTF8.self)
            let items = parseRunLines(text)
            if !items.isEmpty { return items }
        } catch {}

        let url = baseURL.appendingPathComponent("agent-runs.json")
        let (data, resp) = try await URLSession.shared.data(from: url)
        guard let http = resp as? HTTPURLResponse, 200..<300 ~= http.statusCode else { throw URLError(.badServerResponse) }
        let items = parseRunData(data)
        return items
    }

    private func loadJSON<T: Decodable>(named: String, as type: T.Type) -> T? {
        let bundle = Bundle.module
        guard let url = bundle.url(forResource: named, withExtension: "json", subdirectory: "data") ?? bundle.url(forResource: named, withExtension: "json") else {
            return nil
        }
        do {
            let data = try Data(contentsOf: url)
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            return try decoder.decode(T.self, from: data)
        } catch {
            print("[data] Failed to load \(named): \(error)")
            return nil
        }
    }

    private func loadGraph(from artifacts: URL?) -> WorkspaceGraph? {
        guard let url = artifacts?.appendingPathComponent("workspace-graph.json") else { return nil }
        return loadJSON(at: url)
    }

    private func loadCapabilityHealth(from artifacts: URL?) -> CapabilityHealthReport? {
        guard let url = artifacts?.appendingPathComponent("capability-health.json") else { return nil }
        return loadJSON(at: url)
    }

    private func loadTokenDrift(from artifacts: URL?) -> TokenDriftReport? {
        guard let url = artifacts?.appendingPathComponent("token-drift.json") else { return nil }
        return loadJSON(at: url)
    }

    private func loadPipelineSummary() {
        guard let root = WorkspaceLocator.workspaceRoot() else { return }
        let path = root.appendingPathComponent(".dev/automation/artifacts/pipeline-validation/latest.json")
        pipelineSummary = loadJSON(at: path)
    }

    private func loadJSON<T: Decodable>(at url: URL) -> T? {
        do {
            let data = try Data(contentsOf: url)
            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            return try decoder.decode(T.self, from: data)
        } catch {
            return nil
        }
    }

    private func workspaceArtifactsRoot() -> URL? {
        guard let root = WorkspaceLocator.workspaceRoot() else { return nil }
        let artifacts = root.appendingPathComponent(".dev/automation/artifacts")
        return FileManager.default.fileExists(atPath: artifacts.path) ? artifacts : nil
    }

    private func loadRuns(fromArtifacts artifacts: URL?) -> [AgentRunEntry]? {
        guard let artifacts else { return nil }
        let automation = artifacts.appendingPathComponent("automation")
        let jsonl = automation.appendingPathComponent("run-envelopes.jsonl")
        if let text = try? String(contentsOf: jsonl) {
            let items = parseRunLines(text)
            if !items.isEmpty { return items }
        }
        let json = automation.appendingPathComponent("agent-runs.json")
        if let data = try? Data(contentsOf: json) {
            let items = parseRunData(data)
            if !items.isEmpty { return items }
        }
        return nil
    }

    private func loadRunsFromBundle() -> [AgentRunEntry] {
        let bundle = Bundle.module
        if let url = bundle.url(forResource: "run-envelopes", withExtension: "jsonl", subdirectory: "data") ?? bundle.url(forResource: "run-envelopes", withExtension: "jsonl") {
            if let text = try? String(contentsOf: url) {
                let items = parseRunLines(text)
                if !items.isEmpty { return items }
            }
        }
        if let url = bundle.url(forResource: "agent-runs", withExtension: "json", subdirectory: "data") ?? bundle.url(forResource: "agent-runs", withExtension: "json") {
            if let data = try? Data(contentsOf: url) {
                let items = parseRunData(data)
                if !items.isEmpty { return items }
            }
        }
        return []
    }

    private func parseRunLines(_ text: String) -> [AgentRunEntry] {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return text
            .split(separator: "\n")
            .compactMap { line in
                guard let data = line.data(using: .utf8) else { return nil }
                return try? decoder.decode(AgentRunEntry.self, from: data)
            }
    }

    private func parseRunData(_ data: Data) -> [AgentRunEntry] {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        if let arr = try? decoder.decode([AgentRunEntry].self, from: data) { return arr }
        if let wrap = try? decoder.decode(RunEnvelopes.self, from: data) { return wrap.runs }
        return []
    }

    func resolvedURL(for path: String?) -> URL? {
        guard let path, !path.isEmpty else { return nil }
        if let url = URL(string: path), url.scheme?.hasPrefix("http") == true { return url }
        if dataSource == .remote, let remoteBaseURL {
            return remoteBaseURL.appendingPathComponent(path)
        }
        if let root = WorkspaceLocator.workspaceRoot() {
            let direct = root.appendingPathComponent(path)
            if FileManager.default.fileExists(atPath: direct.path) { return direct }

            let artifactsRoot = root.appendingPathComponent(".dev/automation/artifacts")
            let automation = artifactsRoot.appendingPathComponent("automation").appendingPathComponent(path)
            if FileManager.default.fileExists(atPath: automation.path) { return automation }

            let artifactsPath = artifactsRoot.appendingPathComponent(path)
            if FileManager.default.fileExists(atPath: artifactsPath.path) { return artifactsPath }

            return direct
        }
        return nil
    }
}
