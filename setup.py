import re
import json
from urllib import request
from setuptools import setup, find_packages

with open('HISTORY.rst') as history_file:
    history = history_file.read()

with open('README.md') as readme_file:
    readme = readme_file.read()

try:
    # This is to force definitions to be upgraded every build not related to the definitions change
    defs_url_pypi = "https://pypi.org/pypi/alertlogic-sdk-definitions/json"
    with request.urlopen(defs_url_pypi) as defs_rq:
        defs_info = json.loads(defs_rq.read())
    definitions_latest_version = defs_info['info']['version']
    definitions_dependency = 'alertlogic-sdk-definitions>=' + definitions_latest_version
except:
    definitions_dependency = 'alertlogic-sdk-definitions>=0.0.47'

requirements = [
        'requests>=2.18',
        'configparser>=4.0.2',
        'pyyaml==5.1.2',
        'jsonschema[format_nongpl]==3.2.0',
        'm2r==0.2.1',
        definitions_dependency
    ]

test_requirements = [ ]

setup(
    name='alertlogic-sdk-python',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    url='https://github.com/alertlogic/alertlogic-sdk-python',
    license='MIT license',
    author='Alert Logic Inc.',
    author_email='devsupport@alertlogic.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ],
    description='Alert Logic Software Development Kit for Python.',
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    scripts=[],
    packages=find_packages(exclude=['contrib', 'docs', 'tests*', 'troubleshooting']),
    include_package_data=True,
    test_suite='tests',
    tests_require=test_requirements,
    zip_safe=False,
    platforms='any',
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=3',
            'mock>=2.0.0',
            'httpretty>=0.8.14',
            'pycodestyle>=2.3.1',
            'jsonschema[format_nongpl]==3.2.0'
        ],
    },
    keywords=['alertlogic-sdk', 'alertlogic-sdk-python', 'alertlogic-mdr-sdk', 'almdrlib', 'alertlogic']
)
