# -*- coding: utf-8 -*-

"""
    almdrlib.client
    ~~~~~~~~~~~~~~
    almdrlib OpenAPI v3 dynamic client builder 
"""

import os
import glob
import sys
import typing
import inspect
import logging
import pprint
import yaml
import json
import requests

class OpenAPIKeyWord:
    OPENAPI = "openapi"
    INFO = "info"

    SERVERS = "servers"
    URL = "url"
    SUMMARY = "summary"
    DESCRIPTION = "description"
    VARIABLES = "variables"
    REF = "$ref"
    REQUEST_BODY_NAME = "x-alertlogic-request-body-name"

    PATHS = "paths"
    OPERATION_ID = "operationId"
    PARAMETERS = "parameters"
    REQUEST_BODY = "requestBody"
    IN = "in"
    PATH = "path"
    QUERY = "query"
    HEADER = "header"
    COOKIE = "cookie"
    NAME = "name"
    REQUIRED = "required"
    SCHEMA = "schema"
    TYPE = "type"
    STRING = "string"
    OBJECT = "object"
    ALL_OF = "allOf"
    ONE_OF = "oneOf"
    ANY_OF = "anyOf"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    ARRAY = "array"
    NUMBER = "number"
    ENUM = "enum"
    SECURITY = "security"
    COMPONENTS = "components"
    SCHEMAS = "schemas"
    PROPERTIES = "properties"
    REQUIRED = "required"
    CONTENT = "content"
    DEFAULT = "default"

    SIMPLE_DATA_TYPES = [STRING, ARRAY, BOOLEAN, INTEGER, NUMBER]
    DATA_TYPES = [STRING, OBJECT, ARRAY, BOOLEAN, INTEGER, NUMBER]
    SUPPORTED_PAYLOAD_TYPES = [OBJECT, REF]
    INDIRECT_TYPES = [ALL_OF, ANY_OF, ONE_OF]

    # Alert Logic specific extensions
    X_REQUEST_BODY = "x-alertlogic-request-body"
    X_ALERTLOGIC_SCHEMA = "x-alertlogic-schema"

    X_ALERTLOGIC_SESSION_ENDPOINT = "x-alertlogic-session-endpoint"

logger = logging.getLogger(__name__)

class Server(object):
    _url: str
    description: str
    variables: typing.Dict[str, typing.Any]

    def __init__(self, service_name,
            url=None, description=None,
            variables=None,
            variables_spec=None,
            al_session_endpoint=False,
            session = None):
        self._service_name = service_name
        self.description = description
        self.variables = variables or variables_spec and dict((k, v.get(OpenAPIKeyWord.DEFAULT)) for (k, v) in variables_spec.items()) or None

        # Alert Logic extention to use Global Endpoint
        self._url = al_session_endpoint and session and session.get_url(self._service_name) or url
        logger.debug(f"Using '{self._url}' URL for '{self._service_name}' service.")

    @property
    def url(self):
        if self.variables:
            return self._url.format(**self.variables)
        else:
            return self._url

    def set_url(self, url):
        self._url = url

class RequestBody(object):
    def __init__(self, content_type, schema, required, session=None):
        self._content_type = content_type
        self._schema = schema
        self._required = required
        self._session = session

    def serialize(self, headers, kwargs):
        body = {}

        if not all(name in kwargs for name in self._required):
            raise ValueError(f"'{self._required}' are required'")
        for property_name in self._schema.get(OpenAPIKeyWord.PROPERTIES, {}).keys():
            if property_name not in kwargs: continue
            body[property_name] = kwargs.pop(property_name)

        headers['Content-Type'] = self._content_type 
        kwargs['data'] = json.dumps(body) 

    @property
    def schema(self):
        return self._schema 

