import SwiftUI

struct CommandPaletteView: View {
    @EnvironmentObject var repo: DataRepository
    @Binding var searchText: String

    var filteredCaps: [CapabilityHealthItem] {
        if searchText.isEmpty { return repo.capabilityHealth.capabilities }
        return repo.capabilityHealth.capabilities.filter { cap in
            cap.id.localizedCaseInsensitiveContains(searchText) ||
            (cap.summary ?? "").localizedCaseInsensitiveContains(searchText)
        }
    }

    var filteredNodes: [GraphNode] {
        if searchText.isEmpty { return repo.graph.nodes }
        return repo.graph.nodes.filter { node in
            (node.title ?? node.id).localizedCaseInsensitiveContains(searchText)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Command Palette")
                .font(.title3.bold())
            TextField("Search capabilities, graph nodes...", text: $searchText)
                .textFieldStyle(.roundedBorder)

            if !filteredCaps.isEmpty {
                Text("Capabilities")
                    .font(.subheadline.bold())
                List(filteredCaps.prefix(20)) { cap in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(cap.id).font(.headline)
                        Text(cap.summary ?? "").font(.footnote).foregroundColor(.secondary)
                    }
                }
                .listStyle(.plain)
                .frame(maxHeight: 240)
            }

            if !filteredNodes.isEmpty {
                Text("Graph")
                    .font(.subheadline.bold())
                List(filteredNodes.prefix(20)) { node in
                    VStack(alignment: .leading) {
                        Text(node.title ?? node.id).font(.headline)
                        Text(node.kind).font(.footnote).foregroundColor(.secondary)
                    }
                }
                .listStyle(.plain)
                .frame(maxHeight: 240)
            }

            Spacer()
        }
        .padding()
        .frame(minWidth: 520, minHeight: 480)
    }
}

#Preview {
    CommandPaletteView(searchText: .constant(""))
        .environmentObject(DataRepository())
}
