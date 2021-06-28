# -*- coding: utf-8 -*-

"""
    almdrlib.client
    ~~~~~~~~~~~~~~~
    almdrlib OpenAPI v3 dynamic client builder
"""

import abc
# import typing
# import inspect
import logging
import json
import jsonschema
from jsonschema.validators import validator_for
import alsdkdefs

from almdrlib.exceptions import AlmdrlibValueError
from almdrlib.config import Config

from alsdkdefs import OpenAPIKeyWord

logger = logging.getLogger(__name__)


class Server(object):
    def __init__(self, service_name, spec,
                 session=None, variables=None):
        self._service_name = service_name
        self._spec = spec
        self._session = session
        self._url = spec.get(OpenAPIKeyWord.URL)
        self._description = spec.get(OpenAPIKeyWord.DESCRIPTION)

        if variables:
            self.variables = variables
        elif OpenAPIKeyWord.VARIABLES in spec:
            self.variables = dict(
                    (k, v.get(OpenAPIKeyWord.DEFAULT))
                    for k, v in spec[OpenAPIKeyWord.VARIABLES].items())
        else:
            self.variables = variables

        if spec.get(OpenAPIKeyWord.X_ALERTLOGIC_SESSION_ENDPOINT) and \
                self._session:
            self.update_url()

        logger.debug(f"Server initialized using '{self._url}' URL " +
                     f"for '{self._service_name}' service.")

    def update_url(self, account_id=None):
        self._url = self._session.get_url(self._service_name, account_id)

    @property
    def url(self):
        if self.variables:
            return self._url.format(**self.variables)
        else:
            return self._url

    @property
    def spec(self):
        return self._spec

    def set_url(self, url):
        self._url = url


class OperationResponse(object):
    _response_schema = {}

    def __init__(self, schema, session=None):
        for r_code, r_schema in schema.items():
            if r_code[0] == '2':
                self._add_response(r_schema.pop(OpenAPIKeyWord.CONTENT, None))

        self._schema = schema

    def _add_response(self, content):
        if not content:
            return

        # While there could be more than one content type,
        # We support only the first content type.
        content_type, content_type_schema = next(iter(content.items()))
        if content_type not in OpenAPIKeyWord.JSON_CONTENT_TYPES:
            logger.warn(
                    f"{content_type} content type is unsupported." +
                    f"Only {OpenAPIKeyWord.JSON_CONTENT_TYPES} " +
                    "content types are supported"
            )
        if not content_type_schema:
            return

        self._response_schema = content_type_schema.get(OpenAPIKeyWord.SCHEMA)

    @property
    def schema(self):
        return self._response_schema

    @property
    def exceptions(self):
        return {}


class RequestBodyParameter(object):
    def __init__(self, name, schema, required=False, session=None):
        self._name = name
        self._schema = schema
        self._required = required
        self._session = session

        validator_cls = validator_for(schema)
        validator_cls.check_schema(schema)
        self._validator = validator_cls(schema)

    @abc.abstractmethod
    def serialize(self, value, header=[]):
        """ Derived classes handle serialization """
        return

    def validate(self, data):
        try:
            self._validator.validate(data)
        except jsonschema.exceptions.ValidationError as e:
            raise AlmdrlibValueError(
                    f"{e.message}. Schema: {json.dumps(e.schema)}")

    @property
    def name(self):
        return self._name

    @property
    def required(self):
        return self._required

    @property
    def schema(self):
        return {
            self._name: self._schema
        }


class RequestBodySchemaParameter(RequestBodyParameter):
    def __init__(self, name, schema, required=False, session=None):
        super().__init__(name, schema, required, session)

    def serialize(self, kwargs, header=[]):
        data = kwargs.pop(self.name, {})
        self.validate(data)
        kwargs['data'] = json.dumps(data)


class RequestBodySimpleParameter(RequestBodyParameter):
    def __init__(self, name, schema, required=False, session=None):
        super().__init__(name, schema, required, session)
        self._format = schema.get(OpenAPIKeyWord.FORMAT)

    def serialize(self, kwargs, header=None):
        data = kwargs.pop(self.name, "")
        if self._format == 'binary':
            kwargs['data'] = data.encode()
        else:
            kwargs['data'] = data


