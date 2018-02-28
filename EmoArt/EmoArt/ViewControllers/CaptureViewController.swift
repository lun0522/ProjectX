//
//  CaptureViewController.swift
//  EmoArt
//
//  Created by Pujun Lun on 2/28/18.
//  Copyright © 2018 Pujun Lun. All rights reserved.
//

import UIKit

class CaptureViewController: UIViewController, UITextFieldDelegate, UIImagePickerControllerDelegate, UINavigationControllerDelegate, VideoCaptureDelegate {
    
    static let kLandmarksDotsRadius: CGFloat = 6.0
    
    var videoLayer: VideoLayer!
    let shapeLayer = CAShapeLayer()
    let imagePicker = UIImagePickerController()
    var selectedPhoto: UIImage?
    var photoTimestamp: String?
    var lastFrame: CIImage?
    var faceBoundingBox: CGRect?
    var selfieData: Data?
    var viewBoundsSize: CGSize!

    @IBOutlet weak var selectPhotoButton: UIButton!
    @IBOutlet weak var captureFaceButton: UIButton!
    @IBOutlet weak var switchCameraButton: UIButton!
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        do {
            try videoLayer = VideoLayer.newLayer(withCamera: .front, delegate: self)
        } catch {
            showError("Cannot initialize video layer: " + error.localizedDescription)
            return
        }
        view.layer.addSublayer(videoLayer)
        view.layer.addSublayer(shapeLayer)
        shapeLayer.strokeColor = UIColor.red.cgColor
        shapeLayer.lineWidth = 2.0
        shapeLayer.setAffineTransform(CGAffineTransform(scaleX: -1, y: -1))
        imagePicker.delegate = self
        viewBoundsSize = view.bounds.size
        
