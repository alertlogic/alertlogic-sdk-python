import os
import json
from urllib import request
from setuptools import setup, find_packages

def aggregate_release(lns, acc):
    cut = lns[0:3]
    rest = lns[4:]
    if not lns:
        return acc
    tag = cut[0].strip()
    date = cut[1].strip()
    subject = cut[2].strip()
    rel_acc = acc.get(tag, [])
    rel_acc.append(f"* {date} - {subject}")
    acc[tag] = rel_acc
    return aggregate_release(rest, acc)


with os.popen('git --no-pager log --tags --pretty="%S%n%aD%n%s%n"') as stream:
    lines = stream.readlines()
    aggregated = aggregate_release(lines, {})
    res = []
    for rel, changes in aggregated.items():
        ch = '\n'.join(changes)
        res.append(f"### {rel}\n\n{ch}\n")
    hist = "\n".join(res)
    history_header = \
'''
## History

'''
    history = history_header + hist

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
    definitions_dependency = 'alertlogic-sdk-definitions>=v0.0.74'

requirements = [
        'requests>=2.34.2',
        'urllib3>=2.8.0',
        'pyyaml>=6.0.3',
        'jsonschema[format_nongpl]==3.2.0',
        'm2r2>=2.1.0',
        'boto3>=1.43.118',
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
    python_requires='>=3.11',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Programming Language :: Python :: 3.15'
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
            'pytest>=9.1.1',
            'mock>=5.2.0',
            'httpretty>=1.1.4',
            'pycodestyle>=2.15.0',
            'jsonschema[format_nongpl]==3.2.0'
        ],
    },
    keywords=['alertlogic-sdk', 'alertlogic-sdk-python', 'alertlogic-mdr-sdk', 'almdrlib', 'alertlogic']
)
