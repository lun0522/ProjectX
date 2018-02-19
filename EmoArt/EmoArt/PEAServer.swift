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
        
        case store, delete, retrieve, transfer
        
        private func toString() -> String {
            switch self {
            case .store:
                return "Store"
            case .delete:
                return "Delete"
            case .retrieve:
                return "Retrieve"
            case .transfer:
                return "Transfer"
            }
        }
        
    }
    
    private static let kServerAuthentication = "PEAServer"
    private static let kServerType = "_demox._tcp."
    private static let kServerDomain = "local."
    private static let kLeanCloudUrl = "https://us-api.leancloud.cn/1.1/classes/Server"
    private static let kLeanCloudAppId = "OH4VbcK1AXEtklkhpkGCikPB-MdYXbMMI"
    private static let kLeanCloudAppKey = "0azk0HxCkcrtNGIKC5BMwxnr"
    private static let kLeanCloudObjectId = "5a40a4eee37d040044aa4733"
    private static let kClientAuthentication = "PortableEmotionAnalysis"
    
    private var serviceBrowser: NetServiceBrowser?
    private var resolverList: [NetService]?
    private var serverAddress: String?
    
    override private init() {
        super.init()
        searchForServerInLAN()
        queryServerAddress()
    }
    
    private func log(_ message: String) {
        print("[PEAServer] " + message)
    }
    
    // MARK: - NSNetServiceBrowser
    
    private func searchForServerInLAN() {
        if resolverList == nil {
            resolverList = []
        }
        if serviceBrowser == nil {
            serviceBrowser = NetServiceBrowser.init()
            serviceBrowser!.delegate = self
            serviceBrowser!.searchForServices(ofType: PEAServer.kServerType,
                                              inDomain: PEAServer.kServerDomain)
        }
        log("Start browsing for services")
    }
    
    internal func netServiceBrowser(_ browser: NetServiceBrowser,
                                   didFind service: NetService,
                                   moreComing: Bool) {
        if var list = resolverList {
            service.delegate = self
            service.resolve(withTimeout: 10.0)
            list.append(service)
        } else {
            log("Error: Resolver list does not exist when a service is found")
        }
    }
    
    internal func netServiceBrowser(_ browser: NetServiceBrowser,
                                    didNotSearch errorDict: [String : NSNumber]) {
        stopBrowsing()
        log("Error in browsing for services: \(errorDict)")
    }
    
    private func stopBrowsing() {
        if let browser = serviceBrowser {
            browser.stop()
            browser.delegate = nil
            serviceBrowser = nil
        }
        if let list = resolverList {
            for resolver in list {
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
            log("Found server in LAN: " + serverAddress!)
        } else {
            log("\(sender) does not contain server address")
        }
    }
    
    internal func netService(_ sender: NetService, didNotResolve errorDict: [String : NSNumber]) {
        removeResolver(sender, atEvent: "did not resolve")
        log("Error in resolving service \(sender): \(errorDict)")
    }
    
    private func removeResolver(_ resolver: NetService, atEvent event: String) {
        resolver.stop()
        resolver.delegate = nil
        if var list = resolverList {
            if let index = list.index(of: resolver) {
                list.remove(at: index)
            }
        } else {
            log("Error: Resolver list does not exist when " + event)
        }
    }
    
    // MARK: - HTTP requests
    
    private func queryServerAddress() {
        var request = URLRequest.init(url: URL.init(string: PEAServer.kLeanCloudUrl)!,
                                      cachePolicy: NSURLRequest.CachePolicy.reloadIgnoringCacheData,
                                      timeoutInterval: 10.0)
        request.httpMethod = "GET"
        for (value, field) in [
            "X-LC-Id" : PEAServer.kLeanCloudAppId,
            "X-LC-Key" : PEAServer.kLeanCloudAppKey,
            "Content-Type" : "application/json",
            ] {
            request.setValue(value, forHTTPHeaderField: field)
        }
        let session = URLSession.init(configuration: URLSessionConfiguration.default)
        let task = session.dataTask(with: request) {
            (data, response, error) in
            guard error == nil else {
                self.log("Error in requesting server address: " + error!.localizedDescription)
                return
            }
            guard let _ = data else {
                self.log("Error: No data returned when querying for server address")
                return
            }
            var info: [String : Any]?
            do {
                info = try JSONSerialization.jsonObject(with: data!, options: []) as? [String : Any]
            } catch {
                self.log("Error in converting JSON: \(error.localizedDescription)")
            }
            guard let _ = info else {
                self.log("Error: Response of query cannot be converted to dictionary")
                return
            }
            let results = info!["results"] as? [[String : String]]
            guard let _ = results else {
                self.log("Error: Response of query contains no result")
                return
            }
            guard self.serverAddress == nil else {
                return
            }
            if let address = results![0]["address"] {
                self.serverAddress = address
                self.log("Found server through internet: " + address)
                self.stopBrowsing()
            } else {
                self.log("Error: Response of query contains no address")
            }
        }
        task.resume()
    }
    
}
