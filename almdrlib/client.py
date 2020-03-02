# -*- coding: utf-8 -*-

"""
    almdrlib.client
    ~~~~~~~~~~~~~~~
    almdrlib OpenAPI v3 dynamic client builder
"""

import os
import glob
# import typing
# import inspect
import logging
import pprint
import yaml
import json
from almdrlib.exceptions import AlmdrlibValueError
from almdrlib.config import Config


class OpenAPIKeyWord:
    OPENAPI = "openapi"
    INFO = "info"
    TITLE = "title"

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
    BODY = "body"
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
    ENCODING = "encoding"
    EXPLODE = "explode"
    CONTENT_TYPE_PARAM = "content-type"
    CONTENT_TYPE_JSON = "application/json"
    CONTENT_TYPE_TEXT = "text/plain"
    CONTENT_TYPE_PYTHON_PARAM = "content_type"

    JSON_CONTENT_TYPES = ["application/json", "alertlogic.com/json"]

    SIMPLE_DATA_TYPES = [STRING, ARRAY, BOOLEAN, INTEGER, NUMBER]
    DATA_TYPES = [STRING, OBJECT, ARRAY, BOOLEAN, INTEGER, NUMBER]
    SUPPORTED_PAYLOAD_TYPES = [OBJECT, REF]
    INDIRECT_TYPES = [ALL_OF, ANY_OF, ONE_OF]

    # Alert Logic specific extensions
    X_ALERTLOGIC_SCHEMA = "x-alertlogic-schema"
    X_ALERTLOGIC_SESSION_ENDPOINT = "x-alertlogic-session-endpoint"
    X_ALERTLOGIC_DEFAULT_PAYLOAD_PARAM_NAME = "data"


logger = logging.getLogger(__name__)


class Server(object):

    def __init__(self, service_name,
                 url=None, description=None,
                 variables=None,
                 variables_spec=None,
                 al_session_endpoint=False,
                 session=None):
        self._service_name = service_name
        self.description = description
        if variables:
            self.variables = variables
        elif variables_spec:
            self.variables = dict((k, v.get(OpenAPIKeyWord.DEFAULT))
                                  for (k, v) in variables_spec.items())
        else:
            self.variables = None

        # Alert Logic extention to use Global Endpoint
        self._url = \
            al_session_endpoint and session and \
            session.get_url(self._service_name) or \
            url
        logger.debug(f"Using '{self._url}' URL " +
                     f"for '{self._service_name}' service.")

    @property
    def url(self):
        if self.variables:
            return self._url.format(**self.variables)
        else:
            return self._url

    def set_url(self, url):
        self._url = url


class RequestBodySimpleParameter(object):
    def __init__(self, name, schema, required, session):
        self._name = name
        self._schema = schema
        self._required = required
        self._session = session

    def serialize(self, value, header=None):
        return {'data': value}

    @property
    def name(self):
        return self._name

    @property
    def required(self):
        return self._required

    @property
    def schema(self):
        return self._schema


class RequestBodyObjectParameter(object):
    def __init__(self,
                 name,
                 schema,
                 encoding=None,
                 required=False,
                 session=None):
        self._name = name
        self._required = required
        self._schema = schema
        self._schema[OpenAPIKeyWord.REQUIRED] = required
        self._encoding = encoding
        self._session = session

    def serialize(self, value, headers=None):
        if self._encoding and self._encoding.get(OpenAPIKeyWord.EXPLODE):
            return value
        else:
            return {self._name: value}

    @property
    def name(self):
        return self._name

    @property
    def required(self):
        return self._required

    @property
    def schema(self):
        return self._schema


