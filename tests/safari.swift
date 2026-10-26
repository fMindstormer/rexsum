// Check every pattern in Safari's engine, the WebKit that ships with macOS, with the page's JavaScript
// turned off: the HTML pattern attribute alone must mark each test string valid or invalid as the
// reference checker says. The harness sets the values and reads :valid from a script world of its own,
// which a page without JavaScript still allows. The first check compiles the pattern; after that,
// every keystroke costs one check.
//   swiftc -O tests/safari.swift -o safari-check && ./safari-check patterns.json tests/cases.json [name ...]
import AppKit
import WebKit

setvbuf(stdout, nil, _IOLBF, 0)
let args = CommandLine.arguments
let text = try! String(contentsOfFile: args[1], encoding: .utf8)
let pats = try! JSONSerialization.jsonObject(with: Data(text.utf8)) as! [String: [String: Any]]
let cases = try! JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: args[2]))) as! [String: [[Any]]]
let only = Set(args.dropFirst(3))
func place(_ name: String) -> String.Index { text.range(of: "\"\(name)\": {")?.lowerBound ?? text.endIndex }

final class Loaded: NSObject, WKNavigationDelegate {
    var done = false
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { done = true }
}

func wait(_ until: () -> Bool) {
    while !until() { RunLoop.main.run(mode: .default, before: .now + 0.01) }
}

func attr(_ s: String) -> String {
    s.replacingOccurrences(of: "&", with: "&amp;").replacingOccurrences(of: "\"", with: "&quot;")
        .replacingOccurrences(of: "<", with: "&lt;").replacingOccurrences(of: ">", with: "&gt;")
}

let check = """
    const f = document.getElementById("f");
    let t0 = performance.now();
    f.value = cases[0][0];
    f.matches(":valid");
    const first = performance.now() - t0, bad = [];
    t0 = performance.now();
    for (const [s, want] of cases) {
      f.value = s;
      if (f.matches(":valid") !== !!want) bad.push(s);
    }
    return {first, each: (performance.now() - t0) / cases.length, bad, pageScript: document.title === "ran"};
    """

_ = NSApplication.shared
let safari = Bundle(path: "/Applications/Safari.app")?.infoDictionary?["CFBundleShortVersionString"] as? String ?? "?"
let webkit = Bundle(identifier: "com.apple.WebKit")?.infoDictionary?["CFBundleVersion"] as? String ?? "?"
var machine = utsname(); uname(&machine)
let arch = withUnsafeBytes(of: &machine.machine) { String(decoding: $0.prefix(while: { $0 != 0 }), as: UTF8.self) }
print("Safari \(safari), WebKit \(webkit), \(ProcessInfo.processInfo.operatingSystemVersionString), \(arch), " +
      ISO8601DateFormatter().string(from: Date()).prefix(10))
let config = WKWebViewConfiguration()
config.defaultWebpagePreferences.allowsContentJavaScript = false
let view = WKWebView(frame: .zero, configuration: config)
let loaded = Loaded()
view.navigationDelegate = loaded

var totalBad = 0
for name in pats.keys.sorted(by: { place($0) < place($1) }) where only.isEmpty || only.contains(name) {
    let pattern = pats[name]!["pattern"] as! String
    loaded.done = false
    view.loadHTMLString("<script>document.title = \"ran\"</script><form><input id=\"f\" pattern=\"\(attr(pattern))\"></form>",
                        baseURL: nil)
    wait { loaded.done }
    var out: Result<Any, Error>?
    view.callAsyncJavaScript(check, arguments: ["cases": cases[name]!], in: nil, in: .defaultClient) { out = $0 }
    wait { out != nil }
    let r = try! out!.get() as! [String: Any]
    precondition(r["pageScript"] as! Bool == false, "the page's own script ran")
    let bad = r["bad"] as! [String]
    totalBad += bad.count
    print(name.padding(toLength: 8, withPad: " ", startingAt: 0) + String(format: " %7d chars: first check %.0f ms, then %.0f µs each, ",
          pattern.utf16.count, r["first"] as! Double, (r["each"] as! Double) * 1000)
          + "\(cases[name]!.count) strings, mismatches \(bad.count) \(bad.prefix(3).joined(separator: " "))")
}
exit(totalBad > 0 ? 1 : 0)
