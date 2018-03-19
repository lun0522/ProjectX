//
//  LocalDetector.swift
//  EmoArt
//
//  Created by Pujun Lun on 2/20/18.
//  Copyright © 2018 Pujun Lun. All rights reserved.
//

import Foundation
import CoreGraphics
import Vision

class LocalDetector {
    
    static let sharedInstance = LocalDetector()
    static let kDetectionTimeIntervalThreshold = 0.5
    static let kTrackingConfidenceThreshold = 0.8
    
    enum DetectionResult {
        case notFound
        case foundByDetection(CGRect, [CGPoint])
        case foundByTracking(CGRect, [CGPoint])
    }
    
    let faceDetection = VNDetectFaceRectanglesRequest()
    let landmarksDetection = VNDetectFaceLandmarksRequest()
    var lastObservation: VNDetectedObjectObservation?
    let faceDetectionRequest = VNSequenceRequestHandler()
    let landmarksDetectionRequest = VNSequenceRequestHandler()
    var faceTrackingRequest: VNSequenceRequestHandler?
    var resultHandler: ((DetectionResult?, EMAError?) -> Void)?
    var timestamp = Date().timeIntervalSince1970
    var tracking = false
    
    /// empty body
    /// used to initialize the singleton beforehand
    public func initialize() { }
    
    public func detectFaceLandmarks(in image: CIImage,
                                    resultHandler: @escaping (DetectionResult?, EMAError?) -> Void) {
        self.resultHandler = resultHandler
        let currentTime = Date().timeIntervalSince1970
        let doTracking = tracking && (currentTime - timestamp < LocalDetector.kDetectionTimeIntervalThreshold)
        timestamp = currentTime
        if doTracking {
            trackFace(inImage: image)
        } else {
            detectFace(inImage: image)
        }
    }
    
    func log(_ message: String) {
        print("[LocalDetector] " + message)
    }
    
    func detectionDidSuccess(_ result: DetectionResult) {
        if let handler = resultHandler {
            handler(result, nil)
            resultHandler = nil
        } else {
            log("No handler when detection did success")
        }
    }
    
    func detectionDidFail(in domain: EMAErrorDomain, reason: String) {
        guard let handler = resultHandler else {
            log("No handler when detection did fail")
            return
        }
        handler(nil, EMAError(domain: domain, reason: reason))
    }
    
    func detectFace(inImage image: CIImage) {
        do {
            try faceDetectionRequest.perform([faceDetection], on: image)
        } catch {
            detectionDidFail(in: .faceDetection, reason: error.localizedDescription)
            return
        }
        
        guard let results = faceDetection.results as? [VNFaceObservation] else {
            detectionDidFail(in: .faceDetection, reason: "Wrong type")
            return
        }
        guard results.count > 0 else {
            detectionDidSuccess(.notFound)
            return
        }
        
        lastObservation = results.max {
            $0.boundingBox.width * $0.boundingBox.height < $1.boundingBox.width * $1.boundingBox.height
        }
        detectLandmarks(inImage: image)
        tracking = true
        // https://stackoverflow.com/a/46355234/7873124
        // Re-instantiate the request handler after the first frame used for tracking changes,
        // to avoid that Vision throws "Exceeded maximum allowed number of Trackers" error
        faceTrackingRequest = VNSequenceRequestHandler()
    }
    
    func trackFace(inImage image: CIImage) {
        guard let lastObservation = self.lastObservation else {
            detectionDidFail(in: .faceTracking, reason: "No face observation")
            return
        }
        
        // The default tracking level of VNTrackObjectRequest is .fast,
        // which results that the confidence is either 0.0 or 1.0.
        // For more precise results, it should be set to .accurate,
        // so that the confidence floats between 0.0 and 1.0
        let faceTracking = VNTrackObjectRequest(
            detectedObjectObservation: lastObservation,
            completionHandler: {
                [unowned self] (request, error) in
                guard error == nil else {
                    self.detectionDidFail(in: .faceTracking, reason: error!.localizedDescription)
                    return
                }
                guard let results = request.results, results.count > 0 else {
                    self.detectionDidFail(in: .faceTracking, reason: "No face")
                    return
                }
                guard let observation = results[0] as? VNDetectedObjectObservation else {
                    self.detectionDidFail(in: .faceTracking, reason: "Wrong type")
                    return
                }
                self.lastObservation = observation
        })
        faceTracking.trackingLevel = .accurate
        
        guard let request = faceTrackingRequest else {
            self.detectionDidFail(in: .faceTracking, reason: "No face tracking request")
            return
        }
        do {
            try request.perform([faceTracking], on: image)
        } catch {
            self.detectionDidFail(in: .faceTracking, reason: error.localizedDescription)
            return
        }
        
        if Double(lastObservation.confidence) < LocalDetector.kTrackingConfidenceThreshold {
            tracking = false
            detectFace(inImage: image)
        } else {
            detectLandmarks(inImage: image)
        }
    }
    
    func detectLandmarks(inImage image: CIImage) {
        let boundingBox = self.lastObservation!.boundingBox
        do {
            landmarksDetection.inputFaceObservations = [VNFaceObservation(boundingBox: boundingBox)]
            try landmarksDetectionRequest.perform([landmarksDetection], on: image)
        } catch {
            detectionDidFail(in: .landmarksDetection, reason: error.localizedDescription)
            return
        }
        
        guard let results = landmarksDetection.results, results.count > 0 else {
            detectionDidFail(in: .landmarksDetection, reason: "No face")
            return
        }
        guard let faceObservation = results[0] as? VNFaceObservation else {
            detectionDidFail(in: .landmarksDetection, reason: "Wrong type")
            return
        }
        guard let landmarks = faceObservation.landmarks else {
            detectionDidFail(in: .landmarksDetection, reason: "No landmarks")
            return
        }
        
        var landmarksPoints = [CGPoint]()
        let _ = [
            landmarks.leftEyebrow,
            landmarks.rightEyebrow,
            landmarks.noseCrest,
            landmarks.nose,
            landmarks.leftEye,
            landmarks.rightEye,
            landmarks.outerLips,
            landmarks.innerLips
            ].map { landmarksPoints.append(contentsOf: scale($0?.normalizedPoints, toRect: boundingBox)) }
        
        detectionDidSuccess(tracking ?
            .foundByTracking(boundingBox, landmarksPoints) :
            .foundByDetection(boundingBox, landmarksPoints))
    }
    
    func scale(_ points: [CGPoint]?, toRect rect: CGRect) -> [CGPoint] {
        if let _ = points {
            return points!.map {
                CGPoint(x: $0.x * rect.size.width  + rect.origin.x,
                        y: $0.y * rect.size.height + rect.origin.y)
            };
        } else {
            return []
        }
    }
    
}