class RequestBody(object):
    def __init__(self, required=False, description=None, session=None):
        self._required = required
        self._description = description
        self._session = session
        self._content_types = {}
        self._content = {}
        self._default_content_type = None

    def add_content(self, content_type, schema, encoding):
        request_properties = {}
        datatype = schema[OpenAPIKeyWord.TYPE]
        if datatype == OpenAPIKeyWord.OBJECT:
            schema_properties = schema.get(OpenAPIKeyWord.PROPERTIES, [])
            required_properties = schema.get(OpenAPIKeyWord.REQUIRED, [])
            request_properties = {
                prop_name: RequestBodyObjectParameter(
                        name=prop_name,
                        schema=prop_schema,
                        encoding=encoding.get(prop_name),
                        required=prop_name in required_properties,
                        session=self._session
                    )
                for prop_name, prop_schema in schema_properties.items()
            }
        elif datatype in OpenAPIKeyWord.SIMPLE_DATA_TYPES:
            prop_name = schema.get(
                    OpenAPIKeyWord.NAME,
                    OpenAPIKeyWord.X_ALERTLOGIC_DEFAULT_PAYLOAD_PARAM_NAME)

            request_properties = {
                prop_name: RequestBodySimpleParameter(
                        name=prop_name,
                        schema=schema,
                        required=self._required,
                        session=self._session
                    )
            }
        else:
            raise AlmdrlibValueError(
                    f"'{datatype}' is invalid for requestBody property")

        self._content[content_type] = request_properties

    def serialize(self, headers, kwargs):
        #
        # Get content parameters.
        #
        if OpenAPIKeyWord.CONTENT_TYPE_PARAM in headers:
            content_type = headers[OpenAPIKeyWord.CONTENT_TYPE_PARAM]
            content = self._content[content_type]
        elif len(self._content) == 1:
            content_type, content = next(iter(self._content.items()))
            headers[OpenAPIKeyWord.CONTENT_TYPE_PARAM] = content_type
        else:
            raise AlmdrlibValueError(
                f"'{OpenAPIKeyWord.CONTENT_TYPE_PYTHON_PARAM}'" +
                "parameter is required.")

        # Get required properties list
        # and make sure all of them are present in kwargs
        required = self._get_required_properties(content)
        if not all(name in kwargs for name in required):
            raise AlmdrlibValueError(
                f"'{required}' parameters are required. " +
                f"'{kwargs}' were provided.")

        result = {}
        for name, property in content.items():
            if name in kwargs:
                result.update(property.serialize(value=kwargs.pop(name)))

        if content_type in OpenAPIKeyWord.JSON_CONTENT_TYPES:
            kwargs['data'] = json.dumps(result)
        else:
            kwargs['data'] = next(iter(result.values()))

    def get_schema(self):
        content_count = len(self._content)
        if content_count == 1:
            content = next(iter(self._content.values()))
            return {
                OpenAPIKeyWord.PROPERTIES: self._get_content_schema(content)
            }
        elif content_count:
            #
            # Content Type is a required property
            # when number of content types is greater than 0
            #
            return {
                OpenAPIKeyWord.CONTENT: {
                    content_type: {
                        OpenAPIKeyWord.PROPERTIES: self._get_content_schema(
                                                            content),
                    }
                    for content_type, content in self._content.items()
                }
            }
        else:
            return {}

    def _get_content_schema(self, content):
        return {name: property.schema for name, property in content.items()}

    def _get_required_properties(self, content):
        return [property.name
                for property in content.values() if property.required]


class PathParameter(object):
    def __init__(self, spec={}, session=None):
        # TODO: Rework PathParameter to work based on the saved spec
        self._in = spec[OpenAPIKeyWord.IN]
        self._init_name(spec[OpenAPIKeyWord.NAME])
        self._required = spec.get(OpenAPIKeyWord.REQUIRED, False)
        self._description = spec.get(OpenAPIKeyWord.DESCRIPTION, "")
        self._dataype = get_dict_value(
                            spec,
                            [OpenAPIKeyWord.SCHEMA, OpenAPIKeyWord.TYPE],
                            OpenAPIKeyWord.STRING)
        self._spec = spec
        self._session = session
        self._default = None

    def _init_name(self, name):
        self._name = name.replace('-', '_')
        self._schema_name = name

    @property
    def name(self):
        return self._name

    @property
    def schema_name(self):
        return self._schema_name

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
                result.update({k: v for k, v in value.items()})
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

        value = serialize_value(
                self._dataype,
                kwargs.pop(self._name, self.default))

        if self._in == OpenAPIKeyWord.PATH:
            path_params[self.schema_name] = value
        elif self._in == OpenAPIKeyWord.QUERY:
            query_params[self.schema_name] = value
        elif self._in == OpenAPIKeyWord.HEADER:
            headers[self.schema_name] = value
        elif self._in == OpenAPIKeyWord.COOKIE:
            cookies[self.schema_name] = value

        return True


