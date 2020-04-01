import re
import ast
from os import path
from setuptools import setup, find_packages

_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('almdrlib/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

with open('HISTORY.rst') as history_file:
    history = history_file.read()

with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = [
        'requests>=2.18',
        'configparser>=4.0.2',
        'pyyaml==5.1.2',
        'jsonschema[format_nongpl]==3.2.0',
        'm2r==0.2.1'
    ]

test_requirements = [ ]

setup(
    name='alertlogic-sdk-python',
    version=version,
    url='https://github.com/alertlogic/alertlogic-sdk-python',
    license='MIT license',
    author='Alert Logic Inc.',
    author_email='devsupport@alertlogic.com',
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
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
