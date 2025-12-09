import Foundation
import SwiftUI

@MainActor
final class GraphViewModel: ObservableObject {
    @Published var filtered: [GraphNode] = []
    @Published var selection: GraphNode?

    func apply(nodes: [GraphNode], kind: String, search: String) {
        let base = kind == "all" ? nodes : nodes.filter { $0.kind == kind }
        if search.isEmpty {
            filtered = base
        } else {
            filtered = base.filter { ($0.title ?? $0.id).localizedCaseInsensitiveContains(search) }
        }
        if let current = selection, filtered.first(where: { $0.id == current.id }) == nil {
            selection = nil
        }
    }
}