class PathParameter(object):
    def __init__(self, spec = {}, session = None):
        # TODO: Rework PathParameter to work based on the saved spec
        self._in = spec[OpenAPIKeyWord.IN]
        self._name = spec[OpenAPIKeyWord.NAME]
        self._required = spec.get(OpenAPIKeyWord.REQUIRED, False)
        self._description = spec.get(OpenAPIKeyWord.DESCRIPTION, "")
        self._dataype = get_dict_value(spec, [OpenAPIKeyWord.SCHEMA, OpenAPIKeyWord.TYPE], OpenAPIKeyWord.STRING)
        self._spec = spec
        self._session = session
        self._default = None

    @property
    def name(self):
        return self._name

    @property
    def required(self):
        return self._required

    @property 
    def description(self):
        return self._description

    @property
    def datatype(self):
        return self._dataype

    @property
    def default(self):
        if self._default is None:
            self._default = self._session.get_default(self._name)
        return self._default

    @property
    def schema(self):
        result = {}
        for name, value in self._spec.items():
            if OpenAPIKeyWord.SCHEMA == name:
                result.update({k:v for k, v in value.items()})
            elif OpenAPIKeyWord.NAME == name:
                continue
            else:
                result[name] = value

        return result

    def serialize(self, path_params, query_params, headers, cookies, kwargs):
        if self._name not in kwargs and not self.default:
            if self._required:
                raise ValueError(f"'{self._name}' is required")
            return
        value = serialize_value(self._dataype, kwargs.pop(self._name, self.default))
        if self._in == OpenAPIKeyWord.PATH:
            path_params[self._name] = value
        elif self._in == OpenAPIKeyWord.QUERY:
            query_params[self._name] = value
        elif _in == OpenAPIKeyWord.HEADER:
            headers[self._name] = value
        elif _in == OpenAPIKeyWord.COOKIE:
            cookies[self._name] = value
       
        return True

class Operation(object):
    _internal_param_prefix = "_"
    _call: typing.Optional[typing.Callable] = None

    def __init__(self, path, ref, params, summary, description, method, spec, body, session=None, server=None):
        self._path = path
        self._ref = ref
        self._params = params
        self._summary = summary
        self._description = description
        self._method = method
        self._spec = spec
        self._body = body
        self._session = session
        self._server = server

    @property
    def spec(self):
        return self._spec

    @property
    def operation_id(self):
        return self._spec[OpenAPIKeyWord.OPERATION_ID]

    @property
    def method(self):
        return self._method

    @property
    def description(self):
        return self._description

    @property
    def path(self):
        return self._path

    @property
    def params(self):
        return self._params

    @property
    def body(self):
        return self._body

    def url(self, **kwargs):
        return self._server.url + self._path.format(**kwargs)

    def get_schema(self):
        params_schema = {}
        for param in self.params:
            params_schema.update({param.name: param.schema})
        if self.body:
            params_schema.update(self.body.schema.get(OpenAPIKeyWord.PROPERTIES, {}))

        return {
            OpenAPIKeyWord.OPERATION_ID: self.operation_id,
            OpenAPIKeyWord.DESCRIPTION: self.description,
            OpenAPIKeyWord.PARAMETERS: params_schema
        }

    def _get_body(self, headers, body, kwargs):
        body_spec = self._spec.get(OpenAPIKeyWord.REQUEST_BODY)
        if not body_spec:
            return

        name = body_spec.get(OpenAPIKeyWord.REQUEST_BODY_NAME, OpenAPIKeyWord.REQUEST_BODY)

        content = body_spec.get(OpenAPIKeyWord.CONTENT)
        if not content:
            raise ValueError(f"'{OpenAPIKeyWord.CONTENT}' is required for '{OpenAPIKeyWord.REQUEST_BODY}'")
        
        # for now get the first content type
        content_type, schema_spec = content.popitem()
        headers.update({"Content-Type": content_type})
        ref = schema_spec[OpenAPIKeyWord.SCHEMA].get(OpenAPIKeyWord.REF)
        if ref:
            parts = ref.split('/')
            t = getattr(sys.modules[__name__], parts[3])

    def _gen_call(self):
        def f(**kwargs):
            path_params = {}
            params = {}
            headers = {}
            cookies = {}
            body = {}
            
            # Set operation specific parameters
            for param in self._params:
                param.serialize(path_params, params, headers, cookies, kwargs)

            if self._body:
                self._body.serialize(headers, kwargs)

            # collect internal params
            for k in kwargs:
                if not k.startswith(self._internal_param_prefix):
                    continue
                kwargs[
                    k[len(self._internal_param_prefix) :]  # noqa: E203
                ] = kwargs.pop(k)
            
            kwargs.setdefault("params", {}).update(params)
            kwargs.setdefault("headers", {}).update(headers)
            kwargs.setdefault("cookies", {}).update(cookies)

            return self._session.request(
                self._method, self.url(**path_params), **kwargs
            )
            
        return f
            

    def __call__(self, *args, **kwargs):
        if not self._call:
            self._call = self._gen_call()
        return self._call(*args, **kwargs)

    def help(self):
        return pprint.pprint(self.spec, indent=2)

    def __repr__(self):
        return f"<{type(self).__name__}: [{self._method}] {self._path}>"

