# ELabFTW Python API

[![Static Badge](https://img.shields.io/badge/Documentation-blue?logo=readthedocs&logoColor=white&labelColor=gray)](https://pages.nist.gov/elabftw-python-api) [![Static Badge](https://img.shields.io/badge/repository_link-red?logo=github&logoColor=white&labelColor=grey)](https://github.com/usnistgov/elabftw-python-api/)


This repository 
([https://github.com/usnistgov/elabftw-python-api/](https://github.com/usnistgov/elabftw-python-api/)) 
contains a (work in progress) Python library that can be used to communicate with APIv2
of [eLabFTW](https://elabftw.net) ([Github](https://github.com/elabftw/elabftw#readme)).
It was written primarily by [Josh Taillon](https://orcid.org/0000-0002-5185-4503) to develop 
scripts that interface with the NIST instance of eLabFTW. In general, it provides mostly
read-only interfaces to access information about experiments and items within an eLabFTW
instance (see the "Usage" section below). It is in a pre-release state currently, but
is functional enough to be useful.

*Note:* there is an official Python API library available from 
[https://github.com/elabftw/elabapi-python/](https://github.com/elabftw/elabapi-python/),
which works perfectly well, but requires quite a bit of boilerplate code
for simple tasks. The goal of *this* library is to provide a simple interface for common
tasks such as exporting experiments, changing status, etc.

## Installation

```
pip install git+https://github.com/usnistgov/elabftw-python-api
```

or, to install from sources with [poetry](https://python-poetry.org/):

```
$ git clone https://github.com/usnistgov/elabftw-python-api
$ cd elabftw-python-api
$ poetry install
```

## Usage

Check the documentation strings or the dedicated documentation page
([https://pages.nist.gov/elabftw-python-api](https://pages.nist.gov/elabftw-python-api)), 
but in general usage works as follows:

```python
# import the library:
from elabapi import ELabApi, TeamApi

# create an instance of the API with URL and credentials
e = ELabApi(
    api_base_url=os.environ.get("ELAB_URL"),
    api_key=os.environ.get("ELAB_API_KEY"),
)

# get an experiment's JSON representation:
e.get_experiment(64)

# get all experiments with a given status:
e.get_experiments_by_status(status="Ready for Export")

# export an experiment
e.export_experiment(64, format='pdf')  # exports to a pdf file in the current directory
e.export_experiment(64, format='eln')  # export to ELN format archive (see https://github.com/TheELNConsortium/TheELNFileFormat/blob/master/SPECIFICATION.md)
```

### Settings

There are a couple settings you need to provide, which are the base URL for the API
endpoint, and an API Key. These can either be provided as strings when you initialize an
`ELabApi()` instance, or (better) can be provided by querying from the environment. I
like to use the [`python-dotenv`](https://pypi.org/project/python-dotenv/) library to
do this, which allows you to place a `.env` file in the current directory with values
you want to be part of the environment, and then call:

```python
from dotenv import load_dotenv
load_dotenv()
```

to make them available to your script via `os.environ.get()` (as used in the example
above). This repo includes a `.env.example` file that you can rename to `.env` and use
by replacing your API key. An API key for your ELab user can be generated at
from the relevant tab in your "User control panel".

The `CERT_BUNDLE` variable allows you to use a custom certificate bundle to validate 
requests to the API. This can be used if your deployment of eLabFTW uses internal or
self-signed certificates. Otherwise, if the value is not defined, SSL verification
will be disabled (which is fine for testing, but not recommended for production
deployment).