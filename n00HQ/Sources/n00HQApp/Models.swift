import Foundation

struct GraphNode: Codable, Identifiable, Equatable {
    let id: String
    let kind: String
    let title: String?
    let tags: [String]?
}

struct GraphEdge: Codable, Identifiable, Equatable {
    var id: String { "\(from)->\(type)->\(to)" }
    let from: String
    let to: String
    let type: String
}

struct WorkspaceGraph: Codable {
    let nodes: [GraphNode]
    let edges: [GraphEdge]
}

struct PipelineRun: Codable, Identifiable {
    var id: String { name }
    let name: String
    let status: String
    let duration_ms: Int?
    let log: String?
}

struct PipelineValidationSummary: Codable {
    let generated_at: String?
    let runs: [PipelineRun]
}

struct CapabilityHealthItem: Codable, Identifiable {
    let id: String
    let summary: String?
    let entrypoint: String?
    let exists: Bool?
    let executable: Bool?
    let status: String?
    let issues: [String]?
}

struct CapabilityHealthReport: Codable {
    let generated_at: String?
    let capabilities: [CapabilityHealthItem]
}

struct TokenDriftReport: Codable {
    let generated_at: String?
    let drift: Bool?
    let validation: String?
    let validation_reason: String?
}
