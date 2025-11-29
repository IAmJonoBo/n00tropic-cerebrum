import Foundation

@MainActor
final class DataRepository: ObservableObject {
    @Published var graph: WorkspaceGraph = WorkspaceGraph(nodes: [], edges: [])
    @Published var capabilityHealth: CapabilityHealthReport = CapabilityHealthReport(generated_at: nil, capabilities: [])
    @Published var tokenDrift: TokenDriftReport = TokenDriftReport(generated_at: nil, drift: nil, validation: nil, validation_reason: nil)
    @Published var runs: [AgentRunEntry] = []
    @Published var remoteStatus: String = "local"

    func loadAll() {
        graph = loadJSON(named: "graph", as: WorkspaceGraph.self) ?? WorkspaceGraph(nodes: [], edges: [])
        capabilityHealth = loadJSON(named: "capability-health", as: CapabilityHealthReport.self) ?? CapabilityHealthReport(generated_at: nil, capabilities: [])
        tokenDrift = loadJSON(named: "token-drift", as: TokenDriftReport.self) ?? tokenDrift
        runs = loadRuns()
        loadHistory()
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
            let decoder = JSONDecoder(); decoder.keyDecodingStrategy = .convertFromSnakeCase
            let items = text.split(separator: "\n").compactMap { line -> AgentRunEntry? in
                guard let d = line.data(using: .utf8) else { return nil }
                return try? decoder.decode(AgentRunEntry.self, from: d)
            }
            if !items.isEmpty { return items }
        } catch {}

        let url = baseURL.appendingPathComponent("agent-runs.json")
        let (data, resp) = try await URLSession.shared.data(from: url)
        guard let http = resp as? HTTPURLResponse, 200..<300 ~= http.statusCode else { throw URLError(.badServerResponse) }
        let decoder = JSONDecoder(); decoder.keyDecodingStrategy = .convertFromSnakeCase
        if let arr = try? decoder.decode([AgentRunEntry].self, from: data) { return arr }
        if let wrap = try? decoder.decode(RunEnvelopes.self, from: data) { return wrap.runs }
        return []
    }

    private func loadRuns() -> [AgentRunEntry] {
        // Try JSON lines (run-envelopes.jsonl) then JSON (agent-runs.json)
        let bundle = Bundle.module
        if let url = bundle.url(forResource: "run-envelopes", withExtension: "jsonl", subdirectory: "data") ?? bundle.url(forResource: "run-envelopes", withExtension: "jsonl") {
            do {
                let text = try String(contentsOf: url)
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                let items = text.split(separator: "\n").compactMap { line -> AgentRunEntry? in
                    guard let data = line.data(using: .utf8) else { return nil }
                    return try? decoder.decode(AgentRunEntry.self, from: data)
                }
                if !items.isEmpty { return items }
            } catch {}
        }
        if let url = bundle.url(forResource: "agent-runs", withExtension: "json", subdirectory: "data") ?? bundle.url(forResource: "agent-runs", withExtension: "json") {
            do {
                let data = try Data(contentsOf: url)
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase
                if let arr = try? decoder.decode([AgentRunEntry].self, from: data) { return arr }
                if let wrap = try? decoder.decode(RunEnvelopes.self, from: data) { return wrap.runs }
            } catch {}
        }
        return []
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
}
