//
//  PEAServer.swift
//  EmoArt
//
//  Created by Pujun Lun on 2/18/18.
//  Copyright © 2018 Pujun Lun. All rights reserved.
//

import Foundation

class PEAServer: NSObject, NetServiceDelegate, NetServiceBrowserDelegate {
    
    static let sharedInstance = PEAServer()
    
    enum Operation {
        case Store, Delete, Retrieve, Transfer
    }
    
    private static let kServerAuthentication = "PEAServer"
    private static let kServerType = "_demox._tcp."
    private static let kServerDomain = "local."
    private static let kLeanCloudUrl = "https://us-api.leancloud.cn/1.1/classes/Server"
    private static let kLeanCloudAppId = "OH4VbcK1AXEtklkhpkGCikPB-MdYXbMMI"
    private static let kLeanCloudAppKey = "0azk0HxCkcrtNGIKC5BMwxnr"
    private static let kLeanCloudObjectId = "5a40a4eee37d040044aa4733"
    private static let kClientAuthentication = "PortableEmotionAnalysis"
    private static let kServerOperationDict = [
        Operation.Store: "Store",
        Operation.Delete: "Delete",
        Operation.Retrieve: "Retrieve",
        Operation.Transfer: "Transfer",
        ]
    
    private var serviceBrowser: NetServiceBrowser?
    private var resolverList: [NetService]?
    private var serverAddress: String?
    
    override private init() {
        super.init()
        searchForServerInLAN()
    }
    
    private func log(_ message: String) {
        print("[PEAServer] " + message)
    }
    
    // MARK: - NSNetServiceBrowser
    
    private func searchForServerInLAN() {
        if serviceBrowser == nil {
            serviceBrowser = NetServiceBrowser.init()
        }
        if resolverList == nil {
            resolverList = []
        }
        serviceBrowser!.delegate = self
        serviceBrowser!.searchForServices(ofType: PEAServer.kServerType,
                                          inDomain: PEAServer.kServerDomain)
        log("Start browsing for services")
    }
    
    internal func netServiceBrowser(_ browser: NetServiceBrowser,
                                   didFind service: NetService,
                                   moreComing: Bool) {
        guard resolverList != nil else {
            log("Error: Resolver list does not exist when a service is found")
            return
        }
        resolverList!.append(service)
        service.delegate = self
        service.resolve(withTimeout: 10.0)
    }
    
    internal func netServiceBrowser(_ browser: NetServiceBrowser,
                                    didNotSearch errorDict: [String : NSNumber]) {
        stopBrowsing()
        log("Error in browsing for services: \(errorDict)")
    }
    
    private func stopBrowsing() {
        if serviceBrowser != nil {
            serviceBrowser!.stop()
            serviceBrowser!.delegate = nil
            serviceBrowser = nil
        }
        if resolverList != nil {
            for resolver in resolverList! {
                removeResolver(resolver, atEvent: "stop browsing")
            }
            resolverList = nil
        }
        log("Stop browsing")
    }
    
    // MARK: - NSNetServiceResolver
    
    internal func netServiceDidResolveAddress(_ sender: NetService) {
        removeResolver(sender, atEvent: "did resolve")
        guard sender.txtRecordData() != nil else {
            log("No TXT record in \(sender)")
            return
        }
        let txtRecord = NetService.dictionary(fromTXTRecord: sender.txtRecordData()!)
        guard let _ = txtRecord["Identity"] else {
            log("\(sender) has no authentication string")
            return
        }
        guard String.init(data: txtRecord["Identity"]!, encoding: String.Encoding.utf8) ==
            PEAServer.kServerAuthentication else {
            log("\(sender) is not authenticated")
            return
        }
        if let addressData = txtRecord["Address"] {
            serverAddress = String.init(data: addressData, encoding: String.Encoding.utf8)
            stopBrowsing()
            log("Use address: " + serverAddress!)
        } else {
            log("\(sender) does not contain server address")
            return
        }
    }
    
    internal func netService(_ sender: NetService, didNotResolve errorDict: [String : NSNumber]) {
        removeResolver(sender, atEvent: "did not resolve")
        log("Error in resolving service \(sender): \(errorDict)")
    }
    
    private func removeResolver(_ resolver: NetService, atEvent event: String) {
        resolver.stop()
        resolver.delegate = nil
        guard resolverList != nil else {
            log("Error: Resolver list does not exist when " + event)
            return
        }
        if let index = resolverList!.index(of: resolver) {
            resolverList!.remove(at: index)
        }
    }
    
}
