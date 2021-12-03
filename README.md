[![Tests](https://github.com//ckanext-duo/workflows/Tests/badge.svg?branch=main)](https://github.com//ckanext-duo/actions)

# ckanext-duo

Translate dataset/organization/group titles and descriptions using custom `<field>_<locale>` fields.


## Requirements

Compatibility with core CKAN versions:

| CKAN version | Compatible? |
|--------------|-------------|
| 2.9          | yes         |
|              |             |


## Installation

To install ckanext-duo:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

1. Clone the source and install it on the virtualenv

    pip install ckanext-duo


1. Add `duo duo_dataset duo_organization duo_group` to the `ckan.plugins`
   setting in your CKAN config file.

1. Make sure you have non-empty `ckan.locale_default` and
   `ckan.locales_offered` options inside CKAN config file.

1. Restart CKAN.


## Config settings

None at present
