import SwiftUI

struct ForceGraphView: View {
    let nodes: [GraphNode]
    let edges: [GraphEdge]
    @Binding var selection: GraphNode?
    var onSelect: ((GraphNode) -> Void)? = nil

    private var neighborIDs: Set<String> {
        guard let sel = selection else { return [] }
        let connected = edges.filter { $0.from == sel.id || $0.to == sel.id }
        return Set(connected.flatMap { [$0.from, $0.to] })
    }

    var body: some View {
        GeometryReader { geo in
            Canvas { context, size in
                let layout = ForceLayout.compute(nodes: nodes, edges: edges, size: size)
                let neighbors = neighborIDs

                for edge in edges {
                    guard let a = layout[edge.from], let b = layout[edge.to] else { continue }
                    let selected = selection?.id == edge.from || selection?.id == edge.to
                    let stroke = selected ? Color.accentColor.opacity(0.85) : Color.secondary.opacity(selection == nil ? 0.45 : 0.15)
                    var path = Path()
                    path.move(to: a)
                    path.addLine(to: b)
                    context.stroke(path, with: .color(stroke), lineWidth: selected ? 1.6 : 0.9)
                }

                for node in nodes {
                    guard let pt = layout[node.id] else { continue }
                    let isSelected = selection?.id == node.id
                    let isNeighbor = neighbors.contains(node.id)
                    let radius: CGFloat = isSelected ? 10 : (isNeighbor ? 8 : 6)
                    let opacity: Double = isSelected ? 1 : (selection == nil ? 0.9 : (isNeighbor ? 0.75 : 0.25))
                    let circle = Path(ellipseIn: CGRect(x: pt.x - radius, y: pt.y - radius, width: radius * 2, height: radius * 2))
                    context.fill(circle, with: .color(kindColor(node.kind).opacity(opacity)))
                    if isSelected {
                        let halo = Path(ellipseIn: CGRect(x: pt.x - radius - 4, y: pt.y - radius - 4, width: (radius + 4) * 2, height: (radius + 4) * 2))
                        context.stroke(halo, with: .color(Color.accentColor.opacity(0.35)), lineWidth: 2)
                    }
                }
            }
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 0).onEnded { value in
                    let layout = ForceLayout.compute(nodes: nodes, edges: edges, size: geo.size)
                    if let hit = nearestNode(at: value.location, layout: layout) {
                        selection = hit
                        onSelect?(hit)
                    }
                }
            )
        }
        .frame(minHeight: 260)
        .background(Color(NSColor.windowBackgroundColor))
        .cornerRadius(12)
    }

    private func nearestNode(at location: CGPoint, layout: [String: CGPoint]) -> GraphNode? {
        guard !nodes.isEmpty else { return nil }
        let target = nodes.min { lhs, rhs in
            let ld = layout[lhs.id]?.distance(to: location) ?? .infinity
            let rd = layout[rhs.id]?.distance(to: location) ?? .infinity
            return ld < rd
        }
        if let node = target, let point = layout[node.id], point.distance(to: location) < 18 {
            return node
        }
        return nil
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
    static func compute(nodes: [GraphNode], edges: [GraphEdge], size: CGSize) -> [String: CGPoint] {
        guard !nodes.isEmpty else { return [:] }
        let center = CGPoint(x: size.width / 2, y: size.height / 2)
        let kinds = Array(Set(nodes.map { $0.kind })).sorted()
        let clusterRadius = min(size.width, size.height) * 0.32
        let padding: CGFloat = 24

        var clusterCenters: [String: CGPoint] = [:]
        for (idx, kind) in kinds.enumerated() {
            let angle = (2 * .pi * CGFloat(idx)) / CGFloat(max(kinds.count, 1))
            let point = CGPoint(
                x: center.x + cos(angle) * clusterRadius,
                y: center.y + sin(angle) * clusterRadius
            )
            clusterCenters[kind] = point
        }

        var positions: [String: CGPoint] = [:]
        var velocities: [String: CGPoint] = [:]
        for (idx, node) in nodes.enumerated() {
            let base = clusterCenters[node.kind] ?? center
            let jitter = ForceLayout.jitter(for: idx)
            positions[node.id] = CGPoint(x: base.x + jitter.x, y: base.y + jitter.y)
            velocities[node.id] = .zero
        }

        let idealLength: CGFloat = 100
        let charge: CGFloat = 2400
        let damping: CGFloat = 0.85

        for _ in 0..<80 {
            for node in nodes {
                guard var pos = positions[node.id] else { continue }
                var force = CGPoint.zero
                for other in nodes where other.id != node.id {
                    guard let otherPos = positions[other.id] else { continue }
                    let delta = pos - otherPos
                    let dist = max(delta.length, 8)
                    let repulse = charge / (dist * dist)
                    force += delta.normalized * repulse
                }
                if let cluster = clusterCenters[node.kind] {
                    let toCluster = cluster - pos
                    force += toCluster.normalized * 0.6 * idealLength
                }
                velocities[node.id]? += force * 0.002
            }

            for edge in edges {
                guard let from = positions[edge.from], let to = positions[edge.to] else { continue }
                let delta = to - from
                let dist = max(delta.length, 1)
                let spring = (dist - idealLength) * 0.004
                let offset = delta.normalized * spring
                velocities[edge.from]? += offset
                velocities[edge.to]? -= offset
            }

            for node in nodes {
                guard var pos = positions[node.id], var vel = velocities[node.id] else { continue }
                vel = vel * damping
                pos += vel
                pos.x = min(max(pos.x, padding), size.width - padding)
                pos.y = min(max(pos.y, padding), size.height - padding)
                positions[node.id] = pos
                velocities[node.id] = vel
            }
        }

        return positions
    }

    private static func jitter(for index: Int) -> CGPoint {
        let seed = Double((index &* 1664525 &+ 1013904223) % 1000) / 1000.0
        let angle = seed * 2 * Double.pi
        let radius = 10 + 8 * seed
        return CGPoint(x: cos(angle) * radius, y: sin(angle) * radius)
    }
}

private extension CGPoint {
    var length: CGFloat { sqrt(x * x + y * y) }

    var normalized: CGPoint {
        let len = length
        guard len > 0 else { return .zero }
        return CGPoint(x: x / len, y: y / len)
    }

    func distance(to other: CGPoint) -> CGFloat {
        let dx = x - other.x
        let dy = y - other.y
        return sqrt(dx * dx + dy * dy)
    }

    static func +(lhs: CGPoint, rhs: CGPoint) -> CGPoint { CGPoint(x: lhs.x + rhs.x, y: lhs.y + rhs.y) }
    static func -(lhs: CGPoint, rhs: CGPoint) -> CGPoint { CGPoint(x: lhs.x - rhs.x, y: lhs.y - rhs.y) }
    static func *(lhs: CGPoint, rhs: CGFloat) -> CGPoint { CGPoint(x: lhs.x * rhs, y: lhs.y * rhs) }
    static func +=(lhs: inout CGPoint, rhs: CGPoint) { lhs = lhs + rhs }
    static func -=(lhs: inout CGPoint, rhs: CGPoint) { lhs = lhs - rhs }
}
