import SwiftUI

struct ChatConsoleView: View {
    @EnvironmentObject var viewModel: Dashboard.ViewModel
    @State private var draft: String = ""
    @State private var selectedCapability: Dashboard.ViewModel.Capability?
    @State private var runCheck: Bool = false
    @State private var capabilitySearch: String = ""
    @State private var showCheckableOnly: Bool = false
    @Namespace private var scrollAnchor

    private var filteredCapabilities: [Dashboard.ViewModel.Capability] {
        let query = capabilitySearch.trimmingCharacters(in: .whitespacesAndNewlines)
        return viewModel.capabilities.filter { capability in
            let matchesSearch = query.isEmpty
                || capability.id.localizedCaseInsensitiveContains(query)
                || capability.summary.localizedCaseInsensitiveContains(query)
            let matchesCheck = !showCheckableOnly || capability.supportsCheck
            return matchesSearch && matchesCheck
        }
    }

    private var canSend: Bool {
        if viewModel.isExecutingCapability { return false }
        let trimmed = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        if selectedCapability != nil {
            return true
        }
        return !trimmed.isEmpty
    }

    var body: some View {
        HStack(alignment: .top, spacing: 20) {
            capabilityColumn
                .frame(minWidth: 260, maxWidth: 320)
            VStack(alignment: .leading, spacing: 16) {
                header
                conversation
                inputBar
            }
            .frame(maxWidth: .infinity, alignment: .top)
            workspacePanel
                .frame(minWidth: 260, maxWidth: 320)
        }
        .padding()
        .background(Color(nsColor: .windowBackgroundColor))
        .onChange(of: selectedCapability) { newValue in
            if newValue?.supportsCheck != true {
                runCheck = false
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 12) {
                Label("n00t Orchestrator", systemImage: "sparkles")
                    .font(.largeTitle.bold())
                if let active = viewModel.activeCapabilityId {
                    Dashboard.StatusBadge(status: .informational)
                        .help("Currently running \(active)")
                }
                Spacer()
                if viewModel.isExecutingCapability {
                    Button(role: .destructive) {
                        viewModel.cancelActiveExecution()
                    } label: {
                        Label("Cancel Run", systemImage: "stop.circle.fill")
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.red)
                    .help("Terminate the active capability run")
                }
            }
            if let active = viewModel.activeCapabilityId {
                Text("Executing \(active)…")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                Text("Chat with the orchestrator, launch automation capabilities, and review results in one place.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            if let warning = viewModel.capabilityError {
                Label(warning, systemImage: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                    .font(.footnote)
            } else if viewModel.isLoadingCapabilities {
                HStack(spacing: 8) {
                    ProgressView()
                        .scaleEffect(0.7)
                    Text("Discovering capabilities…")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            } else {
                Text("\(viewModel.capabilities.count) capabilities ready.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var capabilityColumn: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("Capabilities", systemImage: "bolt.fill")
                    .font(.title3.bold())
                Spacer()
                if selectedCapability != nil {
                    Button {
                        selectedCapability = nil
                        runCheck = false
                    } label: {
                        Label("Clear", systemImage: "xmark.circle")
                    }
                    .buttonStyle(.bordered)
                    .help("Reset selection")
                }
            }
            TextField("Search capabilities…", text: $capabilitySearch)
                .textFieldStyle(.roundedBorder)
            Toggle("Supports check mode", isOn: $showCheckableOnly)
                .toggleStyle(.switch)
                .font(.caption)
                .help("Filter to capabilities that expose a --check mode")
            Divider()
            if filteredCapabilities.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Label("No capabilities match the filters.", systemImage: "questionmark.circle")
                        .foregroundStyle(.secondary)
                    Text("Clear the search or run a workspace refresh.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 8) {
                        ForEach(filteredCapabilities) { capability in
                            CapabilityListRow(
                                capability: capability,
                                isSelected: capability.id == selectedCapability?.id,
                                isActive: viewModel.activeCapabilityId == capability.id
                            ) {
                                selectedCapability = capability
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
            Divider()
            if let capability = selectedCapability {
                capabilityDetail(for: capability)
            } else {
                Text("Select a capability to inspect inputs, provenance, and run options.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Color(nsColor: .textBackgroundColor))
                .shadow(color: .black.opacity(0.05), radius: 6, x: 0, y: 2)
        )
    }

    private func capabilityDetail(for capability: Dashboard.ViewModel.Capability) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Selected Capability")
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(capability.summary)
                .font(.headline)
            Text(capability.id)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Label(capability.origin, systemImage: "signpost.right")
                .font(.caption2)
                .foregroundStyle(.secondary)
            if capability.supportsCheck {
                Toggle("Run in check mode", isOn: $runCheck)
                    .toggleStyle(.switch)
                    .font(.caption)
            }
            HStack(spacing: 12) {
                Button {
                    send()
                } label: {
                    Label("Run Capability", systemImage: "play.circle.fill")
                }
                .buttonStyle(.borderedProminent)
                .disabled(!canSend || (viewModel.isExecutingCapability && viewModel.activeCapabilityId != capability.id))

                Button {
                    draft = "Run \(capability.summary.lowercased())"
                } label: {
                    Label("Prefill Prompt", systemImage: "text.badge.plus")
                }
                .buttonStyle(.bordered)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor))
        )
    }

    private var conversation: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    ForEach(viewModel.messages) { message in
                        ChatBubble(message: message)
                    }
                    Color.clear
                        .frame(height: 1)
                        .id(scrollAnchor)
                }
                .padding(.vertical, 12)
                .padding(.horizontal, 8)
            }
            .background(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .fill(Color(nsColor: .textBackgroundColor))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .stroke(Color.secondary.opacity(0.12))
                    )
            )
            .onChange(of: viewModel.messages.count) { _ in
                withAnimation(.easeOut(duration: 0.25)) {
                    proxy.scrollTo(scrollAnchor, anchor: .bottom)
                }
            }
        }
    }

    private var inputBar: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .bottom, spacing: 12) {
                Menu {
                    Button("No automation") { selectedCapability = nil }
                    Divider()
                    ForEach(viewModel.capabilities) { capability in
                        Button {
                            selectedCapability = capability
                        } label: {
                            Text(capability.summary)
                        }
                    }
                } label: {
                    Label(selectedCapability?.summary ?? "Choose Capability", systemImage: "slider.horizontal.3")
                        .labelStyle(.titleAndIcon)
                }
                .help("Select which capability to pair with the prompt")

                TextField("Ask n00t for help…", text: $draft, axis: .vertical)
                    .lineLimit(1...4)
                    .textFieldStyle(.roundedBorder)

                Button {
                    send()
                } label: {
                    Label("Send", systemImage: "paperplane.fill")
                }
                .buttonStyle(.borderedProminent)
                .disabled(!canSend)

                Button("Reset") {
                    viewModel.clearChat()
                    draft = ""
                    selectedCapability = nil
                    runCheck = false
                }
                .buttonStyle(.bordered)
                .help("Clear the transcript and selection")
            }
            if viewModel.isExecutingCapability {
                Text("Running capability…")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var workspacePanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Label("Workspace Signals", systemImage: "waveform.path.ecg")
                    .font(.title3.bold())
                Spacer()
                if viewModel.isRefreshing {
                    ProgressView().scaleEffect(0.7)
                }
            }
            Divider()
            WorkspaceInsightCard(
                title: "Meta-check",
                status: viewModel.metaCheckState.statusIndicator,
                summary: viewModel.metaCheckState.summary,
                actionTitle: "View details"
            ) {
                viewModel.selection = .metaCheck
            }
            WorkspaceInsightCard(
                title: "Dependencies",
                status: viewModel.dependencyDashboard.status,
                summary: dependencySummary,
                actionTitle: "Open dashboard"
            ) {
                viewModel.selection = .dependencies
            }
            WorkspaceInsightCard(
                title: "Overrides",
                status: overridesStatus,
                summary: overridesSummary,
                actionTitle: "Review overrides"
            ) {
                viewModel.selection = .overrides
            }
            WorkspaceInsightCard(
                title: "Agent Runs",
                status: agentRunsStatus,
                summary: agentRunsSummary,
                actionTitle: "Inspect runs"
            ) {
                viewModel.selection = .agents
            }
            Spacer(minLength: 0)
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Color(nsColor: .textBackgroundColor))
        )
    }

    private var dependencySummary: String {
        let dashboard = viewModel.dependencyDashboard
        if dashboard.repositoryCount == 0 {
            return "No dependency reports available yet."
        }
        var summary = "\(dashboard.repositoryCount) repos tracked."
        if let pending = dashboard.pendingPRs, pending > 0 {
            summary += " \(pending) Renovate PRs open."
        }
        if !dashboard.findings.isEmpty {
            summary += " Active findings: \(dashboard.findings.count)."
        }
        return summary
    }

    private var overridesStatus: Dashboard.ViewModel.StatusIndicator {
        viewModel.overrideSummaries.isEmpty ? .ok : .warning
    }

    private var overridesSummary: String {
        if viewModel.overrideSummaries.isEmpty {
            return "No active policy overrides."
        }
        let total = viewModel.overrideSummaries.reduce(0) { $0 + $1.entries.count }
        return "\(total) override\(total == 1 ? "" : "s") require review."
    }

    private var agentRunsStatus: Dashboard.ViewModel.StatusIndicator {
        viewModel.agentRuns.first?.status ?? .informational
    }

    private var agentRunsSummary: String {
        if viewModel.agentRuns.isEmpty {
            return "No agent runs logged yet."
        }
        let latest = viewModel.agentRuns.first!
        return "\(latest.capability) \(latest.status.label.lowercased()) • \(latest.started.formatted(date: .abbreviated, time: .shortened))"
    }

    private func send() {
        viewModel.sendChat(text: draft, capability: selectedCapability, runCheck: runCheck)
        draft = ""
        if selectedCapability?.supportsCheck != true {
            runCheck = false
        }
    }
}

