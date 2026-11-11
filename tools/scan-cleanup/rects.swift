import Foundation
import Vision
import AppKit

let path = CommandLine.arguments[1]
guard let img = NSImage(contentsOfFile: path),
      let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("load failed"); exit(1) }
let W = Double(cg.width), H = Double(cg.height)
func px(_ p: CGPoint) -> String { String(format: "(%.0f,%.0f)", p.x * W, (1 - p.y) * H) }

let doc = VNDetectDocumentSegmentationRequest()
let rect = VNDetectRectanglesRequest()
rect.minimumSize = 0.25
rect.maximumObservations = 8
rect.quadratureTolerance = 30
rect.minimumAspectRatio = 0.2
rect.maximumAspectRatio = 1.0
rect.minimumConfidence = 0.3
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
try handler.perform([doc, rect])
for o in (doc.results ?? []) {
    print("DOC conf=\(o.confidence) TL\(px(o.topLeft)) TR\(px(o.topRight)) BR\(px(o.bottomRight)) BL\(px(o.bottomLeft))")
}
for o in (rect.results ?? []) {
    print("RECT conf=\(o.confidence) TL\(px(o.topLeft)) TR\(px(o.topRight)) BR\(px(o.bottomRight)) BL\(px(o.bottomLeft))")
}
