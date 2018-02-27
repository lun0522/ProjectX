//
//  SelectViewController.swift
//  EmoArt
//
//  Created by Pujun Lun on 2/26/18.
//  Copyright © 2018 Pujun Lun. All rights reserved.
//

import UIKit

class SelectViewController: UIViewController {
    
    var selfieData: Data!
    var originalPhoto: UIImage!
    var photoTimestamp: String!
    var selectedPainting: Int = 0
    let blurEffectView = UIVisualEffectView()
    let transferIndicator = UIActivityIndicatorView(activityIndicatorStyle: .whiteLarge)
    var portraits = [UIImage]()
    var paintings = [UIImage]()
    var paintingsId = [String]()
    var stylizedImages = [Int : UIImage]()
    
    @IBOutlet weak var paintingView: UIImageView!
    @IBOutlet weak var firstPortraitView: UIImageView!
    @IBOutlet weak var secondPortraitView: UIImageView!
    @IBOutlet weak var thirdPortraitView: UIImageView!
    
    override func viewDidLoad() {
        super.viewDidLoad()
        blurEffectView.frame = view.frame
        transferIndicator.center = view.center
        transferIndicator.hidesWhenStopped = true
        retrievePaintings()
    }
    
    func showError(_ description: String) {
        let alert = UIAlertController(title: "Error", message: description, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .cancel, handler: nil))
        DispatchQueue.main.async {
            self.present(alert, animated: true, completion: nil)
        }
    }
    
    func retrievePaintings() {
        onProcessingAnimation()
        PEAServer.sharedInstance.sendData(
            selfieData,
            headerFields: nil,
            operation: .retrieve,
            timeout: 10) {
                (response, error) in
                guard error == nil else {
                    self.showError(error!.localizedDescription)
                    return
                }
                
                // extract info and data
                // response -> info: [[String : Any]], data: NSData
                guard let _ = response,
                    let infoData = response!["info"] as? Data,
                    let imageData = response!["data"] as? NSData else {
                    self.showError("No data returned")
                    return
                }
                var infoArray: [[String : Any]]?
                do {
                    infoArray = try JSONSerialization.jsonObject(with: infoData, options: []) as? [[String : Any]]
                } catch {
                    self.showError("Error in converting JSON: " + error.localizedDescription)
                    return
                }
                guard let _ = infoArray, infoArray!.count == 3 else {
                    self.showError("Info incomplete")
                    return
                }
                
                // extract data of each image
                var offset: Int = 0
                let _ = infoArray!.map {
                    guard let paintingId = $0["Painting-Id"] as? String,
                        let paintingDataLength = $0["Painting-Length"] as? Int,
                        let portraitDataLength = $0["Portrait-Length"] as? Int else {
                            self.showError("Info incomplete: \($0)")
                            return
                    }
                    
                    // extract painting
                    self.paintingsId.append(paintingId)
                    guard let painting = UIImage(data: Data(bytesNoCopy: UnsafeMutableRawPointer(mutating: imageData.bytes.advanced(by: offset)), count: paintingDataLength, deallocator: .none)) else {
                        self.showError("Cannot initialize painting")
                        return
                    }
                    self.paintings.append(painting)
                    offset += paintingDataLength
                    
                    // extract portrait
                    guard let portrait = UIImage(data: Data(bytesNoCopy: UnsafeMutableRawPointer(mutating: imageData.bytes.advanced(by: offset)), count: portraitDataLength, deallocator: .none)) else {
                        self.showError("Cannot initialize portrait")
                        return
                    }
                    self.portraits.append(portrait)
                    offset += portraitDataLength
                }
                
                self.paintingView.image = self.paintings[0]
                self.firstPortraitView.image = self.portraits[0]
                self.secondPortraitView.image = self.portraits[1]
                self.thirdPortraitView.image = self.portraits[2]
        }
    }
    
    func onProcessingAnimation() {
        DispatchQueue.main.async {
            self.transferIndicator.startAnimating()
            self.view.addSubview(self.blurEffectView)
            UIView.animate(withDuration: 0.3,
                           animations: {
                self.blurEffectView.effect = UIBlurEffect(style: .dark)
            }, completion: { finished in
                self.view.addSubview(self.transferIndicator)
            })
        }
    }
    
    func endProcessingAnimation(block: @escaping () -> Swift.Void) {
        DispatchQueue.main.async {
            self.transferIndicator.stopAnimating()
            self.transferIndicator.removeFromSuperview()
            block()
            UIView.animate(withDuration: 0.3,
                           animations: {
                self.blurEffectView.effect = nil
            }, completion: { finished in
                self.blurEffectView.removeFromSuperview()
            })
        }
    }
    
    func selectPainting(index: Int) {
        if selectedPainting != index {
            selectedPainting = index
            paintingView.image = paintings[index]
        }
    }

    @IBAction func tapFirstPortrait(_ sender: UITapGestureRecognizer) {
        selectPainting(index: 0)
    }
    
    @IBAction func tapSecondPortrait(_ sender: UITapGestureRecognizer) {
        selectPainting(index: 1)
    }
    
    @IBAction func tapThirdPortrait(_ sender: UITapGestureRecognizer) {
        selectPainting(index: 2)
    }
    
    @IBAction func pushStylized(_ sender: UIButton) {
        var willPush = true
        // do transfer only if stylized image not found in cache
        if stylizedImages.keys.contains(selectedPainting) == false {
            willPush = false
            let semaphore = DispatchSemaphore(value: 0)
            onProcessingAnimation()
            PEAServer.sharedInstance.sendData(
                Data(),
                headerFields: ["Photo-Timestamp": photoTimestamp,
                               "Style-Id": paintingsId[selectedPainting]],
                operation: .transfer,
                timeout: 300,
                responseHandler: {
                    (response, error) in
                    self.endProcessingAnimation {
                        guard error == nil else {
                            self.showError("Error in transfer: " + error!.localizedDescription)
                            return
                        }
                        guard let _ = response, let imageData = response!["data"] as? Data else {
                            self.showError("No data returned")
                            return
                        }
                        self.stylizedImages[self.selectedPainting] = UIImage(data: imageData)
                        self.performSegue(withIdentifier: "showStylizedImage", sender: self)
                        willPush = true
                        semaphore.signal()
                    }
            })
            semaphore.wait()
        }
        if willPush {
            performSegue(withIdentifier: "showStylizedImage", sender: self)
        }
    }
    
    override func prepare(for segue: UIStoryboardSegue, sender: Any?) {
        let svc = segue.destination as! StylizedViewController
        svc.originalPhoto = originalPhoto
        svc.stylizedImage = stylizedImages[selectedPainting]
    }

}
