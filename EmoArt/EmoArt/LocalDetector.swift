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
    
    private let faceDetection: VNDetectFaceRectanglesRequest = VNDetectFaceRectanglesRequest.init()
    private let landmarksDetection: VNDetectFaceLandmarksRequest = VNDetectFaceLandmarksRequest.init()
    private var lastObservation: VNFaceObservation?
    private var faceTracking: VNTrackObjectRequest?
    private let faceDetectionRequest: VNSequenceRequestHandler = VNSequenceRequestHandler.init()
    private let landmarksDetectionRequest: VNSequenceRequestHandler = VNSequenceRequestHandler.init()
    private var faceTrackingRequest: VNSequenceRequestHandler?
    private var timestamp: TimeInterval = Date.init().timeIntervalSince1970
    private var tracking: Bool = false
    
    public func detectFace(inImage image: CIImage,
                           faceDetectionResultHandler: @escaping (DetectionResult) -> Swift.Void,
                           landmarksDetectionResultHandler: @escaping ([NSValue]?, Error) -> Swift.Void) {
        
    }
    
    private func detectFace(inImage image: CIImage,
                            resultHandler: @escaping (DetectionResult) -> Swift.Void) {
        
    }
    
    private func trackFace(inImage image: CIImage,
                           resultHandler: @escaping (DetectionResult) -> Swift.Void) {
        
    }
    
    private func detectLandmarks(inImage image: CIImage,
                                 bound boundingBox: CGRect,
                                 resultHandler: @escaping ([CGPoint]?, Error?) -> Swift.Void) {
        do {
            landmarksDetection.inputFaceObservations = [VNFaceObservation.init(boundingBox: boundingBox)]
            try landmarksDetectionRequest.perform([landmarksDetection], on: image)
        } catch {
            resultHandler(nil, EMAError.faceLandmarksDetectionError("Error in face landmarks detection: " + error.localizedDescription))
            return
        }
        let faceObservation = landmarksDetection.results![0] as! VNFaceObservation
        let landmarks = faceObservation.landmarks!
        
        var landmarksPoints: [CGPoint] = []
        let _ = [
            landmarks.leftEyebrow,
            landmarks.rightEyebrow,
            landmarks.noseCrest,
            landmarks.nose,
            landmarks.leftEye,
            landmarks.rightEye,
            landmarks.outerLips,
            landmarks.innerLips
            ].map { landmarksPoints.append(contentsOf: scale($0?.normalizedPoints, 
                                                             toRect: boundingBox)) }
        resultHandler(landmarksPoints, nil)
    }
    
    private func scale(_ points: [CGPoint]?, toRect rect: CGRect) -> [CGPoint] {
        if let _ = points {
            return points!.map {
                CGPoint.init(x: $0.x * rect.size.width  + rect.origin.x,
                             y: $0.y * rect.size.height + rect.origin.y)
            };
        } else {
            return []
        }
    }
    
}
