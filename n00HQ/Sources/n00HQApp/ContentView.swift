import SwiftUI

struct ContentView: View {
    @EnvironmentObject var repo: DataRepository
    @State private var selection: SidebarItem? = .home
    @State private var searchText: String = ""
    @State private var showingPalette: Bool = false

    var body: some View {
        NavigationSplitView {
            sidebar
        } detail: {
            detailView
                .toolbar { commandPaletteButton }
        }
        .searchable(text: $searchText)
        .sheet(isPresented: $showingPalette) {
            CommandPaletteView(searchText: $searchText)
                .environmentObject(repo)
        }
    }

    private var commandPaletteButton: some View {
        Button {
            showingPalette = true
        } label: {
            Label("Command Palette", systemImage: "command")
        }
        .keyboardShortcut(.init("k"), modifiers: [.command])
    }

    private var sidebar: some View {
        List(selection: $selection) {
            Section("Navigate") {
                ForEach(SidebarItem.allCases) { item in
                    Label(item.title, systemImage: item.icon)
                        .tag(item as SidebarItem?)
                }
            }
        }
        .listStyle(.sidebar)
        .frame(minWidth: 220)
    }

    @ViewBuilder
    private var detailView: some View {
        switch selection ?? .home {
        case .home:
            HomeView()
        case .automation:
            AutomationView()
        case .graph:
            GraphView()
        case .runs:
            RunsView()
        case .management:
            ManagementView()
        }
    }
}

enum SidebarItem: String, CaseIterable, Identifiable {
    case home, automation, graph, runs, management

    var id: String { rawValue }
    var title: String {
        switch self {
        case .home: return "Home"
        case .automation: return "Automation"
        case .graph: return "Graph"
        case .runs: return "Runs"
        case .management: return "Management"
        }
    }
    var icon: String {
        switch self {
        case .home: return "house.fill"
        case .automation: return "bolt.fill"
        case .graph: return "point.3.filled.connected.trianglepath.dotted"
        case .runs: return "clock.arrow.circlepath"
        case .management: return "wrench.and.screwdriver.fill"
        }
    }
}

// MARK: - Screens (initial minimal shells wired to repo)

struct HomeView: View {
    @EnvironmentObject var repo: DataRepository
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text("n00HQ Control Center")
                    .font(.largeTitle.bold())
                HStack(spacing: 16) {
                    MetricCard(title: "Nodes", value: repo.graph.nodes.count)
                    MetricCard(title: "Capabilities", value: repo.capabilityHealth.capabilities.count)
                    MetricCard(title: "Token Drift", value: repo.tokenDrift.drift == true ? "Drift" : "Clean", tint: repo.tokenDrift.drift == true ? .red : .green)
                }
                RemoteFetchSection()
                if let generated = repo.capabilityHealth.generated_at {
                    Text("Last capability scan: \(generated)").font(.footnote).foregroundColor(.secondary)
                }
                Spacer()
            }
            .padding()
        }
    }
}

struct AutomationView: View {
    @EnvironmentObject var repo: DataRepository
    var body: some View {
        List(repo.capabilityHealth.capabilities) { cap in
            VStack(alignment: .leading, spacing: 4) {
                Text(cap.id).font(.headline)
                Text(cap.summary ?? "").font(.subheadline)
                HStack {
                    if cap.status == "ok" { Label("OK", systemImage: "checkmark.seal.fill").foregroundColor(.green) }
                    else { Label("Issue", systemImage: "exclamationmark.triangle.fill").foregroundColor(.orange) }
                    if let issues = cap.issues, !issues.isEmpty {
                        Text(issues.joined(separator: ", ")).font(.footnote).foregroundColor(.secondary)
                    }
                }
            }
        }
    }
}

struct GraphView: View {
    @EnvironmentObject var repo: DataRepository
    @State private var selectedKind: String = "all"
    @State private var search: String = ""
    @State private var edgeType: String = "all"
    @StateObject private var vm = GraphViewModel()
    var kinds: [String] {
        let ks = Set(repo.graph.nodes.map { $0.kind })
        return ["all"] + ks.sorted()
    }
    var edgeTypes: [String] {
        let ts = Set(repo.graph.edges.map { $0.type })
        return ["all"] + ts.sorted()
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Picker("Kind", selection: $selectedKind) {
                    ForEach(kinds, id: \.self) { kind in
                        Text(kind.capitalized).tag(kind)
                    }
                }
                .pickerStyle(.segmented)

                Picker("Edges", selection: $edgeType) {
                    ForEach(edgeTypes, id: \.self) { edge in
                        Text(edge.capitalized).tag(edge)
                    }
                }
                .pickerStyle(.menu)
                .frame(maxWidth: 180)
            }

