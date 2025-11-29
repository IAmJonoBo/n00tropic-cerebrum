import SwiftUI

struct ForceGraphView: View {
    let nodes: [GraphNode]
    let edges: [GraphEdge]
    var onSelect: ((GraphNode) -> Void)? = nil

    var body: some View {
        Canvas { context, size in
            let layout = ForceLayout.compute(nodes: nodes, size: size)
            
            // edges
            context.stroke(Path { p in
                for e in edges {
                    guard let a = layout[e.from], let b = layout[e.to] else { continue }
                    p.move(to: a)
                    p.addLine(to: b)
                }
            }, with: .color(.secondary.opacity(0.5)))

            // nodes
            for n in nodes {
                guard let pt = layout[n.id] else { continue }
                let color: Color = kindColor(n.kind)
                let circle = Path(ellipseIn: CGRect(x: pt.x-6, y: pt.y-6, width: 12, height: 12))
                context.fill(circle, with: .color(color))
            }
        }
        .frame(minHeight: 240)
        .background(Color(NSColor.windowBackgroundColor))
        .cornerRadius(12)
        .gesture(TapGesture().onEnded { location in
            // Simple nearest-node hit test
            // Note: Canvas coordinates are not directly available here; using layout proximity.
            // This is a best-effort interaction for now.
            // onSelect not used in current UI yet; ready for future upgrades.
            if let first = nodes.first, let layout = ForceLayout.compute(nodes: nodes, size: CGSize(width: 300, height: 300))[first.id] {
                _ = layout // placeholder to silence unused warnings
            }
        })
    }

    private func kindColor(_ kind: String) -> Color {
        switch kind {
        case "capability": return .blue
        case "template": return .purple
        case "schema": return .green
        case "doc": return .orange
        default: return .gray
        }
    }
}

enum ForceLayout {
    static func compute(nodes: [GraphNode], size: CGSize) -> [String: CGPoint] {
        // Simple layered layout by kind to improve readability.
        let kinds = Array(Set(nodes.map { $0.kind })).sorted()
        var map: [String: CGPoint] = [:]
        let layerHeight = kinds.isEmpty ? size.height : size.height / CGFloat(kinds.count + 1)
        for (layerIndex, kind) in kinds.enumerated() {
            let row = CGFloat(layerIndex + 1) * layerHeight
            let layerNodes = nodes.filter { $0.kind == kind }
            let count = max(layerNodes.count, 1)
            let step = size.width / CGFloat(count + 1)
            for (i, n) in layerNodes.enumerated() {
                let col = CGFloat(i + 1) * step
                map[n.id] = CGPoint(x: col, y: row)
            }
        }
        return map
    }
}
