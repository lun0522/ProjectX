//
//  EMAError.swift
//  EmoArt
//
//  Created by Pujun Lun on 2/19/18.
//  Copyright © 2018 Pujun Lun. All rights reserved.
//

import Foundation

class EMAError: NSObject, Error {
    
    var domain: Domain!
    var reason: String!
    
    enum Domain: String {
        case videoLayerSetup = "Error in video layer setup: "
        case videoLayerOperation = "Error in operating video layer: "
        case sendingData = "Error in sending data: "
        case faceDetection = "Error in face detection: "
        case faceTracking = "Error in face tracking: "
        case landmarksDetection = "Error in landmarks detection: "
    }
    
    init(in domain: Domain, reason: String) {
        self.domain = domain
        self.reason = reason
    }
    
    var errorDescription: String {
        return domain.rawValue + reason
    }
    
}