        let _ = [selectPhotoButton,
                 captureFaceButton,
                 switchCameraButton].map {
                    if let button = $0 {
                        button.layer.cornerRadius = 8.0
                        button.layer.borderWidth = 1.0
                        button.layer.borderColor = switchCameraButton.tintColor.cgColor
                    }
        }
    }
    
    override func viewDidLayoutSubviews() {
        videoLayer.frame = view.frame
        shapeLayer.frame = view.frame
    }
    
    override func viewWillAppear(_ animated: Bool) {
        videoLayer.start()
    }

    func showError(_ description: String) {
        let alert = UIAlertController(title: "Error", message: description, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .cancel, handler: nil))
        DispatchQueue.main.async {
            self.present(alert, animated: true, completion: nil)
        }
    }
    
    // MARK: - handle result from local detector
    
    func didCaptureFrame(_ frame: CIImage) {
        lastFrame = frame
        LocalDetector.sharedInstance.detectFace(
            inImage: frame,
            faceDetectionResultHandler: {
                (detectionResult, error) in
                var didFindFace = false
                defer {
                    if !didFindFace {
                        self.faceBoundingBox = nil
                        self.clearShapeLayer()
                    }
                }
                
                guard error == nil else {
                    self.showError(error!.localizedDescription)
                    return
                }
                guard let result = detectionResult else {
                    self.showError("Face detection returns no result")
                    return
                }
                
                switch result {
                case .notFound:
                    break
                case let .foundByDetection(boundingBox):
                    self.drawRectangle(self.scale(boundingBox, to: self.viewBoundsSize))
                    didFindFace = true
                    self.faceBoundingBox = boundingBox
                case let .foundByTracking(boundingBox):
                    didFindFace = true
                    self.faceBoundingBox = boundingBox
                }
        },
            landmarksDetectionResultHandler: {
                (detectionResult, error) in
                self.clearShapeLayer()
                guard error == nil else {
                    self.showError(error!.localizedDescription)
                    return
                }
                guard let points = detectionResult else {
                    self.showError("Landmarks detection returns no result")
                    return
                }
                self.drawPoints(points)
        })
    }
    
    // MARK: - select photo with image picker
    
    @IBAction func tapSelectPhoto(_ sender: UIButton) {
        let alert = UIAlertController(title: nil, message: nil, preferredStyle: .actionSheet)
        alert.addAction(UIAlertAction(title: "From album", style: .default, handler: { action in
            self.showImagePicker(sourceType: .photoLibrary)
        }))
        alert.addAction(UIAlertAction(title: "Take a photo", style: .default, handler: { action in
            self.showImagePicker(sourceType: .camera)
        }))
        alert.addAction(UIAlertAction(title: "Cancel", style: .cancel, handler: nil))
        DispatchQueue.main.async {
            self.present(alert, animated: true, completion: nil)
        }
    }
    
    func showImagePicker(sourceType: UIImagePickerControllerSourceType) {
        videoLayer.stop()
        imagePicker.sourceType = sourceType
        DispatchQueue.main.async {
            self.present(self.imagePicker, animated: true, completion: nil)
        }
    }
    
    func imagePickerController(_ picker: UIImagePickerController,
                               didFinishPickingMediaWithInfo info: [String : Any]) {
        dismiss(animated: true, completion: nil)
        videoLayer.start()
        
        func request(data: Data, operation: PEAServer.Operation) {
            PEAServer.sharedInstance.sendData(
                data,
                headerFields: ["Photo-Timestamp": photoTimestamp!],
                operation: operation,
                timeout: 10) {
                    (response, error) in
                    guard error == nil else {
                        self.showError("Error in " + operation.rawValue + ": " + error!.localizedDescription)
                        return
                    }
            }
        }
        
        if let _ = photoTimestamp {
            request(data: Data(), operation: .delete)
        }
        photoTimestamp = String(UInt(NSDate().timeIntervalSince1970 * 1000))
        selectedPhoto = info[UIImagePickerControllerOriginalImage] as? UIImage
        guard let _ = selectedPhoto, let photoData = UIImageJPEGRepresentation(selectedPhoto!, 1.0) else {
            showError("Cannot retrieve selected photo")
            return
        }
        request(data: photoData, operation: .store)
    }
    
    func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
        dismiss(animated: true, completion: nil)
        videoLayer.start()
    }
    
    // MARK: - show pick style view
    
    @IBAction func tapCaptureFace(_ sender: UIButton) {
        guard let _ = selectedPhoto else {
            showError("Please select a photo")
            return
        }
        guard let boundingBox = faceBoundingBox else {
            showError("No face found")
            return
        }
        
        // crop down the face part and mirror it
        let faceImage = lastFrame!.cropped(to: scale(boundingBox, to: lastFrame!.extent.size))
        let mirroredImage = faceImage.transformed(by: CGAffineTransform(scaleX: -1, y: 1))
        // convert CIImage to CGImage, and then to UIImage
        // otherwise UIImageJPEGRepresentation() will return nil
        guard let cgImage = CIContext().createCGImage(mirroredImage, from: mirroredImage.extent) else {
            showError("Cannot create cgImage")
            return
        }
        selfieData = UIImageJPEGRepresentation(UIImage(cgImage: cgImage), 1.0)
        
        videoLayer.stop()
        performSegue(withIdentifier: "showPickStyle", sender: self)
    }
    
    override func prepare(for segue: UIStoryboardSegue, sender: Any?) {
        guard let svc = segue.destination as? SelectViewController else {
            assertionFailure("Internal error: wrong destination")
            return
        }
        svc.selfieData = selfieData!
        svc.originalPhoto = selectedPhoto!
        svc.photoTimestamp = photoTimestamp
    }
    
    // MARK: - draw UI elements
    
    func scale(_ rect: CGRect, to size: CGSize) -> CGRect {
        return CGRect(x: rect.origin.x / rect.size.width * size.width,
                      y: rect.origin.y / rect.size.height * size.height,
                      width: size.width,
                      height: size.height)
    }
    
    func drawPoints(_ points: [CGPoint]) {
        DispatchQueue.main.async {
            let _ = points.map {
                let pointLayer = CAShapeLayer()
                pointLayer.fillColor = UIColor.red.cgColor
                let dotRect = CGRect(x: $0.x, y: $0.y,
                                     width: CaptureViewController.kLandmarksDotsRadius,
                                     height: CaptureViewController.kLandmarksDotsRadius)
                pointLayer.path = UIBezierPath(ovalIn: dotRect).cgPath
                self.shapeLayer.addSublayer(pointLayer)
            }
        }
    }
    
    func drawRectangle(_ rect: CGRect) {
        DispatchQueue.main.async {
            let rectLayer = CAShapeLayer()
            rectLayer.fillColor = UIColor.clear.cgColor
            rectLayer.strokeColor = UIColor.red.cgColor
            rectLayer.path = UIBezierPath(rect: rect).cgPath
            self.shapeLayer.addSublayer(rectLayer)
        }
    }
    
    func clearShapeLayer() {
        DispatchQueue.main.async {
            let _ = self.shapeLayer.sublayers?.map { $0.removeFromSuperlayer() }
        }
    }
    
    @IBAction func tapSwitchCamera(_ sender: UIButton) {
        do {
            try videoLayer.switchCamera()
        } catch {
            showError("Error in switching camera: " + error.localizedDescription)
        }
    }
    
}