private struct CapabilityListRow: View {
    let capability: Dashboard.ViewModel.Capability
    let isSelected: Bool
    let isActive: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text(capability.summary)
                        .font(.headline)
                        .foregroundStyle(.primary)
                    Spacer()
                    if isActive {
                        Label("Running", systemImage: "bolt.fill")
                            .font(.caption2)
                            .foregroundStyle(.green)
                    }
                }
                Text(capability.id)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                if capability.supportsCheck {
                    Label("Supports --check", systemImage: "checkmark.shield")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.vertical, 8)
            .padding(.horizontal, 10)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(isSelected ? Color.accentColor.opacity(0.15) : Color.clear)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .stroke(isSelected ? Color.accentColor : Color.secondary.opacity(0.1), lineWidth: isSelected ? 1.5 : 1)
            )
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("capability-\(capability.id)")
    }
}

private struct WorkspaceInsightCard: View {
    let title: String
    let status: Dashboard.ViewModel.StatusIndicator
    let summary: String
    let actionTitle: String
    let action: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(title)
                    .font(.headline)
                Spacer()
                Dashboard.StatusBadge(status: status)
            }
            Text(summary)
                .font(.caption)
                .foregroundStyle(.secondary)
            Button(actionTitle, action: action)
                .buttonStyle(.bordered)
                .font(.caption)
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 10, style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor))
        )
    }
}

