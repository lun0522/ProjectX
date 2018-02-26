//
//  EMAError.swift
//  EmoArt
//
//  Created by Pujun Lun on 2/19/18.
//  Copyright © 2018 Pujun Lun. All rights reserved.
//

import Foundation

enum EMAErrorDomain: String {
    case videoLayerSetup     = "video layer setup"
    case videoLayerOperation = "operating video layer"
    case sendingData         = "sending data"
    case faceDetection       = "face detection"
    case faceTracking        = "face tracking"
    case landmarksDetection  = "landmarks detection"
}

struct EMAError: Error {

    var domain: EMAErrorDomain
    var reason: String
    
    var errorDescription: String {
        return "Error in " + domain.rawValue + ": " + reason
    }
    
}
