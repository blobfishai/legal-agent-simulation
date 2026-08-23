"""Canonical domain/resource catalog shared by v21 builders and checks.

The catalog deliberately describes synthetic workflow fixtures.  It models
common legal-operations concepts without claiming compatibility with a named
commercial product or making jurisdiction-specific legal conclusions.
"""
from __future__ import annotations

from typing import Final


DOMAIN_RESOURCES: Final[tuple[dict, ...]] = (
    {
        "key": "litigation", "prefix": "lt", "label": "Litigation",
        "resources": ("matters", "parties", "claims", "pleadings", "motions",
                      "discovery_requests", "depositions", "exhibits", "settlements"),
    },
    {
        "key": "corporate", "prefix": "cg", "label": "Corporate Governance",
        "resources": ("entities", "directors", "officers", "board_meetings", "resolutions",
                      "consents", "subsidiaries", "securities", "minute_books"),
    },
    {
        "key": "contracts", "prefix": "cc", "label": "Commercial Contracts",
        "resources": ("agreements", "counterparties", "clauses", "obligations", "renewals",
                      "amendments", "approvals", "notices", "playbooks"),
    },
    {
        "key": "employment", "prefix": "el", "label": "Employment and Labor",
        "resources": ("employees", "complaints", "investigations", "interviews",
                      "accommodations", "leaves", "discipline_actions", "separations", "policies"),
    },
    {
        "key": "privacy", "prefix": "pv", "label": "Privacy",
        "resources": ("processing_activities", "data_subject_requests", "consents", "assessments",
                      "vendors", "transfers", "incidents", "notices", "retention_rules"),
    },
    {
        "key": "cybersecurity", "prefix": "cy", "label": "Cybersecurity Response",
        "resources": ("security_incidents", "affected_assets", "forensic_images", "indicators",
                      "containment_actions", "notifications", "response_tasks", "vendors", "postmortems"),
    },
    {
        "key": "intellectual_property", "prefix": "ip", "label": "Intellectual Property",
        "resources": ("trademarks", "patents", "copyrights", "licenses", "office_actions",
                      "renewals", "assignments", "infringements", "portfolios"),
    },
    {
        "key": "real_estate", "prefix": "re", "label": "Real Estate",
        "resources": ("properties", "leases", "tenants", "landlords", "estoppels", "title_items",
                      "diligence_requests", "closings", "obligations"),
    },
    {
        "key": "tax", "prefix": "tx", "label": "Tax Controversy",
        "resources": ("taxpayers", "returns", "audits", "adjustments", "notices", "protests",
                      "authorities", "deadlines", "payments"),
    },
    {
        "key": "bankruptcy", "prefix": "bk", "label": "Bankruptcy",
        "resources": ("debtors", "creditors", "claims", "schedules", "motions", "orders", "plans",
                      "ballots", "distributions"),
    },
    {
        "key": "antitrust", "prefix": "at", "label": "Antitrust",
        "resources": ("transactions", "markets", "competitors", "hsr_filings", "second_requests",
                      "custodians", "productions", "remedies", "agency_contacts"),
    },
    {
        "key": "healthcare", "prefix": "hc", "label": "Healthcare Regulatory",
        "resources": ("providers", "facilities", "licenses", "payor_contracts", "claims_audits",
                      "compliance_events", "disclosures", "investigations", "corrective_actions"),
    },
    {
        "key": "environmental", "prefix": "en", "label": "Environmental",
        "resources": ("facilities", "permits", "emissions", "spills", "inspections", "notices",
                      "remediation_projects", "sampling_events", "agency_filings"),
    },
    {
        "key": "financial_services", "prefix": "fs", "label": "Financial Services",
        "resources": ("institutions", "products", "complaints", "examinations", "findings",
                      "suspicious_activities", "disclosures", "controls", "remediation_items"),
    },
    {
        "key": "investment_funds", "prefix": "fm", "label": "Investment Funds",
        "resources": ("funds", "investors", "subscriptions", "side_letters", "valuations", "trades",
                      "compliance_tests", "filings", "distributions"),
    },
    {
        "key": "insurance", "prefix": "in", "label": "Insurance Coverage",
        "resources": ("policies", "insureds", "claims", "coverage_positions", "reservations",
                      "adjusters", "demands", "settlements", "subrogations"),
    },
    {
        "key": "immigration", "prefix": "im", "label": "Business Immigration",
        "resources": ("beneficiaries", "petitions", "filings", "notices", "evidence_requests",
                      "interviews", "expirations", "employers", "dependents"),
    },
    {
        "key": "trusts_estates", "prefix": "te", "label": "Trusts and Estates",
        "resources": ("estates", "trusts", "fiduciaries", "beneficiaries", "assets", "distributions",
                      "accountings", "tax_filings", "court_petitions"),
    },
    {
        "key": "nonprofit", "prefix": "np", "label": "Nonprofit Governance",
        "resources": ("organizations", "directors", "grants", "donations", "restrictions", "conflicts",
                      "filings", "programs", "minutes"),
    },
    {
        "key": "government_contracts", "prefix": "gc", "label": "Government Contracts",
        "resources": ("solicitations", "bids", "awards", "clauses", "modifications", "deliverables",
                      "invoices", "audits", "protests"),
    },
    {
        "key": "product_safety", "prefix": "ps", "label": "Product Safety",
        "resources": ("products", "incidents", "complaints", "tests", "hazards", "recalls", "reports",
                      "corrective_actions", "notices"),
    },
    {
        "key": "investigations", "prefix": "iv", "label": "Internal Investigations",
        "resources": ("matters", "allegations", "witnesses", "interviews", "evidence_items", "holds",
                      "findings", "referrals", "reports"),
    },
)

OPERATIONS: Final[tuple[str, ...]] = ("list", "get", "search", "create", "update")
JURISDICTIONS: Final[tuple[str, ...]] = ("CA", "NY", "TX", "FL", "IL", "DC", "DE", "WA")
RISK_LEVELS: Final[tuple[str, ...]] = ("critical", "high", "medium", "low")
OWNERS: Final[tuple[str, ...]] = (
    "lead-counsel", "senior-associate", "legal-operations", "compliance-counsel",
    "privacy-counsel", "litigation-support", "docketing", "matter-manager",
)


def table_name(domain: dict, resource: str) -> str:
    return f"v21_{domain['prefix']}_{resource}"


def tool_name(domain: dict, resource: str, operation: str) -> str:
    return f"{domain['key']}_{resource}_{operation}"


def resource_label(resource: str) -> str:
    return resource.replace("_", " ").title()


def iter_resources():
    for domain in DOMAIN_RESOURCES:
        for resource in domain["resources"]:
            yield domain, resource


def iter_tools():
    for domain, resource in iter_resources():
        for operation in OPERATIONS:
            yield domain, resource, operation, tool_name(domain, resource, operation)


assert len(DOMAIN_RESOURCES) == 22
assert sum(len(domain["resources"]) for domain in DOMAIN_RESOURCES) == 198
assert sum(1 for _ in iter_tools()) == 990
