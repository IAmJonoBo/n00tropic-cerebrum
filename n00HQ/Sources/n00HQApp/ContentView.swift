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
    @StateObject private var vm = GraphViewModel()
    var kinds: [String] {
        let ks = Set(repo.graph.nodes.map { $0.kind })
        return ["all"] + ks.sorted()
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Picker("Kind", selection: $selectedKind) {
                ForEach(kinds, id: \.self) { kind in
                    Text(kind.capitalized).tag(kind)
                }
            }
            .pickerStyle(.segmented)

            TextField("Search nodes", text: $search)
                .textFieldStyle(.roundedBorder)

            HStack {
                List(vm.filtered) { node in
                    VStack(alignment: .leading) {
                        Text(node.title ?? node.id).font(.headline)
                        Text(node.kind).font(.footnote).foregroundColor(.secondary)
                        if let tags = node.tags { Text(tags.joined(separator: ", ")).font(.footnote) }
                    }
                    .onTapGesture { vm.selection = node }
                }
                .frame(minWidth: 280)

                Divider()

                VStack {
                    ForceGraphView(nodes: vm.filtered, edges: filteredEdges)
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
    }

    private var filteredEdges: [GraphEdge] {
        if selectedKind == "all" { return repo.graph.edges }
        let nodeIds = Set(vm.filtered.map { $0.id })
        return repo.graph.edges.filter { nodeIds.contains($0.from) && nodeIds.contains($0.to) }
    }

    private func relatedEdges(for node: GraphNode) -> [GraphEdge]? {
        repo.graph.edges.filter { $0.from == node.id || $0.to == node.id }
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
                        Text(run.capability_id ?? run.id).font(.headline)
                        Text(run.summary ?? "").font(.subheadline)
                        HStack {
                            Label(run.status ?? "", systemImage: run.status == "ok" ? "checkmark.circle.fill" : "exclamationmark.circle.fill")
                                .foregroundColor(run.status == "ok" ? .green : .orange)
                            if let started = run.started_at { Text(started).font(.footnote).foregroundColor(.secondary) }
                            if let completed = run.completed_at { Text("→ \(completed)").font(.footnote).foregroundColor(.secondary) }
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
}

struct ManagementView: View {
    @EnvironmentObject var repo: DataRepository
    @StateObject private var runner = ScriptRunner()
    @State private var running: Bool = false
    @State private var lastCommand: String = ""
    @State private var lastStatusLabel: String = ""
    @State private var history: [GuardRun] = []
    @State private var loadingHistory: Bool = true
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Management & Drift Guards")
                .font(.title3.bold())
            GuardList(title: "Token Drift", status: repo.tokenDrift.drift == true ? .issue : .ok, detail: repo.tokenDrift.validation_reason)
            GuardList(title: "Capability Health", status: capabilityStatus, detail: nil)
            GuardList(title: "Toolchain Pins", status: .ok, detail: "Checked in policy-sync")
            GuardList(title: "Typesense Freshness", status: .ok, detail: "See nightly guard")

            GuardActions(running: $running) { cmd, label in
                await runCmd(cmd, label: label)
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
                }
            }
            Spacer()
        }
        .padding()
        .disabled(running)
        .onAppear {
            history = repo.guardHistory
            loadingHistory = false
        }
    }

    private func runCmd(_ cmd: String, label: String) async {
        running = true
        lastCommand = cmd
        lastStatusLabel = "running"
        await runner.run(command: cmd)
        let status: GuardStatus = runner.lastStatus == 0 ? .ok : .issue
        lastStatusLabel = status == .ok ? "ok" : "issue"
        history.insert(GuardRun(id: UUID(), label: label, status: status, timestamp: Date()), at: 0)
        repo.guardHistory = history
        repo.saveHistory(history)
        running = false
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
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Data Source")
                .font(.headline)
            HStack {
                TextField("Remote base URL (optional)", text: $remoteURL)
                    .textFieldStyle(.roundedBorder)
                Button("Fetch latest") {
                    guard let url = URL(string: remoteURL), !remoteURL.isEmpty else { return }
                    fetching = true
                    Task { await repo.fetchRemote(baseURL: url); fetching = false }
                }
                .buttonStyle(.bordered)
                .disabled(fetching || remoteURL.isEmpty)
            }
            if fetching { Text("Fetching...").foregroundColor(.secondary).font(.footnote) }
            else if repo.remoteStatus == "ok" { Text("Remote data loaded").foregroundColor(.green).font(.footnote) }
            else if repo.remoteStatus == "error" { Text("Remote fetch failed").foregroundColor(.orange).font(.footnote) }
        }
    }
}

struct ActionButton: View {
    let title: String
    let systemImage: String
    let action: () async -> Void
    @State private var isRunning = false
    var body: some View {
        Button {
            isRunning = true
            Task { await action(); isRunning = false }
        } label: {
            Label(title, systemImage: systemImage)
        }
        .buttonStyle(.borderedProminent)
        .controlSize(.small)
        .disabled(isRunning)
    }
}

struct GuardActions: View {
    @Binding var running: Bool
    let run: (String, String) async -> Void
    var body: some View {
        HStack(spacing: 12) {
            ActionButton(title: "Toolchain pins", systemImage: "bolt.fill") {
                await run("node scripts/check-toolchain-pins.mjs --json", "toolchain pins")
            }
            ActionButton(title: "Token drift", systemImage: "aqi.medium") {
                await run(".dev/automation/scripts/token-drift.sh", "token drift")
            }
            ActionButton(title: "Typesense", systemImage: "network") {
                await run(".dev/automation/scripts/typesense-freshness.sh 7", "typesense")
            }
        }
        .disabled(running)
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
