import Foundation

struct AgentRunEntry: Codable, Identifiable {
    let id: String
    let capabilityId: String?
    let status: String?
    let startedAt: String?
    let completedAt: String?
    let summary: String?
    let logPath: String?
    let telemetryPath: String?
    let assetIds: [String]?
    let datasetId: String?
    let tags: [String]?
    let notes: String?
    let metadata: [String: String]?

    // Convenience accessors to keep UI code tidy.
    var displayCapability: String { capabilityId ?? "unknown" }
    var artifacts: [String] {
        var items: [String] = []
        if let assetIds { items.append(contentsOf: assetIds) }
        if let metadata { items.append(contentsOf: metadata.values) }
        return items
    }

    enum CodingKeys: String, CodingKey {
        case id
        case runId = "run_id"
        case capabilityId = "capability_id"
        case capability
        case status
        case startedAt = "started_at"
        case started
        case completedAt = "completed_at"
        case completed
        case summary
        case logPath
        case telemetryPath = "telemetry_path"
        case assetIds = "asset_ids"
        case datasetId = "dataset_id"
        case tags
        case notes
        case metadata
    }

    init(id: String,
         capabilityId: String?,
         status: String?,
         startedAt: String?,
         completedAt: String?,
         summary: String?,
         logPath: String?,
         telemetryPath: String?,
         assetIds: [String]?,
         datasetId: String?,
         tags: [String]?,
         notes: String?,
         metadata: [String: String]?) {
        self.id = id
        self.capabilityId = capabilityId
        self.status = status
        self.startedAt = startedAt
        self.completedAt = completedAt
        self.summary = summary
        self.logPath = logPath
        self.telemetryPath = telemetryPath
        self.assetIds = assetIds
        self.datasetId = datasetId
        self.tags = tags
        self.notes = notes
        self.metadata = metadata
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decodeIfPresent(String.self, forKey: .id)
            ?? container.decode(String.self, forKey: .runId)
        capabilityId = try container.decodeIfPresent(String.self, forKey: .capabilityId)
            ?? container.decodeIfPresent(String.self, forKey: .capability)
        status = try container.decodeIfPresent(String.self, forKey: .status)
        startedAt = try container.decodeIfPresent(String.self, forKey: .startedAt)
            ?? container.decodeIfPresent(String.self, forKey: .started)
        completedAt = try container.decodeIfPresent(String.self, forKey: .completedAt)
            ?? container.decodeIfPresent(String.self, forKey: .completed)
        summary = try container.decodeIfPresent(String.self, forKey: .summary)
        logPath = try container.decodeIfPresent(String.self, forKey: .logPath)
        telemetryPath = try container.decodeIfPresent(String.self, forKey: .telemetryPath)
        assetIds = try container.decodeIfPresent([String].self, forKey: .assetIds)
        datasetId = try container.decodeIfPresent(String.self, forKey: .datasetId)
        tags = try container.decodeIfPresent([String].self, forKey: .tags)
        notes = try container.decodeIfPresent(String.self, forKey: .notes)
        metadata = try container.decodeIfPresent([String: String].self, forKey: .metadata)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encodeIfPresent(capabilityId, forKey: .capabilityId)
        try container.encodeIfPresent(status, forKey: .status)
        try container.encodeIfPresent(startedAt, forKey: .startedAt)
        try container.encodeIfPresent(completedAt, forKey: .completedAt)
        try container.encodeIfPresent(summary, forKey: .summary)
        try container.encodeIfPresent(logPath, forKey: .logPath)
        try container.encodeIfPresent(telemetryPath, forKey: .telemetryPath)
        try container.encodeIfPresent(assetIds, forKey: .assetIds)
        try container.encodeIfPresent(datasetId, forKey: .datasetId)
        try container.encodeIfPresent(tags, forKey: .tags)
        try container.encodeIfPresent(notes, forKey: .notes)
        try container.encodeIfPresent(metadata, forKey: .metadata)
    }
}

struct RunEnvelopes: Codable {
    let runs: [AgentRunEntry]
}
