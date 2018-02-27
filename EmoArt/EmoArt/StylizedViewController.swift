//
//  StylizedViewController.swift
//  EmoArt
//
//  Created by Pujun Lun on 2/26/18.
//  Copyright © 2018 Pujun Lun. All rights reserved.
//

import UIKit

class StylizedViewController: UIViewController {
    
    var originalPhoto: UIImage!
    var stylizedImage: UIImage!

    @IBOutlet weak var imageView: UIImageView!
    
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor.black
        imageView.contentMode = .scaleAspectFit
        imageView.image = stylizedImage
        
    }

    @IBAction func longPressImage(_ sender: UILongPressGestureRecognizer) {
        imageView.image = sender.state == .began ? originalPhoto : stylizedImage
    }
    
    @IBAction func tapShare(_ sender: UIButton) {
        let alert = UIAlertController(title: nil, message: nil, preferredStyle: .actionSheet)
        alert.addAction(UIAlertAction(title: "Save to album", style: .default, handler: { action in
            UIImageWriteToSavedPhotosAlbum(self.stylizedImage, self, #selector(self.image(_:didFinishSavingWithError:contextInfo:)), nil)
        }))
        DispatchQueue.main.async {
            self.present(alert, animated: true, completion: nil)
        }
    }
    
    @objc func image(_ image: UIImage,
                     didFinishSavingWithError error: Error?,
                     contextInfo: UnsafeRawPointer) {
        let alert = UIAlertController(title: error == nil ? "Success!" : "Error",
                                      message: error == nil ? "Please view in the album" : error!.localizedDescription,
                                      preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "OK", style: .cancel, handler: nil))
        DispatchQueue.main.async {
            self.present(alert, animated: true, completion: nil)
        }
    }
    
}
