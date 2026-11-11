import Foundation
import PDFKit
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count >= 4, let doc = PDFDocument(url: URL(fileURLWithPath: args[1])),
      let first = Int(args[2]), let last = Int(args[3]) else { print("usage: ocr file first last [fast]"); exit(1) }
let fast = args.count > 4
for i in (first - 1)..<min(last, doc.pageCount) {
  autoreleasepool {
    guard let page = doc.page(at: i) else { return }
    let b = page.bounds(for: .mediaBox)
    let img = page.thumbnail(of: NSSize(width: b.width * 2, height: b.height * 2), for: .mediaBox)
    guard let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = fast ? .fast : .accurate
    req.recognitionLanguages = ["de-DE"]
    req.usesLanguageCorrection = !fast
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    let text = (req.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
    print("=== PAGE \(i + 1)")
    print(text)
    fflush(stdout)
  }
}
