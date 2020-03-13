

class ServiceFormat(object):
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

    REQUEST_SYNTAX_HEADER = """
{0}**Request Syntax**
{0}::

    """

    REQUEST_SYNTAX_DECLARATION = """
{2}response = client.{0}(
{1}
{2})
    """

    METHOD_DECLARATION = """

{1}.. py:method:: {0}(**kwargs)

    """

    REQUIRED_QUALIFIER = "**[REQUIRED]**"
    PARAM_DECLARATION = """

{3}:type {0}: {1}
{3}:param {0}: {2}"""

    CHILD_PARAM_DECLARATION = """
{3}- **{0}** *({1}) --{2}*"""

    ENUM_DECLARATION = """
{1}*Valid Values:*
{2}{0}
"""

    INDENT_INCREMENT = '  '
