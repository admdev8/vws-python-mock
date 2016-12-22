[![Build Status](https://travis-ci.org/adamtheturtle/vws-python.svg?branch=master)](https://travis-ci.com/adamtheturtle/vws-python)
[![Coverage Status](https://coveralls.io/repos/github/adamtheturtle/vws-python/badge.svg)](https://coveralls.io/github/adamtheturtle/vws-python)
[![Requirements Status](https://requires.io/github/adamtheturtle/vws-python/requirements.svg?branch=master)](https://requires.io/github/adamtheturtle/vws-python/requirements/?branch=master)

# vws-python

Python wrapper for Vuforia Web Services (VWS) API

# Installation

This package has not yet been uploaded to PyPI.

This requires Python 3.5+.
Get in touch with `adamdangoor@gmail.com` if you would like to see this with another language.

# Tests

To run the tests, first install the dependencies:

    pip install -e .[dev]

Create an environment variable file for secrets:

    cp vuforia_secrets.env.example vuforia_secrets.env

Some tests require Vuforia credentials.
To run these tests, add the Vuforia credentials to the file `vuforia_secrets.env`.
See "Connecting to Vuforia".

Then run `pytest`:

    pytest

## Connecting to Vuforia

To connect to Vuforia,
a Vuforia target database must be created via the Vuforia Web UI.
Then, secret keys must be set as environment variables.

The test infrastructure allows those keys to be set in the file `vuforia_secrets.env`.
See `vuforia_secrets.env.example` for the environment variables to set.

To create a target database, first create a license key in the [License Manager](https://developer.vuforia.com/targetmanager/licenseManager/licenseListing).
Then, add a database from the [Target Manager](https://developer.vuforia.com/targetmanager).

To find the environment variables to set in the `vuforia_secrets.env` file,
visit the Target Database in the Target Manager and view the "Database Access Keys".