class RequestBodyObjectParameter(RequestBodyParameter):
    def __init__(self,
                 name,
                 schema,
                 al_schema={},
                 required=False,
                 session=None):
        super().__init__(
                name,
                _normalize_schema(name,
                                  schema,
                                  required),
                required,
                session
            )

        self._encoding = al_schema.pop(OpenAPIKeyWord.ENCODING, None)
        self._explode = \
            self._encoding and \
            self._encoding.get(OpenAPIKeyWord.EXPLODE, False)

        #
        # Get request body object properties
        #
        self._properties = self._schema.get(OpenAPIKeyWord.PROPERTIES, None)
        self._required_properties = self._schema.get(
                                            OpenAPIKeyWord.REQUIRED, [])

        if self._properties:
            for name in self._required_properties:
                self._properties[name].update(
                        {'x-alertlogic-required': True})

        logger.debug(
                "Initialized body parameter. "
                f"Name: {self.name}. "
                "Properties: "
                f"{self._properties and self._properties.keys() or self.name}"
                "Required Properties: "
                f"{self._required_properties}"
            )

    def serialize(self, kwargs, headers=None):
        if not all(name in kwargs for name in self._required_properties):
            raise AlmdrlibValueError(
                f"'{self._required_properties}' parameters are required. " +
                f"'{kwargs}' were provided.")

        result = {
                    k: kwargs.pop(k)
                    for k in self._properties.keys() if k in kwargs
                }

        if self.required and not bool(result):
            raise AlmdrlibValueError(
                "At least one the " +
                f"{self._properties.keys()} parameters must be specified."
            )

        # Validate provided payload against the schema
        self.validate(result)

        if self._explode:
            kwargs['data'] = json.dumps(result.pop(self.name))
        else:
            kwargs['data'] = json.dumps(result)

    @property
    def schema(self):
        return self._properties


