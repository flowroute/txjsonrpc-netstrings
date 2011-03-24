from twisted.protocols.basic import NetstringReceiver
from twisted.internet import defer, reactor
import jsonrpclib
import simplejson
from twisted.python import log
import logging

class Protocol(NetstringReceiver):
    requests = {}
    id = 1
    MAX_LENGTH = 10 * 1024 * 1024 # 10MB

    def __init__(self, onConnect=None, onDisconnect=None):
        '''Overrid these instance variables to set callbacks on connect and disconnect'''
        self.onConnect = onConnect
        self.onDisconnect = onDisconnect
        
    def connectionMade(self):
        # if hasattr(self.transport, 'hostname'):
            # print '* Connection Made From "%s" *' % self.transport.hostname
        if self.onConnect:
            self.onConnect(self)
            
    def connectionLost(self, reason):
        # print '* Connection Lost *'
        if self.onDisconnect:
            self.onDisconnect(self)
            
    def stringReceived(self, string):
        message_id = None
        try:
            if len(string) > self.MAX_LENGTH:
                raise jsonrpclib.JsonRpcTooBigError()
            
            try:
                obj = jsonrpclib.load_string(string)
            except simplejson.decoder.JSONDecodeError:
                raise jsonrpclib.JsonRpcParseError()
            
            if not 'jsonrpc' in obj or obj['jsonrpc'] != '2.0':
                raise jsonrpclib.JsonRpcInvalidRequestError()
                
            if 'id' in obj:
                message_id = obj['id']
        
            if 'method' in obj:
                method, params, message_id = obj["method"], obj["params"], obj["id"]
                if hasattr(self, '_getFunction'):
                    f = self._getFunction(method)
                    d = f(params)
                    d.addCallback(self.responseReady, message_id)
                    d.addErrback(self.internalError, message_id)
                else:
                    logging.debug('** Client Got Request **')
                    logging.debug('%s - %s' % (method, params))
                    d = defer.Deferred()
                    d.addCallback(self.responseReady, message_id)
                    reactor.callLater(0, d.callback, 'ok')
            elif 'result' in obj:
                # Client got result back
                result, message_id = obj["result"], obj["id"]
                if message_id in self.requests:
                    self.requests[message_id].callback(result)
        except Exception as error:
            log.err()
            
            if not isinstance(error, jsonrpclib.JsonRpcClientError):
                self.errorReady(error, message_id)
          
        if 'error' in obj:
            # Client got error back
            code, message = obj["error"]['code'], obj["error"]['message']
            #logging.error('* Error (%s): %s' % (code, message))
            if message_id in self.requests:
                exception = jsonrpclib.JsonRpcClientError()
                exception.message = message
                exception.code = code
                self.requests[message_id].errback(exception)
            else:
                logging.debug('****** NO ERRBACK ******')
            
    def sendRequest(self, method, params={}):
        """This method is used as a client sending a request to a server"""
        req_id = self.id
        self.id += 1
        if self.id > 65000:
            self.id = 1
        string = jsonrpclib.dump_request(method, params, req_id)
        
        if len(string) > self.MAX_LENGTH:
            raise jsonrpclib.JsonRpcTooBigError()
        
        packet = '%d:%s,' % (len(string), string)
        self.transport.write(packet)
        d = defer.Deferred()
        self.requests[req_id] = d
        return d

    def responseReady(self, result, req_id):
        '''This is called when the server wants to respond to a request'''
        string = jsonrpclib.dump_response(result, req_id)
        
        if len(string) > self.MAX_LENGTH:
            self.errorReady(jsonrpclib.JsonRpcTooBigError(), req_id)
            return
        
        packet = '%d:%s,' % (len(string), string)
        # print 'Reply: %s' % string
        logging.debug('Reply: %s...' % string)
        self.transport.write(packet)

    def errorReady(self, error, req_id):
        string = jsonrpclib.dump_error(error, req_id)
        packet = '%d:%s,' % (len(string), string)
        logging.debug('Error Reply: %s' % string)
        self.transport.write(packet)
        
    def internalError(self, failure, message_id):
        failure_message = failure.getErrorMessage()
        logging.error(failure.getTraceback())
        error = jsonrpclib.JsonRpcInternalError()
        error.message = failure_message
        self.errorReady(error, message_id)
        
