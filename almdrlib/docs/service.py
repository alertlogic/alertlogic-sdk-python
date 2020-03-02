import textwrap
from pypandoc import convert_text
from almdrlib.client import OpenAPIKeyWord

CLIENT_SECTION = """
{0}
{1}
{0}

.. contents:: Table of Contents
   :depth: 2

"""

CLASS_SECTION = """

======
Client
======

.. py:class:: {0}.Client

  A client object representing '{0}' Service::


    import almdrlib

    client = almdrlib.client('{1}')

  Available methods:

{2}


"""

METHOD_HEADER = """
  *   :py:meth:`~{0}.Client.{1}`


"""

METHOD_DECLARATION = """

  .. py:method:: {0}(**kwargs)

"""
METHOD_DESC_INDENT = '    '

REQUIRED_QUALIFIER = "**[REQUIRED]**"
PARAM_DECLARATION = """

    :type {0}: {1}
    :param {0}: {2}"""
PARAM_DESC_IDENTENT = '      '


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
        header_section = CLIENT_SECTION.format(
                section_line,
                self._service_name.capitalize()
            )
        self._doc.append(header_section)

        operations = self._spec['operations']
        methods = [
            METHOD_HEADER.format(
                    self._service_name.capitalize(),
                    op_name
                )
            for op_name in operations.keys()
        ]

        # Add Client Section
        class_section = CLASS_SECTION.format(
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
        self._doc.append(METHOD_DECLARATION.format(op_name))
        description = self._format_text(
                op_spec.get(OpenAPIKeyWord.DESCRIPTION, ''),
                indent=METHOD_DESC_INDENT
            )
        self._doc.append(f"\n\n{description}\n\n")

        # Process method parameters
        parameters = op_spec.get(OpenAPIKeyWord.PARAMETERS, {})
        for param_name, param_spec in parameters.items():
            self._make_parameter(param_name, param_spec)

    def _make_parameter(self, param_name, param_spec):
        '''
        Make parameter section
        '''
        param_required = param_spec.get(OpenAPIKeyWord.REQUIRED, False)
        param_type = self._get_param_type(
                param_spec.get(OpenAPIKeyWord.TYPE, OpenAPIKeyWord.STRING)
            )

        self._doc.append(
                PARAM_DECLARATION.format(
                    param_name,
                    param_type,
                    param_required and REQUIRED_QUALIFIER or ""
                )
            )
        description = self._format_text(
                param_spec.get(OpenAPIKeyWord.DESCRIPTION, ""),
                indent=PARAM_DESC_IDENTENT
            )
        self._doc.append(f"{description}\n\n")

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
