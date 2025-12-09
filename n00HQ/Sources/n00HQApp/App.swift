import SwiftUI

@main
struct N00HQApp: App {
    @StateObject private var repo = DataRepository()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(repo)
                .onAppear { repo.loadAll() }
        }
    }
}
