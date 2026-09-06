"""A domain's code lives on Bitbucket or GitHub — either satisfies registration.

Registration demanded a Bitbucket coordinate, which made GitHub-hosted teams
unable to create a domain at all. The requirement itself is kept: a domain with
no repository anywhere has nothing to onboard. Only its Bitbucket-specificity
went.
"""
from __future__ import annotations

import pytest

from src.services import domain_service


@pytest.fixture
def registered(monkeypatch):
    """A tracker double that records what registration was handed."""
    calls = {}

    class Tracker:
        def get_product(self, name):
            return {"name": name} if name == "ACME" else None

        def get_domain(self, slug):
            return None

        def register_domain(self, **kwargs):
            calls.update(kwargs)
            return 1

        def record_activity(self, **kwargs):
            pass

    monkeypatch.setattr(domain_service, "_tracker", lambda: Tracker())
    monkeypatch.setattr(domain_service, "get_domain_detail",
                        lambda slug: domain_service.DomainDetail(
                            name=slug, product="ACME", domain="X"))
    return calls


class TestEitherHostIsAccepted:
    @pytest.mark.parametrize("field", [
        "bitbucket_project", "bitbucket_url", "github_org", "github_url",
    ])
    def test_any_single_coordinate_registers(self, registered, field):
        domain_service.create_domain(domain="X", product="ACME", **{field: "value"})
        assert registered[field] == "value"

    def test_github_alone_is_enough(self, registered):
        """The case that was impossible before."""
        domain_service.create_domain(domain="X", product="ACME", github_org="acme")
        assert registered["github_org"] == "acme"
        assert not registered.get("bitbucket_project")

    def test_both_hosts_together_are_fine(self, registered):
        domain_service.create_domain(domain="X", product="ACME",
                                     bitbucket_project="CGF", github_org="acme")
        assert registered["bitbucket_project"] == "CGF"
        assert registered["github_org"] == "acme"


class TestSomeCoordinateIsStillRequired:
    def test_no_coordinate_is_refused(self, registered):
        with pytest.raises(ValueError) as excinfo:
            domain_service.create_domain(domain="X", product="ACME")
        message = str(excinfo.value)
        # The message has to name both hosts now — pointing a GitHub user at
        # Bitbucket is what made this look like a missing feature.
        assert "Bitbucket" in message and "GitHub" in message

    def test_whitespace_is_not_a_coordinate(self, registered):
        with pytest.raises(ValueError):
            domain_service.create_domain(domain="X", product="ACME",
                                         github_org="   ", bitbucket_url="  ")

    def test_an_unknown_product_still_fails_first(self, registered):
        with pytest.raises(ValueError) as excinfo:
            domain_service.create_domain(domain="X", product="NOPE",
                                         github_org="acme")
        assert "not found" in str(excinfo.value)
