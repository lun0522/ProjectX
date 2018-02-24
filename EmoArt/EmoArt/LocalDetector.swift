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

class LocalDetector: NSObject {
    
    static let sharedInstance = LocalDetector()
    static let kDetectionTimeIntervalThreshold = 0.5
    static let kTrackingConfidenceThreshold = 0.8
    
    enum DetectionResult {
        case notFound
        case foundByDetection(CGRect)
        case foundByTracking(CGRect)
    }
    
    private let faceDetection = VNDetectFaceRectanglesRequest()
    private let landmarksDetection = VNDetectFaceLandmarksRequest()
    private var lastObservation: VNFaceObservation?
    private let faceDetectionRequest = VNSequenceRequestHandler()
    private let landmarksDetectionRequest = VNSequenceRequestHandler()
    private var faceTrackingRequest = VNSequenceRequestHandler()
    private var faceHandler: ((DetectionResult?, EMAError?) -> Swift.Void)?
    private var landmarksHandler: (([CGPoint]?, EMAError?) -> Swift.Void)?
    private var timestamp: TimeInterval = Date().timeIntervalSince1970
    private var tracking = false
    
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
    
    private func log(_ message: String) {
        print("[LocalDetector] " + message)
    }
    
    private func faceDetectionSuccess(_ result: DetectionResult) {
        if let handler = faceHandler {
            handler(result, nil)
            faceHandler = nil
        } else {
            log("No handler when face detection did success")
        }
    }
    
    private func faceDetectionFail(with error: EMAError) {
        if let handler = faceHandler {
            handler(nil, error)
            faceHandler = nil
        } else {
            log("No handler when face detection did fail")
        }
    }
    
    private func landmarksDetectionSuccess(_ result: [CGPoint]) {
        if let handler = landmarksHandler {
            handler(result, nil)
            landmarksHandler = nil
        } else {
            log("No handler when landmarks detection did success")
        }
    }
    
    private func landmarksDetectionFail(with error: EMAError) {
        if let handler = landmarksHandler {
            handler(nil, error)
            landmarksHandler = nil
        } else {
            log("No handler when landmarks detection did fail")
        }
    }
    
    private func detectFace(inImage image: CIImage) {
        do {
            try faceDetectionRequest.perform([faceDetection], on: image)
        } catch {
            faceDetectionFail(with: .faceDetectionError(error.localizedDescription))
        }
        
        guard let results = faceDetection.results as? [VNFaceObservation] else {
            faceDetectionFail(with: .faceDetectionError("Wrong type"))
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
    
    private func trackFace(inImage image: CIImage) {
        guard let lastObservation = self.lastObservation else {
            faceDetectionFail(with: .faceTrackingError("No face observation"))
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
                    self.faceDetectionFail(with: .faceTrackingError(error!.localizedDescription))
                    return
                }
                guard let results = request.results, results.count > 0 else {
                    self.faceDetectionFail(with: .faceTrackingError("No face"))
                    return
                }
                guard let observation = results[0] as? VNFaceObservation else {
                    self.faceDetectionFail(with: .faceTrackingError("Wrong type"))
                    return
                }
                didFindFace = true
                self.lastObservation = observation
        })
        faceTracking.trackingLevel = .accurate
        
        do {
            try faceTrackingRequest.perform([faceTracking], on: image)
        } catch {
            self.faceDetectionFail(with: .faceTrackingError(error.localizedDescription))
            return
        }
        
        if Double(lastObservation.confidence) < LocalDetector.kTrackingConfidenceThreshold {
            tracking = false
            detectFace(inImage: image)
        } else {
            detectLandmarks(inImage: image, bound: lastObservation.boundingBox)
        }
    }
    
    private func detectLandmarks(inImage image: CIImage,
                                 bound boundingBox: CGRect) {
        do {
            landmarksDetection.inputFaceObservations = [VNFaceObservation(boundingBox: boundingBox)]
            try landmarksDetectionRequest.perform([landmarksDetection], on: image)
        } catch {
            landmarksDetectionFail(with: .landmarksDetectionError(error.localizedDescription))
            return
        }
        
        guard let results = landmarksDetection.results, results.count > 0 else {
            landmarksDetectionFail(with: .landmarksDetectionError("No face"))
            return
        }
        guard let faceObservation = results[0] as? VNFaceObservation else {
            landmarksDetectionFail(with: .landmarksDetectionError("Wrong type"))
            return
        }
        guard let landmarks = faceObservation.landmarks else {
            landmarksDetectionFail(with: .landmarksDetectionError("No landmarks"))
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
    
    private func scale(_ points: [CGPoint]?, toRect rect: CGRect) -> [CGPoint] {
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
