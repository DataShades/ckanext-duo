from __future__ import annotations
from typing import Iterable

from flask.signals import before_render_template
import ckan.plugins.toolkit as tk

def setup_listeners():
    before_render_template.connect(organization_translator)


def organization_translator(sender, template, context):

    if template.name == "organization/snippets/organization_item.html":
        _translate(context.get("organization"), ["description"])

    elif template.name == "snippets/organization.html":
        _translate(context.get("organization"), ["description", "title"])

    elif template.name == "group/snippets/info.html":
        _translate(context.get("group"), ["description", "title"])

    elif template.name == "group/snippets/group_item.html":
        _translate(context.get("group"), ["description"])

    elif template.name == "snippets/package_item.html":
        pkg = context["package"]
        pkg["title"] = tk.h.get_translated(pkg, "title")
        pkg["notes"] = tk.h.get_translated(pkg, "notes")


def _translate(data, fields: Iterable[str]):
    if not data:
        return

    lang = tk.h.lang()
    for field in fields:
        if field not in data:
            continue

        data[field] = data.get(
            f"{field}_{lang}",
            tk.h.get_pkg_dict_extra(data, f"{field}_{lang}", data[field])
        )