class RequestBody(object):
    def __init__(self, required=False, description=None, session=None):
        self._parameters = {}
        self._required = required
        self._description = description
        self._session = session
        self._content_types = {}
        self._content = {}
        self._default_content_type = None

    def add_content(self, content_type, schema, al_schema):
        if not schema:
            return

        datatype = schema.get(OpenAPIKeyWord.TYPE)
        name = al_schema.get(OpenAPIKeyWord.NAME, OpenAPIKeyWord.DATA)
        if datatype == OpenAPIKeyWord.OBJECT:
            parameter = RequestBodyObjectParameter(
                            name=name,
                            schema=schema,
                            al_schema=al_schema,
                            required=self._required,
                            session=self._session
                        )
        elif datatype in OpenAPIKeyWord.SIMPLE_DATA_TYPES:
            parameter = RequestBodySimpleParameter(
                            name=name,
                            schema=schema,
                            required=self._required,
                            session=self._session
                        )
        else:
            parameter = RequestBodySchemaParameter(
                            name=name,
                            schema=schema,
                            required=self._required,
                            session=self._session
                        )

        self._content[content_type] = parameter

        if name in self._parameters:
            self._parameters[name].update({content_type: parameter.schema})
        else:
            self._parameters[name] = {content_type: parameter.schema}

    def serialize(self, headers, kwargs):
        #
        # Get content parameters.
        #
        if OpenAPIKeyWord.CONTENT_TYPE_PARAM in headers:
            content_type = headers[OpenAPIKeyWord.CONTENT_TYPE_PARAM]
            payloadBodyParam = self._content[content_type]
        elif len(self._content) == 1:
            content_type, payloadBodyParam = next(iter(self._content.items()))
            headers[OpenAPIKeyWord.CONTENT_TYPE_PARAM] = content_type
        else:
            raise AlmdrlibValueError(
                f"'{OpenAPIKeyWord.CONTENT_TYPE_PYTHON_PARAM}'" +
                "parameter is required.")

        payloadBodyParam.serialize(kwargs, headers)

    def get_schema(self):
        if len(self._content) == 1:
            payloadBodyParam = next(iter(self._content.values()))
            return {OpenAPIKeyWord.PROPERTIES: payloadBodyParam.schema}

        # Request body supports has multiple content types
        properties = dict()
        for name, schema in self._parameters.items():
            properties[name] = {
                    'content': {
                        content_type: parameter.get(name)
                        for content_type, parameter in schema.items()
                    }
                }

        return {
                OpenAPIKeyWord.PROPERTIES: properties,
                'x-alertlogic-payload-content': self._get_content_schema()
            }

    def _get_content_schema(self):
        return {
            name: list(property.schema.keys())
            for name, property in self._content.items()
        }

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
        self._datatype = get_dict_value(
                            spec,
                            [OpenAPIKeyWord.SCHEMA, OpenAPIKeyWord.TYPE],
                            OpenAPIKeyWord.STRING)
        self._style = spec.get(OpenAPIKeyWord.STYLE,
                               self.default_style(self._in))
        self._explode = spec.get(OpenAPIKeyWord.EXPLODE,
                                 self.default_explode(self._style))
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
        return self._datatype

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

        raw_value = kwargs.pop(self._name, self.default)

        value = serialize_value(
                self._datatype,
                raw_value)

        if self._in == OpenAPIKeyWord.PATH:
            path_params[self.schema_name] = value
        elif self._in == OpenAPIKeyWord.QUERY:
            new_query_params = self.serialize_query_parameter(self._style,
                                                              self._explode,
                                                              self._name,
                                                              self._datatype,
                                                              raw_value)
            query_params.update(new_query_params)
        elif self._in == OpenAPIKeyWord.HEADER:
            headers[self.schema_name] = value
        elif self._in == OpenAPIKeyWord.COOKIE:
            cookies[self.schema_name] = value

        return True

    @classmethod
    def default_style(cls, parameter_in):
        if parameter_in == OpenAPIKeyWord.QUERY:
            return OpenAPIKeyWord.PARAMETER_STYLE_FORM
        elif parameter_in == OpenAPIKeyWord.PATH:
            return OpenAPIKeyWord.PARAMETER_STYLE_SIMPLE
        elif parameter_in == OpenAPIKeyWord.HEADER:
            return OpenAPIKeyWord.PARAMETER_STYLE_SIMPLE
        elif parameter_in == OpenAPIKeyWord.COOKIE:
            return OpenAPIKeyWord.PARAMETER_STYLE_FORM
        else:
            return OpenAPIKeyWord.PARAMETER_STYLE_SIMPLE

    @classmethod
    def default_explode(cls, style):
        if style == OpenAPIKeyWord.PARAMETER_STYLE_FORM:
            return True
        else:
            return False

    @classmethod
    def serialize_query_parameter(cls, style, explode, name, datatype, value):
        # Implements partial query parameter serialization using rules from:
        # https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.3.md#style-examples
        # https://swagger.io/docs/specification/serialization/#query
        # TODO: Serialize deepObject style
        valid_styles = [OpenAPIKeyWord.PARAMETER_STYLE_FORM,
                        OpenAPIKeyWord.PARAMETER_STYLE_SPACE_DELIMITED,
                        OpenAPIKeyWord.PARAMETER_STYLE_PIPE_DELIMITED]
        if style not in valid_styles:
            raise ValueError(f"{name} query parameter has invalid style: "
                             f"{style}")
            return

        if (datatype == OpenAPIKeyWord.OBJECT and
                style == OpenAPIKeyWord.PARAMETER_STYLE_FORM):
            if explode:
                return value
            else:
                serialized_pairs = [f'{a},{b}' for (a, b) in value.items()]
                return {name: ",".join(serialized_pairs)}
        elif datatype == OpenAPIKeyWord.ARRAY:
            if explode:
                return {name: value}
            else:
                if style == OpenAPIKeyWord.PARAMETER_STYLE_SPACE_DELIMITED:
                    delimiter = " "
                elif style == OpenAPIKeyWord.PARAMETER_STYLE_PIPE_DELIMITED:
                    delimiter = "|"
                else:
                    # Implicitly 'form' style
                    delimiter = ","
                return {name: delimiter.join(value)}
        elif datatype == OpenAPIKeyWord.BOOLEAN:
            return {name: str(value).lower()}
        else:
            return {name: value}


