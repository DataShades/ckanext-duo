from __future__ import annotations
from typing import Any

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
import ckan.model as model
from ckan.lib.plugins import DefaultDatasetForm, DefaultGroupForm, DefaultOrganizationForm

from .signals import setup_listeners

CONFIG_MODIFY_PACKAGE_SCHEMA = "ckanext.duo.modify_dataset_schema"
CONFIG_MODIFY_ORGANIZATION_SCHEMA = "ckanext.duo.modify_organization_schema"
CONFIG_MODIFY_GROUP_SCHEMA = "ckanext.duo.modify_group_schema"
CONFIG_TRANSLATED_SEARCH_GROUPS  = "ckanext.duo.translate_org_during_search"

DEFAULT_TRANSLATED_SEARCH_GROUPS = False
DEFAULT_MODIFY_PACKAGE_SCHEMA = False
DEFAULT_MODIFY_ORGANIZATION_SCHEMA = False
DEFAULT_MODIFY_GROUP_SCHEMA = False


class DuoPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    def get_helpers(self):
        return {
            "duo_offered_locales": lambda: tk.aslist(tk.config.get("ckan.locales_offered", "en")),
            "duo_default_locale": lambda: tk.config.get("ckan.locale_default", "en"),
        }

    def update_config(self, config_):
        tk.add_template_directory(config_, "templates")
        setup_listeners()


class DuoDatasetPlugin(plugins.SingletonPlugin, DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer, inherit=True)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IDatasetForm, inherit=True)


    def update_config(self, config_):
        if tk.asbool(tk.config.get(CONFIG_MODIFY_PACKAGE_SCHEMA, DEFAULT_MODIFY_PACKAGE_SCHEMA)):
            tk.add_template_directory(config_, "dataset_templates")
        setup_listeners()

    def package_types(self):
        return []

    def is_fallback(self):
        return tk.asbool(tk.config.get(CONFIG_MODIFY_PACKAGE_SCHEMA, DEFAULT_MODIFY_PACKAGE_SCHEMA))

    def _modify_package_schema(self, schema):
        locales = tk.h.duo_offered_locales()
        if_empty_same_as = tk.get_validator("if_empty_same_as")
        convert_to_extras = tk.get_validator("convert_to_extras")

        for locale in locales:
            schema[f"title_{locale}"] = [if_empty_same_as("title"), convert_to_extras]
            schema[f"notes_{locale}"] = [if_empty_same_as("notes"), convert_to_extras]

        return schema

    def show_package_schema(self):
        locales = tk.h.duo_offered_locales()
        schema = super().show_package_schema()
        ignore_missing = tk.get_validator("ignore_missing")
        convert_from_extras = tk.get_validator("convert_from_extras")
        for locale in locales:
            schema[f"title_{locale}"] = [convert_from_extras, ignore_missing]
            schema[f"notes_{locale}"] = [convert_from_extras, ignore_missing]
        return schema

    def update_package_schema(self):
        schema = super().update_package_schema()
        self._modify_package_schema(schema)
        return schema

    def create_package_schema(self):
        schema = super().create_package_schema()
        self._modify_package_schema(schema)
        return schema

    def after_show(self, context, pkg_dict):
        if not context.get("use_cache", True):
            _translate_organization_and_groups(pkg_dict, context)
        _add_translated_pkg_fields(pkg_dict)
        return pkg_dict

    def after_search(self, results, search_params):
        for result in results["results"]:
            if tk.asbool(tk.config.get(CONFIG_TRANSLATED_SEARCH_GROUPS, DEFAULT_TRANSLATED_SEARCH_GROUPS)):
                _translate_organization_and_groups(result, {"ignore_auth": True})

            _add_translated_pkg_fields(result)

        if not tk.request:
            return results

        lang = tk.h.lang()
        for k in results["search_facets"]:
                if k not in ("groups", "organization"):
                    continue
                _translate_group_facets(results["search_facets"][k]["items"], lang)

        return results


