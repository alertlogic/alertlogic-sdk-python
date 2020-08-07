import json
import logging
import itertools
try:
    from m2r import convert
except Exception:
    def convert(text):
        return text

from alsdkdefs import OpenAPIKeyWord

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

            yield from self._make_request_parameters(
                    op_name, parameters, indent)

            yield from self._make_response(
                    op_spec.get('response', {}), indent)

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

    def _make_request_parameters(self, op_name, parameters, indent):
        indent = self._indent(indent)
        for name, spec in sorted(parameters.items()):
            yield ''
            if 'content' in spec:
                type = ' | '.join([
                        get_param_type(v)
                        for v in spec['content'].values()
                    ])
            else:
                type = get_param_type(spec)

            yield f'{indent}:type {name}: {type}'
            if 'required' in spec or 'x-alertlogic-required' in spec:
                yield f'{indent}:param {name}:  **[REQUIRED]**'
            else:
                yield f'{indent}:param {name}:'
            yield ''

            for line in convert(spec.get('description', "")).splitlines():
                yield f'{indent}{indent}{line}'

            yield from self._make_property(
                    spec, name=name,
                    declare=False, indent=self._indent(indent))

            if name == 'content_type':
                yield from self._make_content_type(
                        op_name,
                        spec.pop('x-alertlogic-payload-content'),
                        indent=indent)

            elif 'content' in spec:
                yield from self._make_request_body_parameter(
                        spec.pop('content'),
                        name,
                        indent=self._indent(indent)
                    )
            else:
                yield from self._make_properties(
                        spec=spec,
                        indent=self._indent(indent),
                        declare=False
                    )

    def _make_content_type(self, op_name, spec, indent):
        if not spec:
            return

        content_indent = self._indent(indent)
        valid_values = ', '.join([
                f'``{v}``'
                for v in spec.keys()]
            )
        yield ''
        yield f'{content_indent}*Valid values*: {valid_values}'
        yield ''
        yield f'{content_indent}.. note::'
        content_indent = self._indent(content_indent)
        yield (f'{content_indent}Following parameters depend on the'
               '``content_type`` value:')

        properties = []
        for property in itertools.chain.from_iterable(spec.values()):
            if property not in properties:
                properties.append(property)

        prop_links = [
                f':paramref:`.{op_name}.{v}`'
                for v in sorted(properties)
            ]
        yield f'{content_indent}{", ".join(prop_links)}'

    def _make_request_body_parameter(self, specs, name, indent=None):
        yield ''
        yield f'{indent}Below is specification of ``{name}`` parameter '
        yield (f"{indent}as it relates to the ``content_type`` "
               "parameter's value")

        for content_type, spec in specs.items():
            yield ''
            spec_indent = self._indent(indent)
            yield f'{spec_indent}.. toggle-header::'

            title = f'``content_type`` == {content_type}'
            spec_indent = self._indent(spec_indent)
            yield f'{spec_indent}:header: {title}'

            yield ''
            spec_indent = self._indent(spec_indent)
            yield from self._make_property(spec, indent=spec_indent)
            yield from self._make_properties(
                    spec=spec,
                    indent=self._indent(spec_indent))

    def _make_properties(self, spec, name=None, indent=None, declare=True):
        type = get_param_type(spec)

        if type == 'list':
            if 'items' in spec:
                yield from self._make_property(
                        spec['items'], name=name, indent=indent)
                yield from self._make_properties(
                        spec=spec['items'], indent=self._indent(indent))

            elif 'enum' in spec:
                yield from self._make_property(spec, indent=indent)

            else:
                logger.warn(
                        f"Unknown key for data type for {name}: {type}."
                        f"{json.dumps(spec, indent=2)}")

        elif type == 'dict':
            for p_name, p_spec in sorted(spec.get('properties', {}).items()):
                yield from self._make_property(
                        spec=p_spec, name=p_name, indent=indent)
                yield from self._make_properties(
                        spec=p_spec,
                        indent=self._indent(indent))

        elif type == 'oneOf' or type == 'anyOf':
            yield from self._make_indirect_property(
                    specs=spec.get('oneOf', spec.get('anyOf')),
                    name=name, indent=indent)

    def _make_indirect_property(self, specs, name=None, indent=None):
        yield ''
        yield f'{indent}.. content-tabs::'
        yield ''
        for spec in specs:
            title = spec.get('title', spec.get('type', name))
            spec_indent = self._indent(indent)
            yield ''
            yield f'{spec_indent}.. tab-container:: {title}'

            spec_indent = self._indent(spec_indent)
            yield f'{spec_indent}:title: {title}'
            yield from self._make_property(spec, indent=spec_indent)
            yield from self._make_properties(
                    spec=spec,
                    indent=spec_indent)

    def _make_property(self, spec, name=None, indent=None, declare=True):
        yield ''
        if declare:
            type = get_param_type(spec)
            if name:
                if 'required' in spec or 'x-alertlogic-required' in spec:
                    yield f'{indent}- **{name}** *({type}) --* **[REQUIRED]**'
                else:
                    yield f'{indent}- **{name}** *({type}) --*'
            else:
                yield f'{indent}- *({type}) --*'

        indent = self._indent(indent)
        if declare:
            yield ''
            for line in convert(spec.get('description', "")).splitlines():
                yield f'{indent}{line}'

        if 'enum' in spec:
            valid_values = ', '.join([f'``{v}``' for v in spec['enum']])
            yield ''
            yield f'{indent}*Valid values*: {valid_values}'

        if 'default' in spec:
            yield ''
            yield f'{indent}*Default*: ``{spec["default"]}``'

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

        yield from self._make_properties(
                spec=spec,
                indent=self._indent(indent))


def get_param_spec(spec):
    if OpenAPIKeyWord.ONE_OF in spec:
        types = [get_param_type(v) for v in spec[OpenAPIKeyWord.ONE_OF]]
        return '|'.join(list(set(sorted(types))))

    if OpenAPIKeyWord.ANY_OF in spec:
        types = [get_param_type(v) for v in spec[OpenAPIKeyWord.ANY_OF]]
        return '|'.join(list(set(sorted(types))))

    if OpenAPIKeyWord.CONTENT in spec:
        content = spec.get(OpenAPIKeyWord.CONTENT, {})
        return '|'.join(
                sorted([get_param_type(v) for v in content.values()])
            )

    param_type = spec.get(OpenAPIKeyWord.TYPE)
    if param_type == OpenAPIKeyWord.ARRAY:
        return [get_param_spec(spec.get(OpenAPIKeyWord.ITEMS, {}))]

    if param_type == OpenAPIKeyWord.OBJECT:
        properties = spec.get(OpenAPIKeyWord.PROPERTIES, {})
        return {k: get_param_spec(v) for k, v in sorted(properties.items())}

    if param_type == OpenAPIKeyWord.BOOLEAN:
        return "False|True"

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
    elif format:
        return format
    elif type:
        return type
    else:
        if 'oneOf' in spec:
            return 'oneOf'
        elif 'anyOf' in spec:
            return 'anyOf'
        else:
            raise ValueError(
                f'Unsupported parameter type. {json.dumps(spec, indent=2)}')


def format_json(value, indent=None):
    if not indent:
        indent = ''
    res = json.dumps(value, sort_keys=True, indent=4).splitlines()
    return f'\n{indent}'.join(res)
