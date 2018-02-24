//
//  EMAError.swift
//  EmoArt
//
//  Created by Pujun Lun on 2/19/18.
//  Copyright © 2018 Pujun Lun. All rights reserved.
//

enum EMAError: Error {
    
    case sendDataError(String)
    case faceDetectionError(String)
    case faceTrackingError(String)
    case landmarksDetectionError(String)
    
    var errorDescription: String {
        switch self {
        case let .sendDataError(description):
            return "Error in sending data: " + description
        case let .faceDetectionError(description):
            return "Error in face detection: " + description
        case let .faceTrackingError(description):
            return "Error in face tracking: " + description
        case let .landmarksDetectionError(description):
            return "Error in landmarks detection: " + description
        }
    }
    
}