            TextField("Search nodes", text: $search)
                .textFieldStyle(.roundedBorder)

            HStack {
                List(vm.filtered) { node in
                    VStack(alignment: .leading) {
                        Text(node.title ?? node.id).font(.headline)
                        Text(node.kind).font(.footnote).foregroundColor(.secondary)
                        if let tags = node.tags { Text(tags.joined(separator: ", ")).font(.footnote) }
                    }
                    .listRowBackground(vm.selection?.id == node.id ? Color.accentColor.opacity(0.08) : Color.clear)
                    .onTapGesture { vm.selection = node }
                }
                .frame(minWidth: 280)

                Divider()

                VStack {
                    ForceGraphView(nodes: vm.filtered, edges: filteredEdges, selection: $vm.selection)
                        .frame(minHeight: 260)
                    if let sel = vm.selection {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(sel.title ?? sel.id).font(.title3.bold())
                            Text(sel.kind).font(.subheadline).foregroundColor(.secondary)
                            if let tags = sel.tags { TagCloud(tags: tags) }
                            if let related = relatedEdges(for: sel), !related.isEmpty {
                                Text("Connections")
                                    .font(.subheadline.bold())
                                ForEach(related) { edge in
                                    Text("\(edge.type): \(edge.from) → \(edge.to)")
                                        .font(.footnote)
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    } else {
                        Text("Select a node to inspect").foregroundColor(.secondary)
                            .frame(maxWidth: .infinity, alignment: .center)
                    }
                }
            }
        }
        .padding()
        .onAppear { vm.apply(nodes: repo.graph.nodes, kind: selectedKind, search: search) }
        .onChange(of: selectedKind, initial: false) { new, _ in
            vm.apply(nodes: repo.graph.nodes, kind: new, search: search)
        }
        .onChange(of: search, initial: false) { new, _ in
            vm.apply(nodes: repo.graph.nodes, kind: selectedKind, search: new)
        }
        .onChange(of: repo.graph.nodes) { nodes, _ in
            vm.apply(nodes: nodes, kind: selectedKind, search: search)
        }
    }

    private var filteredEdges: [GraphEdge] {
        let baseEdges = edgeType == "all" ? repo.graph.edges : repo.graph.edges.filter { $0.type == edgeType }
        if selectedKind == "all" { return baseEdges }
        let nodeIds = Set(vm.filtered.map { $0.id })
        return baseEdges.filter { nodeIds.contains($0.from) && nodeIds.contains($0.to) }
    }

    private func relatedEdges(for node: GraphNode) -> [GraphEdge]? {
        filteredEdges.filter { $0.from == node.id || $0.to == node.id }
    }
}

struct TagCloud: View {
    let tags: [String]
    var body: some View {
        HStack { ForEach(tags, id: \.self) { tag in
            Text(tag)
                .font(.footnote)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.accentColor.opacity(0.15))
                .cornerRadius(6)
        } }
    }
}

