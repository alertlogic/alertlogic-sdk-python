import json
import textwrap
import logging
from pypandoc import convert_text
from almdrlib.docs.format import ServiceFormat
from almdrlib.client import OpenAPIKeyWord

logger = logging.getLogger(__name__)


class ServiceDocGenerator(object):
    def __init__(self,
                 service_name,
                 spec,
                 width=256,
                 indent_increment=2):
        self._width = width
        self._indent_increment = indent_increment
        self._initial_indent = '    '
        self._subsequent_indent = '    '
        self._service_name = service_name
        self._spec = spec
        self._doc = []

    def make_documentation(self):
        logger.info(
            f"Generating documentation for '{self._service_name}' service.")

        self._make_header()
        self._make_methods()
        return '\n'.join(self._doc).encode('utf-8')

    def _make_header(self):
        logger.debug(
            f"Making header for '{self._service_name}' service.")
        section_line = '*'*len(self._service_name)

        # Add Header Section
        header_section = ServiceFormat.CLIENT_SECTION.format(
                section_line,
                self._service_name.capitalize()
            )
        self._doc.append(header_section)

        operations = self._spec['operations']
        methods = [
            ServiceFormat.METHOD_HEADER.format(
                self._service_name.capitalize(),
                op_name
            )
            for op_name in operations.keys()
        ]

        # Add Client Section
        class_section = ServiceFormat.CLASS_SECTION.format(
                self._service_name.capitalize(),
                self._service_name,
                '\n'.join(methods)
            )
        self._doc.append(class_section)

    def _make_methods(self):
        operations = self._spec['operations']
        for op_name, op_spec in operations.items():
            self._make_method(op_name, op_spec)

    def _make_method(self, op_name, op_spec):
        '''
        Make a secition for a method
        '''
        logger.debug(
            f"Making documentation for '{op_name}' method")

        # Declare method
        indent = ServiceFormat.INDENT_INCREMENT
        self._doc.append(
                ServiceFormat.METHOD_DECLARATION.format(
                    op_name,
                    indent
                )
            )

        # Add method description
        indent += ServiceFormat.INDENT_INCREMENT
        description = self._format_text(
                op_spec.get(OpenAPIKeyWord.DESCRIPTION, ''),
                indent=indent + ServiceFormat.INDENT_INCREMENT,
                format='md'
            )
        self._doc.append(f"\n\n{description}\n\n")

        # Add method request syntax
        parameters = op_spec.get(OpenAPIKeyWord.PARAMETERS, {})

        self._make_request_syntax(
                name=op_name,
                parameters=parameters,
                indent=indent+ServiceFormat.INDENT_INCREMENT)

        # Process method parameters
        for param_name, param_spec in parameters.items():
            self._make_parameter(
                    param_name,
                    param_spec,
                    format_string=ServiceFormat.PARAM_DECLARATION,
                    indent=indent
                )

    def _make_request_syntax(self, name, parameters, indent):
        self._doc.append(ServiceFormat.REQUEST_SYNTAX_HEADER.format(indent))
        indent += ServiceFormat.INDENT_INCREMENT
        request_params = self._make_request_spec(parameters, indent)

        self._doc.append(
            ServiceFormat.REQUEST_SYNTAX_DECLARATION.format(
                name,
                request_params,
                indent
            )
        )

    def _make_request_spec(self, parameters, indent):
        indent += ServiceFormat.INDENT_INCREMENT*2
        request_spec = [
            f"{indent}{ServiceFormat.INDENT_INCREMENT}{param_name}=" +
            f"{self._get_param_spec(param_spec, indent)}"
            for param_name, param_spec in parameters.items()
        ]
        return '\n'.join(request_spec).replace('"', "'").replace("''", "'")

    def _get_param_spec(self, spec, indent):
        param_type = spec.get(OpenAPIKeyWord.TYPE, OpenAPIKeyWord.STRING)
        if param_type == OpenAPIKeyWord.OBJECT:
            return self._get_dict_param_spec(
                    spec.get(OpenAPIKeyWord.PROPERTIES, {}),
                    indent)
        elif param_type == OpenAPIKeyWord.BOOLEAN:
            return "True|False"
        else:
            enum = spec.get(OpenAPIKeyWord.ENUM)
            if enum:
                return '|'.join(f"'{v}'" for v in enum)
            else:
                return f"'{param_type}'"

    def _get_dict_param_spec(self, properties, indent):
        indent += ServiceFormat.INDENT_INCREMENT
        res = {
                name: self._get_param_spec(value, indent)
                for name, value in properties.items()
        }

        return self._format_text(
                json.dumps(res, sort_keys=True, indent=4),
                separator='\n' + indent
            )

    def _make_parameter(self, param_name, param_spec, format_string, indent):
        '''
        Make parameter section
        '''
        param_required = param_spec.get(OpenAPIKeyWord.REQUIRED, False)
        param_type = self._get_param_type(
                param_spec.get(OpenAPIKeyWord.TYPE, OpenAPIKeyWord.STRING),
                param_spec.get(OpenAPIKeyWord.FORMAT)
            )

        self._doc.append(
                format_string.format(
                    param_name,
                    param_type,
                    param_required and ServiceFormat.REQUIRED_QUALIFIER or "",
                    indent
                )
            )

        indent += ServiceFormat.INDENT_INCREMENT
        description = self._format_text(
                param_spec.get(OpenAPIKeyWord.DESCRIPTION, ""),
                indent=indent,
                format='md'
            )
        self._doc.append(f"{description}\n\n")

        if param_type == 'dict':
            self._make_dict_parameter(
                    parameters=param_spec.get(OpenAPIKeyWord.PROPERTIES, {}),
                    indent=indent
                )
        elif param_spec.get(OpenAPIKeyWord.ENUM):
            self._make_enum(param_spec[OpenAPIKeyWord.ENUM], indent)

    def _make_dict_parameter(self, parameters, indent):
        for param_name, param_spec in parameters.items():
            self._make_parameter(
                    param_name,
                    param_spec,
                    format_string=ServiceFormat.CHILD_PARAM_DECLARATION,
                    indent=indent)

    def _make_enum(self, values, indent):
        values_indent = indent + ServiceFormat.INDENT_INCREMENT
        self._doc.append(
                ServiceFormat.ENUM_DECLARATION.format(
                    ('\n' + values_indent).join(['* ' + v for v in values]),
                    indent,
                    values_indent
                )
            )

    def _get_param_type(self, type, format):
        if type == OpenAPIKeyWord.OBJECT:
            return 'dict'
        elif type == OpenAPIKeyWord.ARRAY:
            return 'array'
        else:
            return format and format or type

    def _format_text(
            self, text,
            indent='', subsequent_indent=None, separator='\n', format=None):
        '''
        Convert text from md to rst.
        '''
        conv_text = format and convert_text(text, 'rst', format=format) or text
        if not subsequent_indent:
            subsequent_indent = indent

        res = [
            textwrap.fill(
                    str,
                    width=self._width,
                    initial_indent=indent,
                    subsequent_indent=subsequent_indent)
            for str in conv_text.splitlines()
        ]
        return separator.join(res)
