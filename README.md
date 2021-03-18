# The Alert Logic SDK For Python (almdrlib)

[![pypi](https://img.shields.io/pypi/v/alertlogic-sdk-python.svg)](https://pypi.python.org/pypi/alertlogic-sdk-python)
[![python](https://img.shields.io/pypi/pyversions/alertlogic-sdk-python.svg)](https://pypi.python.org/pypi/alertlogic-sdk-python)
[![Build Status](https://travis-ci.com/alertlogic/alertlogic-sdk-python.svg?branch=master)](https://travis-ci.com/alertlogic/alertlogic-sdk-python)
[![Docs](https://readthedocs.org/projects/pip/badge/?version=latest&style=plastic)](https://readthedocs.org/projects/alertlogic-sdk-python)

Alert Logic Software Development Kit for Python allows developers to integrate with Alert Logic MDR Services.

## Quick Start

1. Install the library:

	```pip install alertlogic-sdk-python```

2. Set up configuration file (in e.g. ```~/.alertlogic/config```

	```
	[default]
	access_key_id = YOUR_KEY
	secret_key = YOUR_SECRET
	```

	To create and manage access keys, use the [Alert Logic Console](https://console.account.alertlogic.com/#/aims/users).  For information on creating an access key, see 
	[https://docs.alertlogic.com/prepare/access-key-management.htm](https://docs.alertlogic.com/prepare/access-key-management.htm) 
   
	Optionally you can specify if you are working with ***integration*** deployment of Alert Logic MDR Services or ***production*** by specifying:

	```
	global_endpoint=integration
	```

	```
	global_endpoint=production
	```

	NOTE: If *global_endpoint* isn't present, SDK defaults to production.

3. Test installation
Launch python interpreter and then type:

	```
	import almdrlib
	aims = almdrlib.client("aims")
	res = aims.get_account_details()
	print(f"{res.json()}")
	```


## Development

### Getting Started

#### Prerequisites:

1. *Python v3.7* or newer
2. *virtualenv* or *virtualenvwrapper* (We recommend ***virtualenvwrapper***  <https://virtualenvwrapper.readthedocs.io/en/latest/> )
3. To produce RESTful APIs documentation install *redoc-cli* and *npx*:

    ```
    npm install --save redoc-cli
    npm install --save npx
    ```



Setup your development environment and install required dependencies:

```
export WORKON_HOME=~/environments
mkdir -p $WORKON_HOME
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv alsdk
```

```
git clone https://github.com/alertlogic/alertlogic-sdk-python
cd alertlogic-sdk-python
pip install -r requirements_dev.txt
pip install -e .
```
    
### Using local services

- Setup a local profile:

```
[aesolo]
access_key_id=skip
secret_key=skip
global_endpoint=map
endpoint_map_file=aesolo.json
```

- Write an endpoint map (here, `~/.alertlogic/aesolo.json`; `endpoint_map_file` can also be an absolute path):

```
{
  "aecontent" : "http://127.0.0.1:8810",
  "aefr" : "http://127.0.0.1:8808",
  "aepublish" : "http://127.0.0.1:8811",
  "aerta" : "http://127.0.0.1:8809",
  "aetag" : "http://127.0.0.1:8812",
  "aetuner": "http://127.0.0.1:3000",
  "ingest" : "http://127.0.0.1:9000"
}
```

Alternatively `global_endpoint` configuration option or `ALERTLOGIC_ENDPOINT` value might be set to the url value:
```
[aesolo]
access_key_id=skip
secret_key=skip
global_endpoint=http://api.aesolo.com
...
global_endpoint=http://api.aesolo.com:3001
```

```
export ALERTLOGIC_ENDPOINT="http://api.aesolo.com"
...
export ALERTLOGIC_ENDPOINT="http://api.aesolo.com:3001"
```