struct RunsView: View {
    @EnvironmentObject var repo: DataRepository
    @Environment(\.openURL) var openURL
    @State private var statusFilter: String = "all"
    var statuses: [String] {
        let s = Set(repo.runs.compactMap { $0.status })
        return ["all"] + s.sorted()
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Runs & Logs")
                .font(.title3.bold())
            Picker("Status", selection: $statusFilter) {
                ForEach(statuses, id: \.self) { Text($0.capitalized).tag($0) }
            }
            .pickerStyle(.segmented)
            if filteredRuns.isEmpty {
                Text("No runs ingested yet.").foregroundColor(.secondary)
            } else {
                List(filteredRuns.prefix(50)) { run in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(run.capabilityId ?? run.id).font(.headline)
                        Text(run.summary ?? "").font(.subheadline)
                        HStack {
                            Label(run.status ?? "", systemImage: (run.status ?? "").lowercased().contains("ok") || (run.status ?? "").lowercased().contains("success") ? "checkmark.circle.fill" : "exclamationmark.circle.fill")
                                .foregroundColor(statusColor(run.status))
                            if let started = run.startedAt { Text(started).font(.footnote).foregroundColor(.secondary) }
                            if let completed = run.completedAt { Text("→ \(completed)").font(.footnote).foregroundColor(.secondary) }
                        }
                        if let tags = run.tags, !tags.isEmpty {
                            Text(tags.joined(separator: ", "))
                                .font(.footnote)
                                .foregroundColor(.secondary)
                        }
                        HStack(spacing: 8) {
                            if let logURL = repo.resolvedURL(for: run.logPath ?? run.telemetryPath) {
                                Button {
                                    openURL(logURL)
                                } label: {
                                    Label("Log", systemImage: "doc.richtext")
                                }
                                .buttonStyle(.borderless)
                            }
                            if !run.artifacts.isEmpty {
                                Menu {
                                    ForEach(run.artifacts, id: \.self) { artifact in
                                        if let url = repo.resolvedURL(for: artifact) {
                                            Button {
                                                openURL(url)
                                            } label: { Text(shortPath(artifact)) }
                                        }
                                    }
                                } label: {
                                    Label("Artifacts (\(run.artifacts.count))", systemImage: "paperclip")
                                }
                            }
                            if let dataset = run.datasetId {
                                Text(dataset).font(.footnote).foregroundColor(.secondary)
                            }
                        }
                    }
                }
            }
        }
        .padding()
    }

    var filteredRuns: [AgentRunEntry] {
        if statusFilter == "all" { return repo.runs }
        return repo.runs.filter { $0.status == statusFilter }
    }

    private func statusColor(_ status: String?) -> Color {
        guard let status else { return .secondary }
        let lower = status.lowercased()
        if lower.contains("ok") || lower.contains("success") || lower.contains("succeed") { return .green }
        return .orange
    }

    private func shortPath(_ path: String) -> String {
        if let url = URL(string: path), url.scheme?.hasPrefix("http") == true {
            return url.lastPathComponent
        }
        return URL(fileURLWithPath: path).lastPathComponent
    }
}

struct ManagementView: View {
    @EnvironmentObject var repo: DataRepository
    @StateObject private var runner = ScriptRunner()
    @State private var runningActionID: String?
    @State private var lastCommand: String = ""
    @State private var lastStatusLabel: String = ""
    @State private var history: [GuardRun] = []
    private let guardActions: [GuardAction] = [
        GuardAction(id: "toolchain", title: "Toolchain pins", systemImage: "bolt.fill", command: "node scripts/check-toolchain-pins.mjs --json", label: "toolchain pins"),
        GuardAction(id: "token", title: "Token drift", systemImage: "aqi.medium", command: ".dev/automation/scripts/token-drift.sh", label: "token drift"),
        GuardAction(id: "typesense", title: "Typesense", systemImage: "network", command: ".dev/automation/scripts/typesense-freshness.sh 7", label: "typesense"),
        GuardAction(id: "pipelines", title: "Validate pipelines", systemImage: "arrow.triangle.2.circlepath", command: "scripts/validate-pipelines.sh --clean", label: "pipeline validation")
    ]
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Management & Drift Guards")
                .font(.title3.bold())
            GuardList(title: "Token Drift", status: repo.tokenDrift.drift == true ? .issue : .ok, detail: repo.tokenDrift.validation_reason)
            GuardList(title: "Capability Health", status: capabilityStatus, detail: nil)
            GuardList(title: "Toolchain Pins", status: .ok, detail: "Checked in policy-sync")
            GuardList(title: "Typesense Freshness", status: .ok, detail: "See nightly guard")

            GuardActions(actions: guardActions, runningActionID: $runningActionID) { action in
                await runCmd(action)
            }

            if !runner.lastOutput.isEmpty {
                HStack {
                    StatusChip(text: lastStatusLabel.isEmpty ? "done" : lastStatusLabel, status: runner.lastStatus == 0 ? .ok : .issue)
                    Text("\(lastCommand)").font(.footnote).foregroundColor(.secondary)
                    Spacer()
                }
                ScrollView {
                    Text(runner.lastOutput)
                        .font(.system(.footnote, design: .monospaced))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(8)
                        .background(Color(NSColor.windowBackgroundColor))
                        .cornerRadius(8)
                }
                .frame(maxHeight: 160)
            }

