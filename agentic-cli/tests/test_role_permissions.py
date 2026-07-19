"""Tests for the role-activity permission review additions."""

from agentic_cli.auth.models import (
    ADMIN,
    DEVELOPER,
    MAINTAINER,
    PERM_PLATFORM_CONFIGURE,
    PERM_REQUIREMENTS_PUSH,
    VIEWER,
    Principal,
    permissions_for,
)


def test_requirements_push_granted_developer_and_up():
    assert PERM_REQUIREMENTS_PUSH not in permissions_for([VIEWER])
    assert PERM_REQUIREMENTS_PUSH in permissions_for([DEVELOPER])
    assert PERM_REQUIREMENTS_PUSH in permissions_for([MAINTAINER])
    assert Principal(subject="a", roles=[ADMIN]).has(PERM_REQUIREMENTS_PUSH)


def test_platform_configure_granted_maintainer_and_up():
    assert PERM_PLATFORM_CONFIGURE not in permissions_for([VIEWER])
    assert PERM_PLATFORM_CONFIGURE not in permissions_for([DEVELOPER])
    assert PERM_PLATFORM_CONFIGURE in permissions_for([MAINTAINER])
    assert Principal(subject="a", roles=[ADMIN]).has(PERM_PLATFORM_CONFIGURE)


def test_viewer_still_has_no_permissions():
    assert permissions_for([VIEWER]) == set()
