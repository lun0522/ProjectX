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
        case foundByDetection(CGRect)
        case foundByTracking(CGRect)
    }
    
    let faceDetection = VNDetectFaceRectanglesRequest()
    let landmarksDetection = VNDetectFaceLandmarksRequest()
    var lastObservation: VNFaceObservation?
    let faceDetectionRequest = VNSequenceRequestHandler()
    let landmarksDetectionRequest = VNSequenceRequestHandler()
    var faceTrackingRequest = VNSequenceRequestHandler()
    var faceHandler: ((DetectionResult?, EMAError?) -> Swift.Void)?
    var landmarksHandler: (([CGPoint]?, EMAError?) -> Swift.Void)?
    var timestamp = Date().timeIntervalSince1970
    var tracking = false
    
    public func detectFace(inImage image: CIImage,
                           faceDetectionResultHandler: @escaping (DetectionResult?, EMAError?) -> Swift.Void,
                           landmarksDetectionResultHandler: @escaping ([CGPoint]?, EMAError?) -> Swift.Void) {
        faceHandler = faceDetectionResultHandler
        landmarksHandler = landmarksDetectionResultHandler
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
    
    func faceDetectionSuccess(_ result: DetectionResult) {
        if let handler = faceHandler {
            handler(result, nil)
            faceHandler = nil
        } else {
            log("No handler when face detection did success")
        }
    }
    
    func landmarksDetectionSuccess(_ result: [CGPoint]) {
        if let handler = landmarksHandler {
            handler(result, nil)
            landmarksHandler = nil
        } else {
            log("No handler when landmarks detection did success")
        }
    }
    
    func detectionFail(in domain: EMAErrorDomain, reason: String) {
        switch domain {
        case .faceDetection, .faceTracking:
            if let handler = faceHandler {
                handler(nil, EMAError(domain: domain, reason: reason))
                faceHandler = nil
            } else {
                log("No handler when face detection did fail")
            }
        case .landmarksDetection:
            if let handler = landmarksHandler {
                handler(nil, EMAError(domain: domain, reason: reason))
                landmarksHandler = nil
            } else {
                log("No handler when landmarks detection did fail")
            }
        default:
            log("Detection failed with unknown error type")
        }
    }
    
    func detectFace(inImage image: CIImage) {
        do {
            try faceDetectionRequest.perform([faceDetection], on: image)
        } catch {
            detectionFail(in: .faceDetection, reason: error.localizedDescription)
            return
        }
        
        guard let results = faceDetection.results as? [VNFaceObservation] else {
            detectionFail(in: .faceDetection, reason: "Wrong type")
            return
        }
        guard results.count > 0 else {
            faceDetectionSuccess(.notFound)
            return
        }
        
        lastObservation = results.max {
            $0.boundingBox.width * $0.boundingBox.height < $1.boundingBox.width * $1.boundingBox.height
        }
        trackFace(inImage: image)
        tracking = true
    }
    
    func trackFace(inImage image: CIImage) {
        guard let lastObservation = self.lastObservation else {
            detectionFail(in: .faceTracking, reason: "No face observation")
            return
        }
        
        // The default tracking level of VNTrackObjectRequest is .fast,
        // which results that the confidence is either 0.0 or 1.0.
        // For more precise results, it should be set to .accurate,
        // so that the confidence floats between 0.0 and 1.0
        let faceTracking = VNTrackObjectRequest(
            detectedObjectObservation: lastObservation,
            completionHandler: {
                (request, error) in
                var didFindFace = false
                defer {
                    // https://stackoverflow.com/a/46355234/7873124
                    // Re-instantiate the request handler if the face is lost
                    if didFindFace == false {
                        self.faceTrackingRequest = VNSequenceRequestHandler()
                    }
                }
                
                guard error == nil else {
                    self.detectionFail(in: .faceTracking, reason: error!.localizedDescription)
                    return
                }
                guard let results = request.results, results.count > 0 else {
                    self.detectionFail(in: .faceTracking, reason: "No face")
                    return
                }
                guard let observation = results[0] as? VNFaceObservation else {
                    self.detectionFail(in: .faceTracking, reason: "Wrong type")
                    return
                }
                didFindFace = true
                self.lastObservation = observation
        })
        faceTracking.trackingLevel = .accurate
        
        do {
            try faceTrackingRequest.perform([faceTracking], on: image)
        } catch {
            self.detectionFail(in: .faceTracking, reason: error.localizedDescription)
            return
        }
        
        if Double(lastObservation.confidence) < LocalDetector.kTrackingConfidenceThreshold {
            tracking = false
            detectFace(inImage: image)
        } else {
            detectLandmarks(inImage: image, bound: lastObservation.boundingBox)
        }
    }
    
    func detectLandmarks(inImage image: CIImage, bound boundingBox: CGRect) {
        do {
            landmarksDetection.inputFaceObservations = [VNFaceObservation(boundingBox: boundingBox)]
            try landmarksDetectionRequest.perform([landmarksDetection], on: image)
        } catch {
            detectionFail(in: .landmarksDetection, reason: error.localizedDescription)
            return
        }
        
        guard let results = landmarksDetection.results, results.count > 0 else {
            detectionFail(in: .landmarksDetection, reason: "No face")
            return
        }
        guard let faceObservation = results[0] as? VNFaceObservation else {
            detectionFail(in: .landmarksDetection, reason: "Wrong type")
            return
        }
        guard let landmarks = faceObservation.landmarks else {
            detectionFail(in: .landmarksDetection, reason: "No landmarks")
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
        
        if tracking {
            faceDetectionSuccess(.foundByTracking(boundingBox))
        } else {
            faceDetectionSuccess(.foundByDetection(boundingBox))
        }
        landmarksDetectionSuccess(landmarksPoints)
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
