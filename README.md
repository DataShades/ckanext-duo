[![Tests](https://github.com//ckanext-duo/workflows/Tests/badge.svg?branch=main)](https://github.com//ckanext-duo/actions)

# ckanext-duo

Translate dataset/organization/group titles and descriptions using custom `<field>_<locale>` fields.


## Requirements

Compatibility with core CKAN versions:

| CKAN version | Compatible? |
|--------------|-------------|
| 2.9          | yes         |

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


## How to use

Depending on entity that must be translated(group, dataset, organization), one
must update corresponding metadata schema. Following fields must be added:

- organization/group
  - `title_<locale>` (ex., `title_ar`)
  - `description_<locale>` (ex., `description_ar`)
- dataset
  - `title_<locale>` (ex., `title_ar`)
  - `notes_<locale>` (ex., `notes_ar`)

If you are using ckanext-scheming, define field like this::

	...
	{
        "field_name": "title_ar",
        "label": "Arabic Name",
        "validators": "if_empty_same_as(title)"
	},
	...

Or you can define custom fields using low-level `IDatasetForm`/`IGroupForm`/`IOrganizationForm`.

If none of above is possible, provide an extra field via CKAN extras(key/value
pairs of fields in the very bottom of dataset/group/organization form).
