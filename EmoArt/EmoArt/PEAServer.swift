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
    
    enum Operation: String {
        case store = "Store"
        case delete = "Delete"
        case retrieve = "Retrieve"
        case transfer = "Transfer"
    }
    
    static let kServerAuthentication = "PEAServer"
    static let kServerType = "_demox._tcp."
    static let kServerDomain = "local."
    static let kLeanCloudUrl = "https://us-api.leancloud.cn/1.1/classes/Server"
    static let kLeanCloudAppId = "OH4VbcK1AXEtklkhpkGCikPB-MdYXbMMI"
    static let kLeanCloudAppKey = "0azk0HxCkcrtNGIKC5BMwxnr"
    static let kLeanCloudObjectId = "5a40a4eee37d040044aa4733"
    static let kClientAuthentication = "PortableEmotionAnalysis"
    
    var serviceBrowser = NetServiceBrowser()
    var resolverList = [NetService]()
    var serverAddress = ""
    var isAddressFound: Bool {
        return serverAddress.count != 0
    }
    
    override init() {
        super.init()
        searchForServerInLAN()
        queryServerAddress()
    }
    
    func log(_ message: String) {
        print("[PEAServer] " + message)
    }
    
    // MARK: - NSNetServiceBrowser
    
    func searchForServerInLAN() {
        serviceBrowser.delegate = self
        serviceBrowser.searchForServices(ofType: PEAServer.kServerType,
                                         inDomain: PEAServer.kServerDomain)
        log("Start browsing for services")
    }
    
    func netServiceBrowser(_ browser: NetServiceBrowser,
                           didFind service: NetService,
                           moreComing: Bool) {
        service.delegate = self
        service.resolve(withTimeout: 10.0)
        resolverList.append(service)
    }
    
    func netServiceBrowser(_ browser: NetServiceBrowser,
                           didNotSearch errorDict: [String : NSNumber]) {
        stopBrowsing()
        log("Error in browsing for services: \(errorDict)")
    }
    
    func stopBrowsing() {
        serviceBrowser.stop()
        serviceBrowser.delegate = nil
        let _ = resolverList.map { removeResolver($0, atEvent: "stop browsing") }
        resolverList.removeAll()
        log("Stop browsing")
    }
    
    // MARK: - NSNetServiceResolver
    
    func netServiceDidResolveAddress(_ sender: NetService) {
        removeResolver(sender, atEvent: "did resolve")
        
        // check TXT record
        guard let txtData = sender.txtRecordData() else {
            log("No TXT record in \(sender)")
            return
        }
        let txtRecord = NetService.dictionary(fromTXTRecord: txtData)
        
        // check identity
        guard let idData = txtRecord["Identity"] else {
            log("\(sender) has no authentication string")
            return
        }
        guard String(data: idData, encoding: .utf8) == PEAServer.kServerAuthentication else {
            log("\(sender) is not authenticated")
            return
        }
        
        // extract server address
        guard let addressData = txtRecord["Address"] else {
            log("\(sender) does not contain server address")
            return
        }
        guard let address = String(data: addressData, encoding: .utf8) else {
            log("Cannot decode data in \(sender)")
            return
        }
        // use address and stop browsing
        guard self.isAddressFound == false else {
            self.log("Server address already exists, discard address found in LAN")
            return
        }
        serverAddress = address
        stopBrowsing()
        log("Found server in LAN: " + serverAddress)
    }
    
    func netService(_ sender: NetService, didNotResolve errorDict: [String : NSNumber]) {
        removeResolver(sender, atEvent: "did not resolve")
        log("Error in resolving service \(sender): \(errorDict)")
    }
    
    func removeResolver(_ resolver: NetService, atEvent event: String) {
        resolver.stop()
        resolver.delegate = nil
        if let index = resolverList.index(of: resolver) {
            resolverList.remove(at: index)
        }
    }
    
    // MARK: - HTTP requests
    
    func setHeaderFields(_ headerFields: [String : String]?, for request: inout URLRequest) {
        let _ = headerFields?.map { request.setValue($1, forHTTPHeaderField: $0) }
    }
    
    func queryServerAddress() {
        // setup request
        var request = URLRequest(url: URL(string: PEAServer.kLeanCloudUrl)!,
                                 cachePolicy: .reloadIgnoringCacheData,
                                 timeoutInterval: 10.0)
        request.httpMethod = "GET"
        setHeaderFields(["X-LC-Id": PEAServer.kLeanCloudAppId,
                         "X-LC-Key": PEAServer.kLeanCloudAppKey,
                         "Content-Type": "application/json"],
                        for: &request)
        
        // start task
        let task = URLSession(configuration: .default).dataTask(with: request) {
            (returnedData, response, error) in
            guard error == nil else {
                self.log("Error in requesting server address: " + error!.localizedDescription)
                return
            }
            
            // extract server address
            // data -> info: [String : Any]
            guard let data = returnedData else {
                self.log("Error: No data returned when querying for server address")
                return
            }
            var info: [String : Any]?
            do {
                info = try JSONSerialization.jsonObject(with: data, options: []) as? Dictionary
            } catch {
                self.log("Error in converting JSON after query: " + error.localizedDescription)
                return
            }
            // info["results"] -> results: [[String : String]]
            guard let results = info!["results"] as? [[String : String]], results.count > 0 else {
                self.log("Error: Response of query contains no result")
                return
            }
            // results[0]["address"] -> address: String
            guard let address = results[0]["address"] else {
                self.log("Error: Response of query contains no address")
                return
            }
            // use address and stop browsing
            guard self.isAddressFound == false else {
                self.log("Server address already exists, discard address retrieved through internet")
                return
            }
            self.serverAddress = address
            self.log("Found server through internet: " + address)
            self.stopBrowsing()
        }
        task.resume()
    }
    
    public func sendData(_ data: Data,
                         headerFields: [String : String]?,
                         operation: Operation,
                         timeout: TimeInterval,
                         responseHandler: @escaping ([String : Any]?, EMAError?) -> Swift.Void) {
        func didFail(reason: String) {
            responseHandler(nil, EMAError(domain: .sendingData, reason: reason))
        }
        
        guard isAddressFound == true else {
            didFail(reason: "No server address found")
            return
        }
        
        // setup request
        var request = URLRequest(url: URL(string: serverAddress)!,
                                 cachePolicy: .reloadIgnoringCacheData,
                                 timeoutInterval: timeout)
        
        switch operation {
        case .delete:
            request.httpMethod = "DELETE"
        default:
            request.httpMethod = "POST"
        }
        
        setHeaderFields(headerFields, for: &request)
        setHeaderFields(["Operation": operation.rawValue,
                         "Authentication": PEAServer.kClientAuthentication,
                         "Content-Length": "\(data.count)"],
                        for: &request)
        
        // start task
        let task = URLSession(configuration: .default).uploadTask(with: request, from: data) {
                (returnedData, response, error) in
                guard error == nil else {
                    didFail(reason: error!.localizedDescription)
                    return
                }
                let httpResponse = response as! HTTPURLResponse
                guard httpResponse.statusCode != 200 else {
                    didFail(reason: "Code \(httpResponse.statusCode)")
                    return
                }
                
                // handle response
                switch operation {
                case .store, .delete:
                    var info: [String : Any]?
                    if let data = returnedData {
                        do {
                            info = try JSONSerialization.jsonObject(with: data, options: []) as? Dictionary
                        } catch {
                            self.log("Error in converting JSON after \(operation): \(error.localizedDescription)")
                            return
                        }
                    }
                    responseHandler(info, nil)
                case .retrieve:
                    guard let data = returnedData else {
                        didFail(reason: "No data returned after retrieving")
                        return
                    }
                    guard let info = httpResponse.allHeaderFields["Image-Info"] else {
                        didFail(reason: "No image info returned after retrieving")
                        return
                    }
                    responseHandler(["info": info,
                                     "data": data], nil)
                case .transfer:
                    guard let data = returnedData else {
                        didFail(reason: "No image data returned after transfer")
                        return
                    }
                    responseHandler(["data": data], nil)
                }
        }
        task.resume()
    }
    
}
