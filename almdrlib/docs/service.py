import json
import logging
import itertools
from m2r import convert
from almdrlib.client import OpenAPIKeyWord

logger = logging.getLogger(__name__)


class ServiceDocGenerator(object):
    def __init__(self,
                 service_name,
                 spec,
                 initial_indent='  ',
                 indent_increment=2):
        self._initial_indent = initial_indent
        self._indent_increment = indent_increment
        self._service_name = service_name
        self._spec = spec

    def _indent(self, indent, count=1):
        return indent + self._initial_indent * count

    def get_documentation(self):
        generators = []
        generators.append(self._make_header())
        generators.append(self._make_class())
        generators.append(self._make_methods())
        return iter(itertools.chain(*generators))

    def _make_header(self):
        yield self._service_name.capitalize()
        yield '*' * len(self._service_name)
        yield ''

        yield '.. contents:: Table of Contents'
        yield '   :depth: 2'
        yield ''

    def _make_class(self):
        yield '======'
        yield 'Client'
        yield '======'

        indent = self._initial_indent
        c_name = self._service_name.capitalize()
        yield f'.. py:class:: {c_name}.Client'
        yield ''
        yield f"{indent}A client object representing '{c_name}' Service::"
        yield ''

        yield f'{indent*2}import almdrlib'
        yield ''
        yield f"{indent*2}client = almdrlib.client('{self._service_name}')"
        yield ''

        yield f'{indent}Available methods:'
        for op_name in self._spec['operations'].keys():
            yield ''
            yield f'{indent}*   :py:meth:`~{c_name}.Client.{op_name}`'
            yield ''

    def _make_methods(self):
        indent = self._initial_indent
        for op_name, op_spec in self._spec['operations'].items():
            yield ''
            yield f'{indent}.. py:method:: {op_name}(**kwargs)'
            for line in convert(op_spec.get('description', "")).splitlines():
                yield f'{indent}{indent}{line}'

            parameters = op_spec.get('parameters', {})
            for line in self._make_request_syntax(
                    op_name, parameters, self._indent(indent)):
                yield line

            yield from self._make_request_parameters(parameters, indent)

            yield from self._make_response(op_spec.get('response', {}), indent)

    def _make_request_syntax(self, name, parameters, indent):
        yield ''
        yield f'{indent}**Request Syntax**'
        yield f'{indent}::'
        yield ''

        indent = self._indent(indent)
        yield f'{indent}response = client.{name}('

        param_indent = self._indent(indent, 2)
        request_spec = [
                f"{param_indent}{param_name}=" +
                format_json(get_param_spec(param_spec), param_indent)
                for param_name, param_spec in parameters.items()
            ]

        result = '\n'.join(request_spec).replace('"', "'").replace("''", "'")
        for line in result.splitlines():
            yield f'{line}'
        yield f'{indent})'

    def _make_request_parameters(self, parameters, indent):
        for name, spec in parameters.items():
            yield ''
            type = get_param_type(spec)
            yield f'{indent}:type {name}: {type}'
            if spec.get('required'):
                yield f'{indent}:param {name}: **[REQUIRED]**'
            else:
                yield f'{indent}:param {name}:'
            yield ''

            for line in convert(spec.get('description', "")).splitlines():
                yield f'{indent}{indent}{line}'

    def _make_response(self, spec, indent):
        yield ''
        if not bool(spec):
            yield f'{indent}:returns: None'
            yield ''
            return ''

        yield f'{indent}:rtype: {get_param_type(spec)}'
        yield f'{indent}:returns:'

        indent = self._indent(indent)
        yield f'{indent}**Response Syntax**'
        yield ''
        yield f'{indent}::'

        yield ''
        syntax_indent = self._indent(indent)
        syntax = format_json(get_param_spec(spec))
        for line in syntax.replace('"', "'").replace("''", "'").splitlines():
            yield f'{syntax_indent}{line}'

        yield ''
        yield f'{indent}**Response Definitions**'
        yield ''

        for line in self._make_response_spec(spec, ''):
            yield f'{indent}{line}'

    def _make_response_spec(self, spec, indent):
        if 'type' not in spec:
            if 'oneOf' in spec:
                _spec = spec['oneOf']
                yield ''
                yield f'{indent} * One of the following objects:'
                yield ''
            elif 'anyOf' in spec:
                _spec = spec['anyOf']
                yield ''
                yield f'{indent} * Any of the following objects:'
                yield ''
            else:
                logger.warn(f"Unsupported response. {json.dumps(spec)}")
                return

            indent = self._indent(indent)
            for t_spec in _spec:
                yield f'{indent}* ``{t_spec.get("title")}`` -'
                yield ''
                for line in convert(
                        t_spec.get('description', "")).splitlines():
                    yield f'{indent}{indent}{line}'
                    yield ''

                yield from self._make_response_parameters(
                        t_spec.get('properties', {}),
                        self._indent(indent))

        else:
            datatype = spec['type']
            if datatype == 'object':
                # Dictionary parameter
                yield f'{indent}- *(dict) --*'
                yield ''
                for line in convert(spec.get('description', "")).splitlines():
                    yield f'{indent}{indent}{line}'

                yield ''
                yield from self._make_response_parameters(
                            spec.get('properties', {}),
                            self._indent(indent))

            if datatype == 'array':
                yield ''
                for line in convert(spec.get('description', "")).splitlines():
                    yield f'{indent}{line}'

                if 'items' in spec:
                    yield from self._make_response_spec(
                                spec['items'],
                                self._indent(indent))

    def _make_response_parameters(self, parameters, indent):
        for name, spec in parameters.items():
            yield ''
            type = get_param_type(spec)
            if spec.get('required'):
                yield f'{indent}**{name}** *({type}) --* **[REQUIRED]**'
            else:
                yield f'{indent}**{name}** *({type}) --*'
            yield ''

            for line in convert(spec.get('description', "")).splitlines():
                yield f'{indent}{indent}{line}'
            yield ''

            if type == 'dict':
                yield from self._make_response_parameters(
                            spec.get('properties', {}),
                            self._indent(indent))

        yield ''


def get_param_spec(spec):
    if OpenAPIKeyWord.ONE_OF in spec:
        return get_param_spec(spec[OpenAPIKeyWord.ONE_OF][0])

    if OpenAPIKeyWord.ANY_OF in spec:
        return get_param_spec(spec[OpenAPIKeyWord.ANY_OF][0])

    param_type = spec.get(OpenAPIKeyWord.TYPE)
    if param_type == OpenAPIKeyWord.ARRAY:
        return [get_param_spec(spec.get(OpenAPIKeyWord.ITEMS, {}))]

    if param_type == OpenAPIKeyWord.OBJECT:
        properties = spec.get(OpenAPIKeyWord.PROPERTIES, {})
        return {k: get_param_spec(v) for k, v in properties.items()}

    if param_type == OpenAPIKeyWord.BOOLEAN:
        return "True|False"

    enum = spec.get(OpenAPIKeyWord.ENUM)
    if enum:
        return '|'.join(f"'{v}'" for v in enum)
    else:
        return f"'{param_type}'"


def get_param_type(spec):
    type = spec.get('type', 'object')
    format = spec.get('format')

    if type == 'object':
        return 'dict'
    elif type == 'array':
        return 'list'
    else:
        return format and format or type


def format_json(value, indent=None):
    if not indent:
        indent = ''
    res = json.dumps(value, sort_keys=True, indent=4).splitlines()
    return f'\n{indent}'.join(res)