private struct ChatBubble: View {
    let message: Dashboard.ViewModel.ChatMessage

    var body: some View {
        HStack {
            if message.role == .user {
                Spacer(minLength: 0)
            }
            VStack(alignment: message.role == .user ? .trailing : .leading, spacing: 6) {
                HStack(spacing: 6) {
                    if let capability = message.capabilityId {
                        Text(capability)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                    if message.stream != .transcript {
                        Label(message.stream == .stdout ? "stdout" : "stderr",
                              systemImage: message.stream == .stdout ? "arrow.up.doc" : "exclamationmark.triangle")
                            .font(.caption2)
                            .foregroundStyle(message.stream == .stderr ? Color.orange : Color.secondary)
                    }
                }
                Text(message.text)
                    .font(.body)
                    .foregroundStyle(foreground)
                    .frame(maxWidth: 420, alignment: message.role == .user ? .trailing : .leading)
                HStack(spacing: 6) {
                    if let status = message.status {
                        Label(status.label, systemImage: statusIcon(for: status))
                            .font(.caption2)
                            .foregroundStyle(status.color)
                    }
                    Text(message.timestamp, style: .time)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.vertical, 10)
            .padding(.horizontal, 12)
            .background(bubbleColor)
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            if message.role != .user {
                Spacer(minLength: 0)
            }
        }
        .padding(.horizontal, 6)
    }

    private var bubbleColor: Color {
        switch message.role {
        case .user:
            return Color.accentColor
        case .assistant:
            switch message.stream {
            case .stdout:
                return Color.secondary.opacity(0.12)
            case .stderr:
                return Color.red.opacity(0.18)
            case .transcript:
                return Color.secondary.opacity(0.15)
            }
        case .system:
            return Color.blue.opacity(0.2)
        case .event:
            return Color.orange.opacity(0.15)
        }
    }

    private var foreground: Color {
        message.role == .user ? .white : .primary
    }

    private func statusIcon(for status: Dashboard.ViewModel.StatusIndicator) -> String {
        switch status {
        case .ok: return "checkmark.circle.fill"
        case .warning: return "exclamationmark.triangle.fill"
        case .failed: return "xmark.octagon.fill"
        case .skipped: return "forward.end.alt"
        case .informational: return "info.circle.fill"
        case .unknown: return "questionmark.circle.fill"
        }
    }
}