class Operation(object):
    _internal_param_prefix = "_"
    _call = None

    def __init__(self,
                 path,
                 params,
                 summary,
                 description,
                 method, spec,
                 body,
                 response,
                 session=None,
                 server=None):
        self._path = path
        self._params = params
        self._summary = summary
        self._description = description
        self._method = method
        self._spec = spec
        self._body = body
        self._response = response
        self._session = session
        self._server = server
        self._operation_id = self._spec[OpenAPIKeyWord.OPERATION_ID]

        logger.debug(f"Initilized {self._operation_id} operation.")

    @property
    def spec(self):
        return self._spec

    @property
    def operation_id(self):
        return self._operation_id

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
            params_schema.update(schema.get(OpenAPIKeyWord.PROPERTIES))
            payload_content = schema.get('x-alertlogic-payload-content')
            if payload_content:
                params_schema['content_type'].update(
                        {'x-alertlogic-payload-content': payload_content}
                )

            # if OpenAPIKeyWord.CONTENT in schema:
                # result.update(schema)
            # if 'x-alertlogic-payload' in schema:
            #     params_schema['content_type'].update(schema)
            # else:
            #     params_schema.update(schema.get(OpenAPIKeyWord.PROPERTIES))

        result.update({
            OpenAPIKeyWord.PARAMETERS: dict(sorted(params_schema.items()))
        })

        result.update({
            OpenAPIKeyWord.RESPONSE: self._response.schema,
            OpenAPIKeyWord.EXCEPTIONS: self._response.exceptions
        })

        return result

    def _gen_call(self):
        def f(**kwargs):
            path_params = {}
            params = {}
            headers = {}
            cookies = {}
            account_id = kwargs.get('account_id')

            if account_id:
                self._server.update_url(account_id)

            logger.debug(
                    f"{self.operation_id} called " +
                    f"with {kwargs} arguments")
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
        logger.debug(
            f"Initializing client for '{self._name}' " +
            f"Spec: '{service_name}' Variables: '{variables}'")
        spec = alsdkdefs.load_service_spec(service_name, Config.get_api_dir(), version)
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
            raise ValueError("Invalid OpenAPI document")

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
                spec=s,
                session=self._session,
                variables=variables)
            for s in servers
        ]

        if not self._server and self.servers:
            if self._session:
                self._server = list(
                        filter(lambda s: self._session.validate_server(s.spec),
                               self.servers))[0]
            else:
                self._server = self.servers[0]

        self._initialize_operations()

    def _initialize_operations(self):
        self._operations = {}
        for path, path_spec in self.paths.items():
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

                if operation_id in self._operations:
                    raise AlmdrlibValueError(f"Duplication {operation_id} \
                                       specified for {self._name} API")

                # Initialize parameters (path, header, query)
                params = [
                    PathParameter(spec=s, session=self._session)
                    for s in op_spec.get(OpenAPIKeyWord.PARAMETERS, [])
                ]

                # Initialize operation's body
                body = self._initalize_request_body(
                        op_spec.pop(OpenAPIKeyWord.REQUEST_BODY, None)
                    )

                # Initialize operation's response
                response = OperationResponse(
                        op_spec.pop(OpenAPIKeyWord.RESPONSES, None)
                    )

                self._operations[operation_id] = Operation(
                    path,
                    params,
                    summary,
                    description,
                    method,
                    op_spec,
                    body,
                    response,
                    session=self._session,
                    server=self._server
                )

    def _initalize_request_body(self, body_spec=None):
        ''' Initilize request body content & parameters'''
        if not body_spec:
            return None

        request_body = RequestBody(
                required=body_spec.pop(OpenAPIKeyWord.REQUIRED, False),
                description=body_spec.pop(OpenAPIKeyWord.DESCRIPTION, None),
                session=self._session)

        content = body_spec.pop(OpenAPIKeyWord.CONTENT, {})
        for content_type, content_schema in content.items():
            request_body.add_content(
                    content_type,
                    content_schema.pop(OpenAPIKeyWord.SCHEMA),
                    content_schema.pop(OpenAPIKeyWord.X_ALERTLOGIC_SCHEMA, {})
            )
        return request_body

    def __getattr__(self, op_name):
        if op_name in self._operations:
            return self._operations[op_name]
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{op_name}'"
        )

    def __dir__(self):
        # Add in operation names
        return super().__dir__() + list(self._operations.keys())


def _normalize_schema(name, schema, required=False):
    properties = schema.get(OpenAPIKeyWord.PROPERTIES)
    if properties and bool(properties):
        return schema

    result = {
        OpenAPIKeyWord.TYPE: OpenAPIKeyWord.OBJECT,
        OpenAPIKeyWord.PROPERTIES: {
            name: schema
        }
    }

    if required:
        result[OpenAPIKeyWord.REQUIRED] = [name]
    return result


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


def update_dict_no_replace(target, source):
    for key in source.keys():
        if key not in target:
            target[key] = source[key]


def serialize_value(datatype, value):
    if OpenAPIKeyWord.STRING == datatype:
        return value
    elif OpenAPIKeyWord.BOOLEAN == datatype:
        return value and "true" or "false"
    else:
        return str(value)