class Operation(object):
    _internal_param_prefix = "_"
    _call = None

    def __init__(self,
                 path,
                 ref,
                 params,
                 summary,
                 description,
                 method, spec,
                 body,
                 session=None,
                 server=None):
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
        result = {
            OpenAPIKeyWord.OPERATION_ID: self.operation_id,
            OpenAPIKeyWord.DESCRIPTION: self.description
        }
        params_schema = {}
        for param in self.params:
            params_schema.update({param.name: param.schema})

        if self.body:
            schema = self.body.get_schema()
            if OpenAPIKeyWord.CONTENT in schema:
                result.update(schema)
            else:
                params_schema.update(schema.get(OpenAPIKeyWord.PROPERTIES))

        result.update({
            OpenAPIKeyWord.PARAMETERS: params_schema
        })
        return result

    def _gen_call(self):
        def f(**kwargs):
            path_params = {}
            params = {}
            headers = {}
            cookies = {}

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
    def __init__(self,
                 name,
                 version=None,
                 session=None,
                 residency=None,
                 variables=None):
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
        service_api_dir = f"{Config.get_api_dir()}/{service_name}"
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
        logger.debug(
            f"Initializing client for '{self._name}'" +
            f"Spec: '{service_spec_file}' Variables: '{variables}'")
        spec = load_spec_from_file(service_spec_file)
        self.load_spec(spec, variables)

    @property
    def name(self):
        return self._name

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

    def load_spec(self, spec, variables):
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
                al_session_endpoint=s.get(
                        OpenAPIKeyWord.X_ALERTLOGIC_SESSION_ENDPOINT,
                        False
                    ),
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
            # TODO: Add ref handler
            ref = path_spec.pop(OpenAPIKeyWord.REF, "")

            params = [
                PathParameter(
                    spec=param_spec,
                    session=self._session
                )
                for param_spec in path_spec.pop(OpenAPIKeyWord.PARAMETERS, [])
            ]

            for method, op_spec in path_spec.items():
                operation_id = op_spec.get(OpenAPIKeyWord.OPERATION_ID)
                summary = op_spec.pop(OpenAPIKeyWord.SUMMARY, "")
                description = op_spec.pop(OpenAPIKeyWord.DESCRIPTION, "")

                if not operation_id:
                    logging.warn(
                        f"'{OpenAPIKeyWord.OPERATION_ID}' not found in: \
                          '[{method}] {path}'"
                    )
                    continue

                params.extend([
                    PathParameter(
                        spec=param_spec,
                        session=self._session
                    )
                    for param_spec in op_spec.get(OpenAPIKeyWord.PARAMETERS,
                                                  [])
                ])

                body = self._initalize_request_body(
                        op_spec.pop(OpenAPIKeyWord.REQUEST_BODY, None))

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
                        session=self._session,
                        server=self._server
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
                            session=self._session,
                            server=self._server
                        )
                    )

    def _initalize_request_body(self, body_spec=None):
        if not body_spec:
            return None

        content = body_spec.pop(OpenAPIKeyWord.CONTENT, {})
        description = body_spec.pop(OpenAPIKeyWord.DESCRIPTION, None)
        required = body_spec.pop(OpenAPIKeyWord.REQUIRED, False)
        request_body = RequestBody(required=required,
                                   description=description,
                                   session=self._session)

        for content_type, content_schema in content.items():
            schema = content_schema.get(OpenAPIKeyWord.SCHEMA)
            al_schema = content_schema.get(OpenAPIKeyWord.X_ALERTLOGIC_SCHEMA)
            encoding = content_schema.pop(OpenAPIKeyWord.ENCODING, {})
            request_body.add_content(content_type,
                                     self._expand_schema(schema, al_schema),
                                     encoding)

        return request_body

    def _expand_schema(self, schema, al_schema=None):
        if not schema:
            return None

        ref = schema.get(OpenAPIKeyWord.REF)
        if ref:
            # Get Model schema
            return self._expand_schema(self._get_model_reference(ref),
                                       al_schema)

        datatype = schema.get(OpenAPIKeyWord.TYPE)
        if datatype not in OpenAPIKeyWord.DATA_TYPES:
            raise AlmdrlibValueError(f"Invalid {datatype} data type \
                                       specified for {self._name} API")

        if datatype in OpenAPIKeyWord.SIMPLE_DATA_TYPES:
            if al_schema:
                #
                # Add parameter name field to the schema
                #
                schema['name'] = al_schema.get(
                        OpenAPIKeyWord.NAME,
                        OpenAPIKeyWord.X_ALERTLOGIC_DEFAULT_PAYLOAD_PARAM_NAME
                        )
            return schema

        result = {}
        for key, value in schema.items():
            if key == OpenAPIKeyWord.PROPERTIES:
                # Process OpenAPI defined properties
                properties = {}
                for prop_name, prop_schema in value.items():
                    ref = prop_schema.get(OpenAPIKeyWord.REF)
                    if ref:
                        #
                        # Resolve model reference
                        #
                        properties[prop_name] = self._expand_schema(
                                self._get_model_reference(ref),
                                al_schema)
                        result[key] = properties
                        continue

                    datatype = prop_schema.get(OpenAPIKeyWord.TYPE)
                    if datatype in OpenAPIKeyWord.SIMPLE_DATA_TYPES:
                        properties[prop_name] = prop_schema
                    elif datatype == OpenAPIKeyWord.OBJECT:
                        properties[prop_name] = self._expand_schema(
                                                            prop_schema,
                                                            al_schema)
                    else:
                        alternate_type, alternate_schemas = next(
                                                    iter(prop_schema.items()))

                        if alternate_type in OpenAPIKeyWord.INDIRECT_TYPES:
                            properties[prop_name] = {
                                alternate_type: [
                                    self._expand_schema(alternate_schema,
                                                        al_schema)
                                    for alternate_schema in alternate_schemas
                                ]
                            }
                        else:
                            raise AlmdrlibValueError(
                                f"Invalid schema for '{self._name}' API's. \
                                  Property: '{prop_name}'. \
                                  Datatype: '{datatype}'")

                result[key] = properties
            else:
                # Add OpenAPI keys and values
                result[key] = value

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
