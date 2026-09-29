import AppKit

let size = NSSize(width: 1024, height: 1024)
let image = NSImage(size: size)
image.lockFocus()
let background = NSBezierPath(roundedRect: NSRect(x: 54, y: 54, width: 916, height: 916), xRadius: 205, yRadius: 205)
NSGradient(starting: NSColor(calibratedRed: 0.16, green: 0.42, blue: 0.39, alpha: 1), ending: NSColor(calibratedRed: 0.06, green: 0.22, blue: 0.23, alpha: 1))!.draw(in: background, angle: -75)
let shadow = NSShadow()
shadow.shadowColor = NSColor.black.withAlphaComponent(0.25)
shadow.shadowBlurRadius = 35
shadow.shadowOffset = NSSize(width: 0, height: -15)
NSGraphicsContext.saveGraphicsState()
shadow.set()
NSColor(calibratedRed: 0.93, green: 0.9, blue: 0.79, alpha: 1).setFill()
NSBezierPath(roundedRect: NSRect(x: 255, y: 205, width: 505, height: 625), xRadius: 40, yRadius: 40).fill()
NSGraphicsContext.restoreGraphicsState()
NSColor(calibratedRed: 0.82, green: 0.79, blue: 0.66, alpha: 1).setFill()
NSBezierPath(roundedRect: NSRect(x: 255, y: 205, width: 62, height: 625), xRadius: 25, yRadius: 25).fill()
NSColor(calibratedRed: 0.72, green: 0.39, blue: 0.18, alpha: 1).setFill()
let ribbon = NSBezierPath()
ribbon.move(to: NSPoint(x: 649, y: 830)); ribbon.line(to: NSPoint(x: 699, y: 830)); ribbon.line(to: NSPoint(x: 699, y: 684)); ribbon.line(to: NSPoint(x: 674, y: 709)); ribbon.line(to: NSPoint(x: 649, y: 684)); ribbon.close(); ribbon.fill()
NSColor(calibratedRed: 0.12, green: 0.34, blue: 0.32, alpha: 1).setFill()
let blade = NSBezierPath()
blade.move(to: NSPoint(x: 472, y: 435)); blade.line(to: NSPoint(x: 580, y: 660)); blade.line(to: NSPoint(x: 640, y: 698)); blade.line(to: NSPoint(x: 646, y: 626)); blade.line(to: NSPoint(x: 512, y: 413)); blade.close(); blade.fill()
let guardPath = NSBezierPath()
guardPath.move(to: NSPoint(x: 433, y: 461)); guardPath.line(to: NSPoint(x: 558, y: 400)); guardPath.lineWidth = 24; guardPath.lineCapStyle = .round
NSColor(calibratedRed: 0.12, green: 0.34, blue: 0.32, alpha: 1).setStroke(); guardPath.stroke()
let handle = NSBezierPath()
handle.move(to: NSPoint(x: 490, y: 428)); handle.line(to: NSPoint(x: 452, y: 354)); handle.lineWidth = 24; handle.lineCapStyle = .round; handle.stroke()
let text = "XX" as NSString
text.draw(at: NSPoint(x: 612, y: 255), withAttributes: [.font: NSFont.systemFont(ofSize: 48, weight: .black), .foregroundColor: NSColor(calibratedRed: 0.12, green: 0.34, blue: 0.32, alpha: 1)])
image.unlockFocus()
let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!)!
try bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
