import XCTest
@testable import DashboardApp

final class DashboardAppTests: XCTestCase {
    func testStatusIndicatorMapping() {
        let ok = Dashboard.StatusCode.ok
        let indicator = Dashboard.ViewModel.StatusIndicator(statusCode: ok)
        XCTAssertEqual(indicator, .ok)
    }

    func testChatMessageAppendHelper() {
        let original = Dashboard.ViewModel.ChatMessage(
            role: .assistant,
            text: "hello",
            status: .informational,
            capabilityId: "demo",
            stream: .stdout
        )
        let combined = original.appending(" world")
        XCTAssertEqual(combined.text, "hello world")
        XCTAssertEqual(combined.capabilityId, original.capabilityId)
        XCTAssertEqual(combined.stream, .stdout)
    }
}