            if !history.isEmpty {
                Text("History")
                    .font(.subheadline.bold())
                ForEach(history.prefix(10)) { item in
                    HStack {
                        Label(item.label, systemImage: item.status == .ok ? "checkmark.seal.fill" : "exclamationmark.triangle.fill")
                            .foregroundColor(item.status == .ok ? .green : .orange)
                        Spacer()
                        Text(item.timestamp, style: .time)
                            .foregroundColor(.secondary)
                            .font(.footnote)
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background((item.status == .ok ? Color.green : Color.orange).opacity(0.12))
                    .cornerRadius(10)
                }
            }

            if let summary = repo.pipelineSummary {
                Text("Pipeline Validation")
                    .font(.subheadline.bold())
                if let ts = summary.generated_at {
                    Text("Generated: \(ts)")
                        .font(.footnote)
                        .foregroundColor(.secondary)
                }
                ForEach(summary.runs) { run in
                    HStack(spacing: 8) {
                        Circle()
                            .fill(run.status.lowercased() == "ok" ? Color.green : Color.orange)
                            .frame(width: 8, height: 8)
                        Text(run.name)
                        if let dur = run.duration_ms {
                            Text("\(dur) ms").font(.footnote).foregroundColor(.secondary)
                        }
                        Spacer()
                        if let url = repo.resolvedURL(for: run.log) {
                            Link("Log", destination: url)
                                .font(.footnote)
                        }
                    }
                    .padding(10)
                    .background(Color(NSColor.windowBackgroundColor))
                    .cornerRadius(8)
                }
            }
            Spacer()
        }
        .padding()
        .onAppear {
            history = repo.guardHistory
        }
    }

    private func runCmd(_ action: GuardAction) async {
        runningActionID = action.id
        lastCommand = action.command
        lastStatusLabel = "running"
        await runner.run(command: action.command)
        let status: GuardStatus = runner.lastStatus == 0 ? .ok : .issue
        lastStatusLabel = status == .ok ? "ok" : "issue"
        history.insert(GuardRun(id: UUID(), label: action.label, status: status, timestamp: Date()), at: 0)
        repo.guardHistory = history
        repo.saveHistory(history)
        runningActionID = nil
    }

    var capabilityStatus: GuardStatus {
        let bad = repo.capabilityHealth.capabilities.first { $0.status != "ok" }
        return bad == nil ? .ok : .issue
    }
}

struct RemoteFetchSection: View {
    @EnvironmentObject var repo: DataRepository
    @State private var remoteURL: String = ""
    @State private var fetching = false

    private var statusText: String {
        switch repo.dataSource {
        case .local:
            return "Using local workspace artifacts (bundled fallback if missing)."
        case .remote:
            switch repo.remoteStatus {
            case "ok": return "Remote data loaded" + (remoteURL.isEmpty ? "" : " from \(remoteURL)")
            case "fetching": return "Fetching remote data…"
            case "error": return "Remote fetch failed; showing last loaded data."
            default: return "Remote data idle"
            }
        }
    }

