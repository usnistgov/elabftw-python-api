# ELabFTW Python API

This repository holds a Python library that can be used to communicate with APIv2
of [ELabFTW](https://elabftw.net) ([Github](https://github.com/elabftw/elabftw#readme)).
It was written primarily by [Josh](https://nist.gov/people/joshua-taillon) to develop 
scripts that interface with the NIST instance of ELabFTW available at
https://***REMOVED***.

*Note:* there is an official Python API library available from 
https://github.com/elabftw/elabapi-python/, but I found it a bit cumbersome to use,
as it requires quite a bit of boilerplate code for simple tasks. The goal of *this*
library is to provide a simple interface for common tasks such as exporting experiments,
changing status, etc.

## Installation

```
pip install git+https://***REMOVED***/mml-lims/elabftw-python-api
```

or, to install from sources with [poetry](https://python-poetry.org/):

```
$ git clone https://***REMOVED***/mml-lims/elabftw-python-api
$ cd elabftw-python-api
$ poetry install
```

## Usage

Check the documentation strings, but in general, usage works as follows:

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