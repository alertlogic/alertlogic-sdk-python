import textwrap
from pypandoc import convert_text
from almdrlib.docs.format import ServiceFormat
from almdrlib.client import OpenAPIKeyWord


class ServiceDocGenerator(object):
    def __init__(self,
                 service_name,
                 spec,
                 width=80,
                 indent_increment=2):
        self._width = width
        self._indent_increment = indent_increment
        self._initial_indent = '    '
        self._subsequent_indent = '    '
        self._service_name = service_name
        self._spec = spec
        self._doc = []

    def make_documentation(self):
        self._make_header()
        self._make_methods()
        return '\n'.join(self._doc).encode('utf-8')

    def _make_header(self):
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
        indent = ServiceFormat.INDENT_INCREMENT
        self._doc.append(
                ServiceFormat.METHOD_DECLARATION.format(
                    op_name,
                    indent
                )
            )
        
        indent += ServiceFormat.INDENT_INCREMENT
        description = self._format_text(
                op_spec.get(OpenAPIKeyWord.DESCRIPTION, ''),
                indent=indent + ServiceFormat.INDENT_INCREMENT
            )
        self._doc.append(f"\n\n{description}\n\n")

        # Process method parameters
        parameters = op_spec.get(OpenAPIKeyWord.PARAMETERS, {})
        for param_name, param_spec in parameters.items():
            self._make_parameter(
                    param_name,
                    param_spec,
                    format_string=ServiceFormat.PARAM_DECLARATION,
                    indent=indent
                )

    def _make_parameter(self, param_name, param_spec, format_string, indent):
        '''
        Make parameter section
        '''
        param_required = param_spec.get(OpenAPIKeyWord.REQUIRED, False)
        param_type = self._get_param_type(
                param_spec.get(OpenAPIKeyWord.TYPE, OpenAPIKeyWord.STRING)
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
                indent=indent
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

    def _get_param_type(self, type):
        if type == OpenAPIKeyWord.OBJECT:
            return 'dict'
        else:
            return type

    def _format_text(self, text, indent='', subsequent_indent=None):
        '''
        Convert text from md to rst.
        '''
        conv_text = convert_text(text, 'rst', format='md')
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
        return '\n'.join(res)
