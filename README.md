# The Alert Logic SDK For Python (almdrlib)

[![pypi](https://img.shields.io/pypi/v/alertlogic-sdk-python.svg)](https://pypi.python.org/pypi/alertlogic-sdk-python)
[![python](https://img.shields.io/pypi/pyversions/alertlogic-sdk-python.svg)](https://pypi.python.org/pypi/alertlogic-sdk-python)
[![Build Status](https://travis-ci.com/alertlogic/alertlogic-sdk-python.svg?branch=master)](https://travis-ci.com/alertlogic/alertlogic-sdk-python)

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

1. *Python v3.7* or older
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
    
