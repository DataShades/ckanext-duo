from __future__ import annotations
from typing import Any

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
import ckan.model as model

from .signals import setup_listeners

class DuoPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    # IConfigurer

    def update_config(self, config_):
        setup_listeners()


class DuoDatasetPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IPackageController, inherit=True)

    def after_show(self, context, pkg_dict):
        if not context.get("use_cache", True) and pkg_dict["owner_org"]:
            org = tk.get_action("organization_show")(
                context.copy(), {"id": pkg_dict["owner_org"]}
            )
            pkg_dict["organization"]["title_translated"] = _get_translated(org, "title")
            pkg_dict["organization"]["description_translated"] = _get_translated(
                org, "description"
            )

        _add_translated_pkg_fields(pkg_dict)
        return pkg_dict

    def after_search(self, results, search_params):
        for result in results["results"]:
            _add_translated_pkg_fields(result)

        if not tk.request:
            return results

        lang = tk.h.lang()
        if lang != tk.config.get("ckan.locale_default", "en"):
            for k in results["search_facets"]:
                if k not in ("groups", "organization"):
                    continue
                _translate_group_facets(results["search_facets"][k]["items"], lang)

        return results


class DuoOrganizationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IOrganizationController, inherit=True)

    def before_view(self, data):
        return _group_translation(data)


class DuoGroupPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IGroupController, inherit=True)

    def before_view(self, data):
        return _group_translation(data)


def _group_translation(data):
    try:
        lang = tk.h.lang()
    except RuntimeError:
        return data

    if lang == tk.config.get("ckan.locale_default", "en"):
        return data

    for extra in data.get("extras", []):
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
    locales = tk.aslist(tk.config.get("ckan.locales_offered", "en"))
    return {
        locale: data.get(
            f"{field}_{locale}",
            tk.h.get_pkg_dict_extra(data, f"{field}_{locale}", data[field])
        )
        for locale in locales
    }
