"""Provider-neutral affiliate commerce layer.

Network adapters normalize provider-specific offers into one internal record.
No provider credentials or fabricated tracking URLs are stored in this module.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterable, Protocol
from urllib.parse import urlparse


@dataclass(frozen=True)
class AffiliateOffer:
    provider: str
    offer_id: str
    site_id: str
    title: str
    destination_url: str
    affiliate_url: str
    image_url: str
    category: str
    keywords: tuple[str, ...] = ()
    currency: str = ""
    price: str = ""
    availability: str = "unknown"
    popularity_evidence: str = ""
    creative_source: str = ""
    verified: bool = False

    def validate(self) -> None:
        if not self.provider or not self.offer_id or not self.site_id or not self.title:
            raise ValueError("provider, offer_id, site_id and title are required")
        for field in ("destination_url", "affiliate_url", "image_url"):
            value = getattr(self, field)
            parsed = urlparse(value)
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError(f"{field} must be an absolute HTTPS URL")
        if not self.verified:
            raise ValueError("Only verified, account-authorized affiliate offers may be published")


class AffiliateProvider(Protocol):
    provider_id: str

    def search(self, query: str, **kwargs: Any) -> list[AffiliateOffer]: ...
    def create_tracking_link(self, destination_url: str, **kwargs: Any) -> str: ...


class ManualPortalProvider:
    """Portal-assisted provider: links are captured from the logged-in partner portal.

    Browser-only portals must not be scraped or treated as API access. The capture
    adapter accepts a confirmed link + official creative supplied by the portal.
    """

    def __init__(self, provider_id: str, allowed_hosts: tuple[str, ...]):
        self.provider_id = provider_id
        self.allowed_hosts = allowed_hosts

    def normalize_capture(self, record: dict[str, Any], site_id: str) -> AffiliateOffer:
        offer = AffiliateOffer(
            provider=self.provider_id,
            offer_id=str(record.get("offer_id") or record.get("product_id") or record.get("affiliate_url") or ""),
            site_id=site_id,
            title=str(record.get("title") or "").strip(),
            destination_url=str(record.get("destination_url") or record.get("product_url") or ""),
            affiliate_url=str(record.get("affiliate_url") or ""),
            image_url=str(record.get("image_url") or ""),
            category=str(record.get("category") or "general"),
            keywords=tuple(record.get("keywords") or ()),
            currency=str(record.get("currency") or ""),
            price=str(record.get("price") or ""),
            availability=str(record.get("availability") or "unknown"),
            popularity_evidence=str(record.get("popularity_evidence") or ""),
            creative_source=str(record.get("creative_source") or "partner_portal"),
            verified=record.get("verified") is True,
        )
        offer.validate()
        host = urlparse(offer.affiliate_url).netloc.lower()
        if not any(host == h or host.endswith("." + h) for h in self.allowed_hosts):
            raise ValueError(f"affiliate URL host is not approved for {self.provider_id}: {host}")
        return offer

    def search(self, query: str, **kwargs: Any) -> list[AffiliateOffer]:
        raise NotImplementedError("This provider requires its authorized partner portal or approved product feed")

    def create_tracking_link(self, destination_url: str, **kwargs: Any) -> str:
        raise NotImplementedError("Tracking links must be created by the provider's official portal/API")


class AffiliateProviderRegistry:
    def __init__(self):
        self._providers: dict[str, AffiliateProvider] = {}

    def register(self, provider: AffiliateProvider) -> None:
        key = provider.provider_id.lower()
        if key in self._providers:
            raise ValueError(f"Provider already registered: {key}")
        self._providers[key] = provider

    def get(self, provider_id: str) -> AffiliateProvider:
        return self._providers[provider_id.lower()]

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))


def offers_to_records(offers: Iterable[AffiliateOffer]) -> list[dict[str, Any]]:
    records = []
    for offer in offers:
        offer.validate()
        records.append(asdict(offer))
    return records


def load_provider_registry(path: str) -> AffiliateProviderRegistry:
    """Load only adapter declarations; credentials are always environment secrets."""
    import json
    from pathlib import Path

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    registry = AffiliateProviderRegistry()
    for item in data.get("providers", []):
        if item.get("adapter") == "manual_portal":
            registry.register(ManualPortalProvider(
                item["id"], tuple(item.get("allowed_affiliate_hosts", []))
            ))
    return registry