class GroupValidateMixin:
    def validate(self, context, data_dict, schema, action):
        from ckanext.scheming.validation import convert_from_extras_group
        locales = tk.h.duo_offered_locales()
        if_empty_same_as = tk.get_validator("if_empty_same_as")
        convert_to_extras = tk.get_validator("convert_to_extras")
        ignore_missing = tk.get_validator("ignore_missing")

        if action.endswith("_show"):
            for locale in locales:
                schema[f"title_{locale}"] = [convert_from_extras_group, ignore_missing]
                schema[f"description_{locale}"] = [convert_from_extras_group, ignore_missing]
        else:
            for locale in locales:
                schema[f"title_{locale}"] = [if_empty_same_as("title"), convert_to_extras]
                schema[f"description_{locale}"] = [if_empty_same_as("description"), convert_to_extras]

        return tk.navl_validate(data_dict, schema, context)


class DuoOrganizationPlugin(GroupValidateMixin, plugins.SingletonPlugin, DefaultOrganizationForm):

    plugins.implements(plugins.IOrganizationController, inherit=True)
    plugins.implements(plugins.IConfigurer, inherit=True)

    plugins.implements(plugins.IGroupForm, inherit=True)

    def group_types(self):
        if tk.asbool(tk.config.get(CONFIG_MODIFY_ORGANIZATION_SCHEMA, DEFAULT_MODIFY_ORGANIZATION_SCHEMA)):
            return ["organization"]
        return []

    def is_fallback(self):
        return False


    def update_config(self, config_):
        if tk.asbool(tk.config.get(CONFIG_MODIFY_ORGANIZATION_SCHEMA, DEFAULT_MODIFY_ORGANIZATION_SCHEMA)):
            tk.add_template_directory(config_, "organization_templates")

    def before_view(self, data):
        return _group_translation(data)


class DuoGroupPlugin(GroupValidateMixin, plugins.SingletonPlugin, DefaultGroupForm):
    plugins.implements(plugins.IGroupController, inherit=True)
    plugins.implements(plugins.IConfigurer, inherit=True)

    plugins.implements(plugins.IGroupForm, inherit=True)

    def group_types(self):
        if tk.asbool(tk.config.get(CONFIG_MODIFY_GROUP_SCHEMA, DEFAULT_MODIFY_GROUP_SCHEMA)):
            return ["group"]
        return []

    def is_fallback(self):
        return False

    def update_config(self, config_):
        if tk.asbool(tk.config.get(CONFIG_MODIFY_GROUP_SCHEMA, DEFAULT_MODIFY_GROUP_SCHEMA)):
            tk.add_template_directory(config_, "group_templates")

    def before_view(self, data):
        return _group_translation(data)


def _group_translation(data):
    try:
        lang = tk.h.lang()
    except RuntimeError:
        return data

    extras =  data.get("extras", [])
    if not extras:
        extras = [
            {"key": extra.key, "value": extra.value}
            for extra in
            model.Session.query(model.GroupExtra).filter_by(group_id=data["id"])
        ]
    for extra in extras:
        if extra["key"] == f"title_{lang}":
            data["display_name"] = extra["value"]
            break

    return data


def _translate_group_facets(items: list[dict[str, Any]], lang: str):
    group_names = {item["name"] for item in items}
    if not group_names:
        return
    groups = model.Session.query(model.Group.name, model.GroupExtra.value).filter(
        model.Group.id == model.GroupExtra.group_id,
        model.Group.name.in_(group_names),
        model.GroupExtra.key == f"title_{lang}",
    )

    translated = dict(groups)

    for item in items:
        item["display_name"] = translated.get(item["name"], item["name"])


def _add_translated_pkg_fields(pkg_dict):
    fields = ["title", "notes"]

    for field in fields:
        if field not in pkg_dict:
            continue

        pkg_dict[f"{field}_translated"] = _get_translated(pkg_dict, field)


def _get_translated(data: dict[str, Any], field: str):
    locales = tk.h.duo_offered_locales()
    return {
        locale: data.get(
            f"{field}_{locale}",
            tk.h.get_pkg_dict_extra(data, f"{field}_{locale}", data[field])
        )
        for locale in locales
    }


def _translate_organization_and_groups(pkg_dict, context):
    if pkg_dict.get("owner_org"):
        org = tk.get_action("organization_show")(
            context.copy(), {"id": pkg_dict["owner_org"]}
        )
        pkg_dict["organization"]["title_translated"] = _get_translated(org, "title")
        pkg_dict["organization"]["description_translated"] = _get_translated(
            org, "description"
        )
    for group in pkg_dict.get("groups", []):
        group_data = tk.get_action("group_show")(context.copy(), {"id": group["id"]})
        group.update(group_data)
