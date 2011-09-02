import json
from datetime import datetime
import decimal

class JsonRpcServerError(Exception):
    # -32099 to -32000 free for application-defined codes
    code = -32000
    message = 'Server error'
    
class JsonRpcInternalError(JsonRpcServerError):
    code = -32603
    message = 'Internal error'

class JsonRpcInvalidParamsError(JsonRpcServerError):
    code = -32602
    message = 'Invalid params'

class JsonRpcMethodNotFoundError(JsonRpcServerError):
    code = -32601
    message = 'Method not found'

class JsonRpcInvalidRequestError(JsonRpcServerError):
    code = -32600
    message = 'Invalid Request'
    
class JsonRpcTooBigError(JsonRpcInvalidRequestError):
    message = 'Message too big'

class JsonRpcParseError(JsonRpcServerError):
    code = -32700
    message = 'Parse error'
    
class JsonRpcClientError(JsonRpcServerError):
    code = -32000
    message = 'Server error'


def dump_request(method, params, req_id, encoder=json.JSONEncoder):
    obj = {"jsonrpc": "2.0", "method": method, "params": params, "id": req_id}
    return json.dumps(obj, cls=encoder)
    
def dump_response(result, req_id, encoder=json.JSONEncoder):
    obj = {"jsonrpc": "2.0", "result": result, "id": req_id}
    return json.dumps(obj, cls=encoder)
    
def dump_error(error, req_id, encoder=json.JSONEncoder):
    error.code = None if not hasattr(error, 'code') else error.code
    obj = {"jsonrpc": "2.0", "error": {"code":error.code, "message":error.message}, "id": req_id}
    return json.dumps(obj, cls=encoder)


