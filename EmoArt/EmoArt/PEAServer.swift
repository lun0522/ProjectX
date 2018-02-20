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
    
    private var serviceBrowser: NetServiceBrowser?
    private var resolverList: [NetService]?
    private var serverAddress: String?
    
    override init() {
        super.init()
        searchForServerInLAN()
        queryServerAddress()
    }
    
    private func log(_ message: String) {
        print("[PEAServer] " + message)
    }
    
    // MARK: - NSNetServiceBrowser
    
    private func searchForServerInLAN() {
        resolverList = []
        serviceBrowser = NetServiceBrowser.init()
        serviceBrowser!.delegate = self
        serviceBrowser!.searchForServices(ofType: PEAServer.kServerType,
                                          inDomain: PEAServer.kServerDomain)
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
            let _ = list.map { removeResolver($0, atEvent: "stop browsing") }
            resolverList = nil
        }
        log("Stop browsing")
    }
    
    // MARK: - NSNetServiceResolver
    
    internal func netServiceDidResolveAddress(_ sender: NetService) {
        removeResolver(sender, atEvent: "did resolve")
        
        // check TXT record
        guard let _ = sender.txtRecordData() else {
            log("No TXT record in \(sender)")
            return
        }
        let txtRecord = NetService.dictionary(fromTXTRecord: sender.txtRecordData()!)
        
        // check identity
        guard let _ = txtRecord["Identity"] else {
            log("\(sender) has no authentication string")
            return
        }
        guard String.init(data: txtRecord["Identity"]!, encoding: String.Encoding.utf8) ==
            PEAServer.kServerAuthentication else {
            log("\(sender) is not authenticated")
            return
        }
        
        // extract server address
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
        // setup request
        var request = URLRequest.init(url: URL.init(string: PEAServer.kLeanCloudUrl)!,
                                      cachePolicy: URLRequest.CachePolicy.reloadIgnoringCacheData,
                                      timeoutInterval: 10.0)
        request.httpMethod = "GET"
        let _ = [
            "X-LC-Id" : PEAServer.kLeanCloudAppId,
            "X-LC-Key" : PEAServer.kLeanCloudAppKey,
            "Content-Type" : "application/json",
        ].map { request.setValue($1, forHTTPHeaderField: $0) }
        
        // start task
        let task = URLSession.init(configuration: URLSessionConfiguration.default).dataTask(with: request) {
            (data, response, error) in
            guard error == nil else {
                self.log("Error in requesting server address: " + error!.localizedDescription)
                return
            }
            
            // extract server address
            // data -> info: [String : Any]
            guard let _ = data else {
                self.log("Error: No data returned when querying for server address")
                return
            }
            var info: [String : Any]?
            do {
                info = try JSONSerialization.jsonObject(with: data!, options: []) as? Dictionary
            } catch {
                self.log("Error in converting JSON after query: \(error.localizedDescription)")
                return
            }
            // info["results"] -> results: [[String : String]]
            let results = info!["results"] as? [[String : String]]
            guard let _ = results else {
                self.log("Error: Response of query contains no result")
                return
            }
            // results[0]["address"] -> address: String
            guard self.serverAddress == nil else {
                self.log("Server address already exists")
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
    
    public func sendData(_ data: Data,
                         headerFields: [String : String],
                         operation: Operation,
                         timeout: TimeInterval,
                         responseHandler: @escaping ([String : Any]?, Error?) -> Swift.Void) {
        guard let _ = serverAddress else {
            log("No server address found")
            return
        }
        
        // setup request
        var request = URLRequest.init(url: URL.init(string: serverAddress!)!,
                                      cachePolicy: URLRequest.CachePolicy.reloadIgnoringCacheData,
                                      timeoutInterval: timeout)
        switch operation {
        case .delete:
            request.httpMethod = "DELETE"
        default:
            request.httpMethod = "POST"
        }
        let _ = [
            "Operation" : operation.rawValue,
            "Authentication" : PEAServer.kClientAuthentication,
            "Content-Length" : "\(data.count)",
            ].map { request.setValue($1, forHTTPHeaderField: $0) }
        
        // start task
        let task = URLSession.init(configuration: URLSessionConfiguration.default)
            .uploadTask(with: request, from: data) {
                (data, response, error) in
                guard error == nil else {
                    responseHandler(nil, EMAError.sendDataError("Error in sending data: " + error!.localizedDescription))
                    return
                }
                let httpResponse = response as! HTTPURLResponse
                guard httpResponse.statusCode != 200 else {
                    responseHandler(nil, EMAError.sendDataError("Error in sending data. Code \(httpResponse.statusCode)"))
                    return
                }
                
                // handle response
                switch operation {
                case .store, .delete:
                    var info: [String : Any]?
                    if let _ = data {
                        do {
                            info = try JSONSerialization.jsonObject(with: data!, options: []) as? Dictionary
                        } catch {
                            self.log("Error in converting JSON after \(operation): \(error.localizedDescription)")
                            return
                        }
                    }
                    responseHandler(info, nil)
                case .retrieve:
                    guard let _ = data else {
                        responseHandler(nil, EMAError.sendDataError("Error: No data returned after retrieving"))
                        return
                    }
                    guard let _ = httpResponse.allHeaderFields["Image-Info"] else {
                        responseHandler(nil, EMAError.sendDataError("Error: No image info returned after retrieving"))
                        return
                    }
                    responseHandler(["info" : httpResponse.allHeaderFields["Image-Info"]!,
                                     "data" : data!], nil)
                case .transfer:
                    guard let _ = data else {
                        responseHandler(nil, EMAError.sendDataError("Error: No image data returned after transfer"))
                        return
                    }
                    responseHandler(["data" : data!], nil)
                }
        }
        task.resume()
    }
    
}
