import Foundation

struct AgentRunEntry: Codable, Identifiable {
    let id: String
    let capability_id: String?
    let status: String?
    let started_at: String?
    let completed_at: String?
    let summary: String?
}

struct RunEnvelopes: Codable {
    let runs: [AgentRunEntry]
}
