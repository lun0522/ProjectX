//
//  CaptureViewController.swift
//  EmoArt
//
//  Created by Pujun Lun on 2/28/18.
//  Copyright © 2018 Pujun Lun. All rights reserved.
//

import UIKit

class CaptureViewController: UIViewController, UITextFieldDelegate, UIImagePickerControllerDelegate, UINavigationControllerDelegate, VideoCaptureDelegate {
    
    static let kDotsRadius: CGFloat = 6.0
    
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
        
        LocalDetector.sharedInstance.initialize()
        PEAServer.sharedInstance.initialize()
        
        do {
            try videoLayer = VideoLayer.newLayer(withCamera: .front, delegate: self)
        } catch {
            showError("Cannot initialize video layer: " + error.localizedDescription)
            return
        }
        
        shapeLayer.lineWidth = 2.0
        shapeLayer.setAffineTransform(CGAffineTransform(scaleX: 1, y: -1))
        view.layer.insertSublayer(shapeLayer, at: 0)
        view.layer.insertSublayer(videoLayer, at: 0)
        
        viewBoundsSize = view.bounds.size
        imagePicker.delegate = self
        
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
        LocalDetector.sharedInstance.detectFaceLandmarks(
            in: frame,
            resultHandler: {
                [unowned self] (detectionResult, error) in
                self.clearShapeLayer()
                
                var didFindFace = false
                defer {
                    if !didFindFace {
                        self.faceBoundingBox = nil
                    }
                }
                
                guard error == nil else {
                    self.showError(error!.localizedDescription)
                    return
                }
                guard let result = detectionResult else {
                    self.showError("Detection returns no result")
                    return
                }
                
                func draw(_ landmarks: [CGPoint], in faceRect: CGRect, drawFace: Bool) {
                    didFindFace = true
                    self.faceBoundingBox = faceRect
                    self.drawPoints(landmarks)
                    if drawFace {
                        self.drawRectangle(self.scale(faceRect, to: self.viewBoundsSize))
                    }
                }
                
                switch result {
                case .notFound:
                    break
                case let .foundByDetection(faceBoundingBox, landmarks):
                    draw(landmarks, in: faceBoundingBox, drawFace: true)
                case let .foundByTracking(faceBoundingBox, landmarks):
                    draw(landmarks, in: faceBoundingBox, drawFace: false)
                }
        })
    }
    
    // MARK: - select photo with image picker
    
    @IBAction func tapSelectPhoto(_ sender: UIButton) {
        let alert = UIAlertController(title: nil, message: nil, preferredStyle: .actionSheet)
        alert.addAction(UIAlertAction(title: "From album", style: .default, handler: {
            [unowned self] action in
            self.showImagePicker(sourceType: .photoLibrary)
        }))
        alert.addAction(UIAlertAction(title: "Take a photo", style: .default, handler: {
            [unowned self] action in
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
                    [unowned self] (response, error) in
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
        
        guard let photo = selectedPhoto else {
            showError("Cannnot retrieve photo")
            return
        }
        
        if picker.sourceType == .camera {
            // rotate the retrieved image
            UIGraphicsBeginImageContextWithOptions(photo.size, false, photo.scale);
            photo.draw(in: CGRect(origin: CGPoint(x: 0, y: 0), size: photo.size))
            selectedPhoto = UIGraphicsGetImageFromCurrentImageContext();
            UIGraphicsEndImageContext();
        }
        
        guard let photoData = UIImageJPEGRepresentation(selectedPhoto!, 1.0) else {
            showError("Cannot extract photo data")
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
        
        // crop down face part
        var faceImage = lastFrame!.cropped(to: scale(boundingBox, to: lastFrame!.extent.size))
        // mirror it if using back camera
        if videoLayer.currentCameraPosition == .back {
            faceImage = faceImage.transformed(by: CGAffineTransform(scaleX: -1, y: 1))
        }
        // convert CIImage to CGImage, and then to UIImage
        // otherwise UIImageJPEGRepresentation() will return nil
        guard let cgImage = CIContext().createCGImage(faceImage, from: faceImage.extent) else {
            showError("Cannot create cgImage")
            return
        }
        selfieData = UIImageJPEGRepresentation(UIImage(cgImage: cgImage), 1.0)
        
        videoLayer.stop()
        clearShapeLayer()
        performSegue(withIdentifier: "showPickStyle", sender: self)
    }
    
    override func prepare(for segue: UIStoryboardSegue, sender: Any?) {
        guard let svc = segue.destination as? SelectViewController else {
            assertionFailure("Internal error: Wrong destination")
            return
        }
        svc.selfieData = selfieData!
        svc.originalPhoto = selectedPhoto!
        svc.photoTimestamp = photoTimestamp
    }
    
    // MARK: - draw UI elements
    
    func scale(_ rect: CGRect, to size: CGSize) -> CGRect {
        return CGRect(x: rect.origin.x * size.width,
                      y: rect.origin.y * size.height,
                      width: rect.size.width * size.width,
                      height: rect.size.height * size.height)
    }
    
    func drawPoints(_ points: [CGPoint]) {
        DispatchQueue.main.async {
            let _ = points.map {
                let pointLayer = CAShapeLayer()
                pointLayer.fillColor = UIColor.red.cgColor
                let dotRect = CGRect(
                    x: $0.x * self.viewBoundsSize.width - CaptureViewController.kDotsRadius / 2.0,
                    y: $0.y * self.viewBoundsSize.height - CaptureViewController.kDotsRadius / 2.0,
                    width: CaptureViewController.kDotsRadius,
                    height: CaptureViewController.kDotsRadius)
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
            self.shapeLayer.sublayers = nil
        }
    }
    
    @IBAction func tapSwitchCamera(_ sender: UIButton) {
        do {
            try videoLayer.switchCamera()
        } catch {
            showError("Error in switching camera: " + error.localizedDescription)
            return
        }
        // flip shape layer horizontally
        clearShapeLayer()
        shapeLayer.setAffineTransform(shapeLayer.affineTransform().scaledBy(x: -1, y: 1))
    }
    
}
