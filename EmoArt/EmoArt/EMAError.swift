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
    case faceLandmarksDetectionError(String)
}