    private var statusTint: Color {
        switch repo.dataSource {
        case .local: return .gray
        case .remote:
            switch repo.remoteStatus {
            case "ok": return .green
            case "fetching": return .blue
            case "error": return .orange
            default: return .secondary
            }
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Data Source")
                    .font(.headline)
                Spacer()
                Picker("Source", selection: $repo.dataSource) {
                    ForEach(DataSource.allCases) { source in
                        Text(source.title).tag(source)
                    }
                }
                .pickerStyle(.segmented)
                .frame(maxWidth: 260)
            }

            HStack(spacing: 10) {
                Circle().fill(statusTint).frame(width: 10, height: 10)
                Text(statusText)
                    .font(.footnote)
                    .foregroundColor(.primary)
                Spacer()
            }
            .padding(10)
            .background(statusTint.opacity(0.08))
            .cornerRadius(10)

            if repo.dataSource == .remote {
                HStack {
                    TextField("Remote base URL", text: $remoteURL)
                        .textFieldStyle(.roundedBorder)
                    Button {
                        guard let url = URL(string: remoteURL), !remoteURL.isEmpty else { return }
                        fetching = true
                        Task {
                            await repo.fetchRemote(baseURL: url)
                            fetching = false
                        }
                    } label: {
                        if fetching || repo.remoteStatus == "fetching" {
                            ProgressView().controlSize(.small)
                        } else {
                            Label("Fetch latest", systemImage: "arrow.clockwise")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(fetching || remoteURL.isEmpty)
                }
            } else {
                Text("Switch to Remote to pull live JSON from a base URL (expects graph.json, capability-health.json, token-drift.json, and run-envelopes.jsonl or agent-runs.json).")
                    .font(.footnote)
                    .foregroundColor(.secondary)
            }
        }
        .onAppear {
            if remoteURL.isEmpty, let existing = repo.remoteBaseURL?.absoluteString { remoteURL = existing }
        }
        .onChange(of: repo.dataSource, initial: false) { new, _ in
            if new == .local {
                repo.loadLocalArtifacts()
            } else if let url = URL(string: remoteURL), !remoteURL.isEmpty {
                fetching = true
                Task { await repo.fetchRemote(baseURL: url); fetching = false }
            }
        }
    }
}

struct GuardAction: Identifiable {
    let id: String
    let title: String
    let systemImage: String
    let command: String
    let label: String
}

struct ActionButton: View {
    let action: GuardAction
    @Binding var isRunning: Bool
    let run: () async -> Void
    var disabled: Bool

    var body: some View {
        Button {
            isRunning = true
            Task { await run(); isRunning = false }
        } label: {
            if isRunning {
                ProgressView()
                    .controlSize(.small)
                    .frame(width: 80)
            } else {
                Label(action.title, systemImage: action.systemImage)
            }
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.small)
        .frame(minWidth: 140)
        .disabled(disabled)
    }
}

struct GuardActions: View {
    let actions: [GuardAction]
    @Binding var runningActionID: String?
    let run: (GuardAction) async -> Void

    var body: some View {
        let anyRunning = runningActionID != nil
        HStack(spacing: 12) {
            ForEach(actions) { action in
                ActionButton(
                    action: action,
                    isRunning: Binding(
                        get: { runningActionID == action.id },
                        set: { runningActionID = $0 ? action.id : nil }
                    ),
                    run: { await run(action) },
                    disabled: anyRunning && runningActionID != action.id
                )
            }
        }
    }
}

struct StatusChip: View {
    let text: String
    let status: GuardStatus
    var body: some View {
        HStack(spacing: 6) {
            Circle().fill(status == .ok ? Color.green : Color.orange).frame(width: 8, height: 8)
            Text(text).font(.footnote.bold())
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(.thinMaterial)
        .cornerRadius(20)
    }
}

enum GuardStatus { case ok, issue }

struct GuardRun: Identifiable, Codable {
    let id: UUID
    let label: String
    let statusRaw: String
    let timestamp: Date

    var status: GuardStatus { statusRaw == "ok" ? .ok : .issue }

    init(id: UUID, label: String, status: GuardStatus, timestamp: Date) {
        self.id = id
        self.label = label
        self.statusRaw = status == .ok ? "ok" : "issue"
        self.timestamp = timestamp
    }
}

struct GuardList: View {
    let title: String
    let status: GuardStatus
    let detail: String?
    var body: some View {
        HStack {
            Label(title, systemImage: status == .ok ? "checkmark.seal.fill" : "exclamationmark.triangle.fill")
                .foregroundColor(status == .ok ? .green : .orange)
            Spacer()
            if let detail = detail { Text(detail).foregroundColor(.secondary) }
        }
        .padding(10)
        .background(.thinMaterial)
        .cornerRadius(10)
    }
}

struct MetricCard: View {
    let title: String
    let value: Any
    var tint: Color = .accentColor
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.caption).foregroundColor(.secondary)
            Text(String(describing: value)).font(.title.bold())
        }
        .padding()
        .frame(maxWidth: .infinity)
        .background(.thinMaterial)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(tint.opacity(0.2), lineWidth: 1)
        )
    }
}

#Preview {
    ContentView()
        .environmentObject(DataRepository())
}
