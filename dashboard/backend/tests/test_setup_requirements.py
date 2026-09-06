"""What the setup wizard calls required — and what it must stop calling required.

Vertex AI was flagged `required=True` while the local runtime and the built-in
model were optional, so a working Ollama install still read as "not ready" and
pointed the user at a Google Cloud project they did not need. The wizard's own
blurb and its `stepState` had always said any one of the three was enough; only
the flag disagreed.

Dropping the flag alone would have made "ready" stop checking for a model at
all, so the group is what keeps it honest. Both halves are pinned here.
"""
from __future__ import annotations

import pytest

from src.services.setup_service import (
    REQUIRED_GROUPS,
    SetupItem,
    _requirements_met,
    get_setup_status,
)


def _item(key, configured, required=False, group=""):
    return SetupItem(key=key, label=key, configured=configured,
                     required=required, group=group)


def _model_items(vertex=False, local=False, builtin=False):
    return [
        _item("vertex_ai", vertex, group="model"),
        _item("local_model", local, group="model"),
        _item("builtin_model", builtin, group="model"),
    ]


WORKSPACES = _item("workspaces", True, required=True)


class TestAnyModelSatisfies:
    @pytest.mark.parametrize("kwargs,label", [
        ({"vertex": True}, "vertex"),
        ({"local": True}, "ollama"),
        ({"builtin": True}, "built-in"),
    ])
    def test_one_provider_is_enough(self, kwargs, label):
        assert _requirements_met([WORKSPACES, *_model_items(**kwargs)]), label

    def test_no_provider_is_not_enough(self):
        """The group still requires *a* model — silence is not readiness."""
        assert not _requirements_met([WORKSPACES, *_model_items()])

    def test_vertex_is_no_longer_individually_required(self):
        """The bug: a local-model user could never reach ready."""
        status_items = get_setup_status().items
        vertex = next(i for i in status_items if i.key == "vertex_ai")
        assert vertex.required is False
        assert vertex.group == "model"

    def test_all_three_share_one_group(self):
        keys = {i.key for i in get_setup_status().items if i.group == "model"}
        assert keys == {"vertex_ai", "local_model", "builtin_model"}

    def test_an_individually_required_item_still_blocks(self):
        """Groups relax one requirement; they do not relax the others."""
        assert not _requirements_met(
            [_item("workspaces", False, required=True), *_model_items(local=True)])

    def test_a_group_nobody_declares_does_not_block(self):
        """An older status payload with no grouped items must not deadlock."""
        assert _requirements_met([WORKSPACES])

    def test_the_model_group_is_the_declared_one(self):
        assert "model" in REQUIRED_GROUPS


class TestCodeHostIntegrations:
    def test_github_is_offered_beside_bitbucket(self):
        keys = {i.key for i in get_setup_status().items}
        assert {"bitbucket", "github"} <= keys

    def test_neither_code_host_is_mandatory_in_the_wizard(self):
        """Setup lists them as integrations; domain creation is where one is needed."""
        items = {i.key: i for i in get_setup_status().items}
        assert items["bitbucket"].required is False
        assert items["github"].required is False