class Client(object):
    _operations: typing.Dict[str, typing.Any]
    _spec: typing.Dict[str, typing.Any]
    _models: typing.Dict[str, typing.Any]

    def __init__(self, name, version=None, session=None, residency=None, variables=None):
        self._name = name
        self._server = None
        self._session = session
        self._residency = residency
        self._operations = {}
        self._spec = {}
        self._models = {}
        self._info = {}
        self.load_service_spec(name, version, variables)

    def load_service_spec(self, service_name, version=None, variables=None):
        service_spec_file = ""
        service_api_dir = f"{os.path.dirname(__file__)}/apis/{service_name}"
        if not version:
            # Find the latest version of the service api spes
            version = 0
            for file in glob.glob(f"{service_api_dir}/{service_name}.v*.yaml"):
                file_name = os.path.basename(file)
                new_version = int(file_name.split(".")[1][1:])
                version = version > new_version and version or new_version
        else:
            version = version[:1] != "v" and version or version[1:]

        service_spec_file = f"{service_api_dir}/{service_name}.v{version}.yaml"
        logger.debug(f"Initializing client for '{self._name}'. Spec: '{service_spec_file}' Variables: '{variables}'")
        spec = load_spec_from_file(service_spec_file)
        self.load_spec(spec, variables)

    @property
    def server(self):
        return self._server

    def set_server(self, s):
        self._server = s
        self._initialize_operations()

    @property
    def info(self):
        return self._info

    @property
    def description(self):
        return self._info.get(OpenAPIKeyWord.DESCRIPTION, "")

    @property
    def operations(self):
        return self._operations

    @property
    def spec(self):
        return self._spec

    def load_spec(self, spec: typing.Dict, variables: typing.Dict):
        if not all(
            [
                i in spec
                for i in [
                    OpenAPIKeyWord.OPENAPI,
                    OpenAPIKeyWord.INFO,
                    OpenAPIKeyWord.PATHS,
                ]
            ]
        ):
            raise ValueError("Invaliad openapi document")

        self._spec = spec.copy()
        _spec = spec.copy()
        
        self._info = _spec.pop(OpenAPIKeyWord.INFO)

        servers = _spec.pop(OpenAPIKeyWord.SERVERS, [])
        for key in _spec:
            rkey = key.replace("-", "_")
            self.__setattr__(rkey, _spec[key])

        self.servers = [
            Server(
                service_name=self._name,
                url=s.get(OpenAPIKeyWord.URL),
                description=s.get(OpenAPIKeyWord.DESCRIPTION),
                variables=variables,
                variables_spec=s.get(OpenAPIKeyWord.VARIABLES),
                al_session_endpoint=s.get(OpenAPIKeyWord.X_ALERTLOGIC_SESSION_ENDPOINT, False),
                session=self._session
            )
            for s in servers
        ]

        if not self._server and self.servers:
            self._server = self.servers[0]

        self._initialize_operations()
    
    def _initialize_operations(self):
        self._operations = {}
        for path, path_spec in self.paths.items():
            ref = path_spec.pop(OpenAPIKeyWord.REF, "") #TODO: Add ref handler

            params = [
                PathParameter(
                    spec = param_spec,
                    session = self._session
                )
                for param_spec in path_spec.pop(OpenAPIKeyWord.PARAMETERS, [])
            ]

            for method, op_spec in path_spec.items():
                operation_id = op_spec.get(OpenAPIKeyWord.OPERATION_ID)
                summary = op_spec.pop(OpenAPIKeyWord.SUMMARY, "")
                description = op_spec.pop(OpenAPIKeyWord.DESCRIPTION, "")

                if not operation_id:
                    logging.warn(
                        f"'{OpenAPIKeyWord.OPERATION_ID}' not found in: '[{method}] {path}'"
                    )
                    continue

                params.extend([
                    PathParameter(
                        spec = param_spec,
                        session = self._session
                    )
                    for param_spec in op_spec.get(OpenAPIKeyWord.PARAMETERS, [])
                ])

                body = self._initalize_request_body(op_spec.get(OpenAPIKeyWord.REQUEST_BODY, None))

                op_body = op_spec.pop(OpenAPIKeyWord.REQUEST_BODY, None)
                if operation_id not in self._operations:
                    self._operations[operation_id] = Operation(
                        path,
                        ref,
                        params,
                        summary,
                        description,
                        method,
                        op_spec,
                        body,
                        session = self._session,
                        server = self._server
                    )
                else:
                    v = self._operations[operation_id]
                    if type(v) is not list:
                        self._operations[operation_id] = [v]
                    self._operations[operation_id].append(
                        Operation(
                            path,
                            ref,
                            params,
                            summary,
                            description,
                            method,
                            op_spec,
                            body,
                            session = self._session,
                            server = self._server
                        )
                    )

    def _initalize_request_body(self, body_spec = None):
        if not body_spec: return None 
        
        content = body_spec.pop(OpenAPIKeyWord.CONTENT, {})
        content_type, schema_spec = content.popitem()
        
        schema = schema_spec.pop(OpenAPIKeyWord.SCHEMA)
        al_schema = schema.pop(OpenAPIKeyWord.X_ALERTLOGIC_SCHEMA, {})

        body_schema = self._get_object_schema(
                schema, 
                property_name=al_schema.get(OpenAPIKeyWord.NAME))

        required_properties = schema.get(OpenAPIKeyWord.REQUIRED, [])

        return RequestBody(content_type, body_schema, required_properties, session=self._session)

    def _get_object_schema(self, schema, property_name=None):
        '''
            Get Object's schema. If ref is present, resolve it.
        '''
        if schema is None:
            return None 

        ref = schema.get(OpenAPIKeyWord.REF)
        if ref:
            model = self._get_model_reference(ref)
            if property_name is None:
                return self._get_object_schema(model)
                
            return {
                        OpenAPIKeyWord.PROPERTIES: {
                            property_name: self._get_object_schema(model)
                    }
                }
        elif schema.get(OpenAPIKeyWord.TYPE) != OpenAPIKeyWord.OBJECT:
            raise ValueError(f"'{schema}' is unsupported.")

        result = {}
        required = []
        for schema_key, schema_value in schema.items():
            if schema_key == OpenAPIKeyWord.PROPERTIES:
                properties = {}
                for name, value in schema_value.items():
                    datatype = value.get(OpenAPIKeyWord.TYPE)
                    if datatype in OpenAPIKeyWord.DATA_TYPES:
                        properties[name] = value
                    elif datatype == OpenAPIKeyWord.OBJECT:
                        properties[name] = self._get_object_schema(value)
                    elif OpenAPIKeyWord.REF in value:
                        properties[name] = self._get_object_schema(value)
                    else:
                        # This is either oneOf, allOf or anyOf.
                        indirect_type = next(iter(value))
                        if not indirect_type in OpenAPIKeyWord.INDIRECT_TYPES:
                            raise ValueError(f"'{schema}' is unsupported.")

                        properties[name] = {
                                OpenAPIKeyWord.TYPE: indirect_type,
                                OpenAPIKeyWord.DESCRIPTION: value.get(OpenAPIKeyWord.DESCRIPTION, ""),
                                indirect_type: [
                                    self._get_object_schema(v)
                                    for v in value[indirect_type]
                                ]
                            }
                    result[schema_key] = properties
            else:
                if schema_key == OpenAPIKeyWord.REQUIRED:
                    required = schema_value
                result[schema_key] = schema_value

        #
        # Mark required properties
        #
        for property_name in required:
            result[OpenAPIKeyWord.PROPERTIES][property_name][OpenAPIKeyWord.REQUIRED] = True
        return result 

    def _get_model_reference(self, ref):
        # Get model object definitions
        if ref and ref[:2] == '#/':
            return get_dict_value(self._spec, ref[2:].split('/'))

        # TODO: Handle External File References
        return None


    def __getattr__(self, op_name):
        if op_name in self._operations:
            return self._operations[op_name]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{op_name}'"
        )

def load_spec_from_file(file_path):
    with open(file_path) as f:
        s = f.read()
    return yaml.load(s, Loader=yaml.SafeLoader)

def get_dict_value(dict, list, default=None):
    length = len(list)
    try:
        for depth, key in enumerate(list):
            if depth == length - 1:
                output = dict[key]
                return output
            dict = dict[key]
    except (KeyError, TypeError):
        return default
    return default

def serialize_value(datatype, value):
    if OpenAPIKeyWord.STRING == datatype:
        return value
    elif OpenAPIKeyWord.BOOLEAN == datatype:
        return value and "true" or "false"
    else:
        return str(value)
