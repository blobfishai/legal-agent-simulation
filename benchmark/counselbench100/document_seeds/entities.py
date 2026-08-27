"""Entity detection, deterministic re-skinning, and rubric-literal scrubbing.

A seed document is only useful if every fact in it can be replaced: the
parties, the people, the dates, the amounts, the case numbers. This module
finds those spans with plain regexes, builds a consistent substitution map
from a seeded RNG (or from values the caller supplies), and guarantees that a
caller-provided ``avoid`` list never survives — the mechanism that keeps seed
prose from satisfying a rubric criterion or tripping a forbid trap.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, timedelta
from random import Random

_LEGAL_SUFFIX = r"(?i:Inc\.?|LLC|L\.L\.C\.|LLP|L\.L\.P\.|Ltd\.?|Limited|Corp\.?|Corporation|Company|Co\.|L\.P\.|LP\b|PLC|GmbH|S\.A\.|N\.V\.|B\.V\.|AG\b|S\.p\.A\.|Pty\b|Pte\b|Incorporated|N\.A\.)"
_DESCRIPTIVE_SUFFIX = r"(?:Holdings|Partners|Group|Trust|Bank|Fund(?:\s+[IVX]+)?|Associates|Ventures|Capital|Advisors|Advisory|Technologies|Systems|Solutions|Industries|Enterprises|Foundation|Institute|University|Hospital|Insurance|Realty|Properties|Logistics|Labs|Therapeutics|Pharmaceuticals|Biosciences|Energy|Networks|Software|Services|Health|Healthcare|Medical|Manufacturing|International|Global|Worldwide|Authority|Commission|Agency|District|Department)"
_ORG_SUFFIX = r"(?:" + _LEGAL_SUFFIX + r"|" + _DESCRIPTIVE_SUFFIX + r")"
_LEADING_STOP = {
    "Via",
    "The",
    "By",
    "Of",
    "For",
    "And",
    "To",
    "In",
    "On",
    "At",
    "With",
    "From",
    "Between",
    "Among",
    "Each",
    "Any",
    "All",
    "Both",
    "This",
    "That",
    "Such",
    "Other",
    "Our",
    "Their",
    "Its",
    "Whether",
    "Neither",
    "Either",
    "Under",
    "Per",
    "See",
    "Re",
    "Dear",
    "Subject",
    "Attention",
    "Attn",
    "County",
    "City",
    "State",
    "Sincerely",
    "Regards",
    "Thanks",
    "Please",
    "Note",
    "Notes",
    "Section",
    "Article",
    "Exhibit",
    "Schedule",
    "Annex",
    "Appendix",
}
_ORG = re.compile(
    r"\b((?:[A-Z][A-Za-z0-9&'’\-]*[ \u00a0]+){0,4}[A-Z][A-Za-z0-9&'’\-]*(?:,)?[ \u00a0]+"
    + _ORG_SUFFIX
    + r")(?![A-Za-z])"
)
_MONEY = re.compile(
    r"(?:US)?\$\s?\d{1,3}(?:,\d{3})+(?:\.\d{2})?|(?:US)?\$\s?\d+(?:\.\d{1,2})?(?:\s?(?:million|billion|thousand|MM|M|K|B))?\b"
)
_PERCENT = re.compile(r"\b\d{1,3}(?:\.\d{1,2})?\s?(?:%|percent)")
_LONG_DATE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b"
)
_ISO_DATE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
_NUMERIC_DATE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b")
_DOCKET = re.compile(
    r"\b(?:No\.|Case No\.|Docket No\.|Civil Action No\.)\s*[A-Z0-9][A-Z0-9:\-/]{3,}\b"
)
_EMAIL = re.compile(r"\b[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}\b", re.I)
# Superset of the publish scrubber's phone shapes; replacements land in the
# NANPA fictional block (555-0100..0199) and e-mails on the reserved
# ``.example`` TLD, so seeded prose is publishable by construction.
_PHONE = re.compile(
    r"(?<!\d)(?:\+1[ .-]?(?:\d{3}|\(\d{3}\))[ .-]?\d{3}[ .-]?\d{4}|\(\d{3}\)[ .-]?\d{3}[ .-]?\d{4}|\d{3}[-.]\d{3}[-.]\d{4})(?!\d)"
)
_ADDRESS = re.compile(
    r"\b\d{2,5}\s+(?:[A-Z][a-z]+\s+){1,3}(?:Street|St\.|Avenue|Ave\.|Boulevard|Blvd\.|Road|Rd\.|Drive|Dr\.|Lane|Ln\.|Way|Place|Plaza|Parkway|Pkwy|Court|Ct\.|Suite\s+\d+)\b"
)
_DEFINED_TERM = re.compile(r"[\"“]([A-Z][A-Za-z\-\s]{1,40})[\"”]")

_COMMON_WORDS = {
    "The",
    "This",
    "That",
    "These",
    "Those",
    "Each",
    "Any",
    "All",
    "Both",
    "Such",
    "Other",
    "Agreement",
    "Section",
    "Article",
    "Party",
    "Parties",
    "Company",
    "Customer",
    "Provider",
    "Supplier",
    "Buyer",
    "Seller",
    "Lender",
    "Borrower",
    "Landlord",
    "Tenant",
    "Employer",
    "Employee",
    "Executive",
    "Client",
    "Counsel",
    "Board",
    "Committee",
    "Effective",
    "Date",
    "Term",
    "Services",
    "Confidential",
    "Information",
    "Business",
    "Day",
    "Days",
    "State",
    "United",
    "States",
    "District",
    "Court",
    "Northern",
    "Southern",
    "Eastern",
    "Western",
    "New",
    "York",
    "Delaware",
    "California",
    "Texas",
    "Governing",
    "Law",
    "Notice",
    "Notices",
    "Exhibit",
    "Schedule",
    "Annex",
    "Appendix",
    "Page",
    "Total",
    "Annual",
    "Fee",
    "Fees",
    "Base",
    "Data",
    "Transfer",
    "Managed",
    "Security",
    "Service",
    "Level",
    "Statement",
    "Work",
    "Master",
    "Subject",
    "Matter",
    "Chief",
    "Executive",
    "Officer",
    "General",
    "Vice",
    "President",
    "Senior",
    "Managing",
    "Director",
    "Partner",
    "Limited",
    "Liability",
    "Corporation",
    "Holdings",
    "Group",
    "Capital",
    "Partners",
    "Trust",
    "Bank",
    "Fund",
    "Inc",
    "LLC",
    "LLP",
    "Ltd",
    "Corp",
    "Co",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Dear",
    "Sincerely",
    "Regards",
    "Best",
    "Thank",
    "Thanks",
    "Please",
    "Subject",
    "From",
    "Sent",
    "To",
    "Cc",
    "Re",
    "Attorney",
    "Work",
    "Product",
    "Privileged",
    "Draft",
    "Final",
    "Version",
    "Prepared",
    "Reviewed",
    "Approved",
    "Internal",
    "External",
    "Use",
    "Only",
    "Not",
    "For",
    "Distribution",
    "Confidentiality",
    "Purchase",
    "Price",
    "Closing",
    "Escrow",
    "Amount",
    "Payment",
    "Payments",
    "Interest",
    "Rate",
    "Credit",
    "Loan",
    "Facility",
    "Revolving",
    "Termination",
    "Change",
    "Control",
    "Assignment",
    "Consent",
    "Indemnification",
    "Limitation",
    "Liability",
    "Warranty",
    "Warranties",
    "Representations",
    "Covenants",
    "Miscellaneous",
    "Definitions",
    "Recitals",
    "Whereas",
    "Now",
    "Therefore",
    "Witness",
    "Whereof",
    "Signature",
    "Name",
    "Title",
    "By",
    "Its",
    "Infrastructure",
    "Hosting",
    "Professional",
    "Cloud",
    "Related",
    "Additional",
    "Ancillary",
    "Support",
    "Maintenance",
    "Consulting",
    "Certain",
    "Applicable",
    "Comparable",
    "Reorganized",
    "Force",
    "Majeure",
    "Availability",
    "Target",
    "Direct",
    "Competitor",
    "Chronic",
    "Failure",
    "Cumulative",
    "Distributions",
    "Trailing",
    "Cash",
    "Sweep",
    "Low",
    "High",
    "Merchant",
    "Rights",
    "Offering",
    "Equity",
    "Grand",
    "Real",
    "Commercial",
    "Residential",
    "Fruit",
    "Month",
    "Year",
    "Quarter",
    "Week",
    "Gross",
    "Net",
    "Revenue",
    "Operating",
    "Working",
    "Initial",
    "Final",
    "First",
    "Second",
    "Third",
    "Fourth",
    "Last",
    "Next",
    "Prior",
    "Material",
    "Adverse",
    "Effect",
    "Intellectual",
    "Property",
    "Personal",
    "Public",
    "Private",
    "Preferred",
    "Common",
    "Stock",
    "Shares",
    "Units",
    "Option",
    "Options",
    "Warrant",
    "Restricted",
    "Vesting",
    "Exercise",
    "Fair",
    "Market",
    "Value",
    "Book",
    "Cost",
    "Basis",
    "Tax",
    "Taxes",
    "Income",
    "Loss",
    "Losses",
    "Damages",
    "Claim",
    "Claims",
    "Action",
    "Actions",
    "Proceeding",
    "Proceedings",
    "Governmental",
    "Regulatory",
    "Compliance",
    "Environmental",
    "Health",
    "Safety",
    "Security",
    "Privacy",
    "Breach",
    "Default",
    "Event",
    "Events",
    "Cure",
    "Period",
    "Remedy",
    "Remedies",
    "Force",
    "Reasonable",
    "Best",
    "Efforts",
    "Good",
    "Faith",
    "Ordinary",
    "Course",
}

US_STATES = (
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "Hampshire",
    "Jersey",
    "Mexico",
    "York",
    "Carolina",
    "Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode",
    "Island",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "Wisconsin",
    "Wyoming",
    "Columbia",
    "Puerto",
    "Rico",
    "Ontario",
    "Quebec",
    "London",
    "England",
    "Wales",
    "Scotland",
    "Ireland",
    "Canada",
    "Europe",
    "European",
    "America",
    "American",
    "Asia",
    "Pacific",
    "Atlantic",
    "Central",
    "National",
    "Federal",
    "Municipal",
    "Regional",
    "Operations",
    "Operating",
    "Management",
    "Managed",
    "Strategic",
    "Global",
    "International",
    "Universal",
    "General",
    "Standard",
    "Premier",
    "Premium",
    "Advanced",
    "Applied",
    "Integrated",
    "United",
    "Allied",
)
_COMMON_WORDS.update(US_STATES)

FIRST_NAME_LEXICON = frozenset(
    (
        "Aaron",
        "Abigail",
        "Adam",
        "Adaeze",
        "Adrian",
        "Aisha",
        "Alan",
        "Albert",
        "Alex",
        "Alexander",
        "Alexandra",
        "Alice",
        "Alison",
        "Allison",
        "Amanda",
        "Amy",
        "Ana",
        "Andrea",
        "Andrew",
        "Angela",
        "Anita",
        "Ann",
        "Anna",
        "Anne",
        "Anthony",
        "Arthur",
        "Ashley",
        "Audrey",
        "Barbara",
        "Beatrice",
        "Benjamin",
        "Bernard",
        "Beth",
        "Betty",
        "Bill",
        "Bonnie",
        "Brandon",
        "Brenda",
        "Brian",
        "Bruce",
        "Caleb",
        "Cameron",
        "Carl",
        "Carla",
        "Carlos",
        "Carol",
        "Caroline",
        "Catherine",
        "Celeste",
        "Charles",
        "Charlotte",
        "Chloe",
        "Chris",
        "Christina",
        "Christine",
        "Christopher",
        "Claire",
        "Clara",
        "Colin",
        "Craig",
        "Cynthia",
        "Dana",
        "Daniel",
        "Danielle",
        "Darren",
        "David",
        "Dawn",
        "Deborah",
        "Denise",
        "Dennis",
        "Derek",
        "Desmond",
        "Diana",
        "Diane",
        "Dominic",
        "Donald",
        "Donna",
        "Dorothy",
        "Douglas",
        "Edward",
        "Eileen",
        "Elaine",
        "Eleanor",
        "Elena",
        "Elizabeth",
        "Ellen",
        "Emily",
        "Emma",
        "Eric",
        "Erica",
        "Erin",
        "Ethan",
        "Eugene",
        "Eva",
        "Evan",
        "Evelyn",
        "Everett",
        "Fatima",
        "Felix",
        "Fiona",
        "Frances",
        "Francis",
        "Frank",
        "Franklin",
        "Frederick",
        "Gabriel",
        "Gary",
        "George",
        "Gerald",
        "Gloria",
        "Grace",
        "Grayson",
        "Gregory",
        "Hannah",
        "Harold",
        "Harry",
        "Heather",
        "Helen",
        "Helena",
        "Henry",
        "Holly",
        "Howard",
        "Ian",
        "Imani",
        "Ingrid",
        "Irene",
        "Isaac",
        "Isabel",
        "Isabella",
        "Jack",
        "Jacob",
        "Jacqueline",
        "James",
        "Jane",
        "Janet",
        "Janice",
        "Jason",
        "Jean",
        "Jeffrey",
        "Jennifer",
        "Jeremy",
        "Jerome",
        "Jessica",
        "Jill",
        "Joan",
        "Joanna",
        "Joel",
        "John",
        "Jonathan",
        "Jordan",
        "Jose",
        "Joseph",
        "Joshua",
        "Joyce",
        "Juan",
        "Judith",
        "Judy",
        "Julia",
        "Julian",
        "Julie",
        "Justin",
        "Karen",
        "Katherine",
        "Kathleen",
        "Kathryn",
        "Katie",
        "Keith",
        "Kelly",
        "Kenji",
        "Kenneth",
        "Kevin",
        "Kimberly",
        "Kyle",
        "Larry",
        "Laura",
        "Lauren",
        "Lawrence",
        "Leah",
        "Leila",
        "Leonard",
        "Leslie",
        "Linda",
        "Lisa",
        "Lorraine",
        "Louis",
        "Lucas",
        "Lucy",
        "Luis",
        "Lydia",
        "Lynn",
        "Madeline",
        "Malcolm",
        "Marcus",
        "Margaret",
        "Margot",
        "Maria",
        "Marie",
        "Marilyn",
        "Marion",
        "Mark",
        "Martha",
        "Martin",
        "Mary",
        "Matthew",
        "Maureen",
        "Maya",
        "Megan",
        "Melanie",
        "Melissa",
        "Meredith",
        "Michael",
        "Michelle",
        "Miguel",
        "Mildred",
        "Miriam",
        "Mitchell",
        "Monica",
        "Nadia",
        "Nancy",
        "Naomi",
        "Natalie",
        "Nathan",
        "Nathaniel",
        "Neil",
        "Nicholas",
        "Nicole",
        "Noah",
        "Nora",
        "Norman",
        "Oliver",
        "Olivia",
        "Omar",
        "Oscar",
        "Owen",
        "Pamela",
        "Patricia",
        "Patrick",
        "Paul",
        "Paula",
        "Peter",
        "Philip",
        "Phyllis",
        "Priya",
        "Rachel",
        "Rafael",
        "Ralph",
        "Randall",
        "Raymond",
        "Rebecca",
        "Regina",
        "Richard",
        "Rita",
        "Robert",
        "Roberta",
        "Robin",
        "Roger",
        "Ronald",
        "Ronan",
        "Rosa",
        "Rose",
        "Roy",
        "Ruth",
        "Ryan",
        "Sally",
        "Samantha",
        "Samuel",
        "Sandra",
        "Sara",
        "Sarah",
        "Scott",
        "Sean",
        "Sebastian",
        "Sharon",
        "Shirley",
        "Simon",
        "Simone",
        "Sophia",
        "Stanley",
        "Stephanie",
        "Stephen",
        "Steven",
        "Susan",
        "Sylvia",
        "Tamara",
        "Teresa",
        "Terry",
        "Tessa",
        "Theodore",
        "Theresa",
        "Thomas",
        "Timothy",
        "Tina",
        "Todd",
        "Tomas",
        "Tracy",
        "Travis",
        "Valerie",
        "Vanessa",
        "Veronica",
        "Victor",
        "Victoria",
        "Vincent",
        "Virginia",
        "Vivian",
        "Walter",
        "Wanda",
        "Warren",
        "Wayne",
        "Wendy",
        "William",
        "Yolanda",
        "Yuki",
        "Zachary",
        "Zoe",
        "Aditya",
        "Ahmed",
        "Akira",
        "Amara",
        "Anjali",
        "Arjun",
        "Bao",
        "Chen",
        "Dmitri",
        "Elif",
        "Emeka",
        "Farah",
        "Hiroshi",
        "Ibrahim",
        "Ivan",
        "Jin",
        "Kwame",
        "Lakshmi",
        "Li",
        "Mei",
        "Ngozi",
        "Nikolai",
        "Noor",
        "Ravi",
        "Rohan",
        "Sanjay",
        "Sofia",
        "Tariq",
        "Wei",
        "Xiao",
        "Yara",
        "Yusuf",
        "Zara",
        "Zhang",
        "Rachel",
        "Grayson",
        "Harold",
        "Sandra",
    )
)
_TITLES = {"Mr.", "Ms.", "Mrs.", "Dr.", "Hon.", "Prof.", "Judge"}

FIRST_NAMES = (
    "Alexandra",
    "Marcus",
    "Priya",
    "Daniel",
    "Elena",
    "Jonathan",
    "Naomi",
    "Victor",
    "Hannah",
    "Rafael",
    "Ingrid",
    "Thomas",
    "Leila",
    "Gregory",
    "Simone",
    "Andrew",
    "Beatrice",
    "Kenji",
    "Olivia",
    "Samuel",
    "Fatima",
    "Nathaniel",
    "Rosa",
    "Desmond",
    "Clara",
    "Julian",
    "Meredith",
    "Omar",
    "Vivian",
    "Patrick",
    "Adaeze",
    "Lucas",
    "Helena",
    "Miguel",
    "Tessa",
    "Ronan",
    "Yuki",
    "Bernard",
    "Celeste",
    "Dominic",
    "Aisha",
    "Franklin",
    "Margot",
    "Theodore",
    "Imani",
    "Sebastian",
    "Lorraine",
    "Caleb",
    "Nadia",
    "Everett",
)
LAST_NAMES = (
    "Whitfield",
    "Okafor",
    "Lindqvist",
    "Marchetti",
    "Delacroix",
    "Tanaka",
    "Abernathy",
    "Castellanos",
    "Hargrove",
    "Nakamura",
    "Villanueva",
    "Pemberton",
    "Oyelaran",
    "Fitzgerald",
    "Kowalski",
    "Brennan",
    "Sorensen",
    "Aldana",
    "Mbeki",
    "Halvorsen",
    "Quintero",
    "Radcliffe",
    "Ishikawa",
    "Beaumont",
    "Stavros",
    "Wexler",
    "Adeyemi",
    "Corrigan",
    "Montgomery",
    "Petrov",
    "Sandoval",
    "Thackeray",
    "Vasquez",
    "Winslow",
    "Ferreira",
    "Galloway",
    "Haddad",
    "Ivarsson",
    "Jankowski",
    "Kellerman",
    "Lachance",
    "Moreau",
    "Nwachukwu",
    "Ostrowski",
    "Prescott",
    "Rasmussen",
    "Salazar",
    "Tremblay",
    "Underwood",
    "Vandermeer",
)
ORG_STEMS = (
    "Ardent",
    "Beacon",
    "Cobalt",
    "Halcyon",
    "Keystone",
    "Lattice",
    "Meridian",
    "Northgate",
    "Orchard",
    "Pinnacle",
    "Quarry",
    "Ridgeline",
    "Sable",
    "Tidewater",
    "Umber",
    "Vantage",
    "Westbrook",
    "Yarrow",
    "Zephyr",
    "Alder",
    "Brightwater",
    "Cinder",
    "Dunmore",
    "Elmhurst",
    "Foxglove",
    "Granite",
    "Harbor",
    "Ironwood",
    "Juniper",
    "Kestrel",
    "Larkspur",
    "Marlowe",
    "Nightingale",
    "Oakridge",
    "Palisade",
    "Redwood",
    "Silverline",
    "Thornfield",
    "Upland",
    "Valeria",
    "Wrenfield",
    "Amberly",
    "Bluestone",
    "Copperfield",
    "Driftwood",
    "Evergreen",
    "Fairhaven",
    "Glenmoor",
    "Highcastle",
    "Ivyleaf",
)
ORG_DESCRIPTORS = (
    "Industrial",
    "Logistics",
    "Medical",
    "Analytics",
    "Aerospace",
    "Packaging",
    "Maritime",
    "Biologics",
    "Energy",
    "Digital",
    "Materials",
    "Mobility",
    "Foods",
    "Robotics",
    "Financial",
    "Instruments",
    "Networks",
    "Diagnostics",
    "Textiles",
    "Photonics",
    "Semiconductor",
    "Hospitality",
    "Automation",
    "Freight",
    "Agritech",
    "Clinical",
)
ORG_SUFFIXES = (
    "Inc.",
    "LLC",
    "Corporation",
    "Ltd.",
    "Holdings, Inc.",
    "Partners LP",
    "Co.",
    "Group, Inc.",
)
STREETS = (
    "Harrow Street",
    "Linden Avenue",
    "Commerce Boulevard",
    "Whitmore Road",
    "Fifth Avenue",
    "Market Street",
    "Pioneer Drive",
    "Riverside Parkway",
    "Meadowlark Lane",
    "Copley Place",
)
CITIES = (
    "Portland, Oregon",
    "Denver, Colorado",
    "Austin, Texas",
    "Raleigh, North Carolina",
    "Columbus, Ohio",
    "Minneapolis, Minnesota",
    "Wilmington, Delaware",
    "Phoenix, Arizona",
    "Nashville, Tennessee",
    "Boise, Idaho",
)


def _stem_tokens(name: str) -> list[str]:
    tokens = []
    for token in re.split(r"[\s,]+", name):
        clean = token.strip(".,&'’-")
        if (
            len(clean) >= 4
            and clean[0].isupper()
            and clean not in _COMMON_WORDS
            and clean not in _LEADING_STOP
            and not re.fullmatch(_ORG_SUFFIX, token.rstrip(","))
        ):
            tokens.append(clean)
    return tokens


def _clean_org(name: str) -> str:
    """Drop leading stop words ("Via Ridgeline Power Holdings LLC") and collapse whitespace."""

    tokens = name.split()
    while tokens and (
        tokens[0].strip(".,") in _LEADING_STOP or tokens[0].strip(".,") in _COMMON_WORDS
    ):
        tokens.pop(0)
    return " ".join(tokens)


def _has_legal_suffix(name: str) -> bool:
    return re.search(_LEGAL_SUFFIX + r"\s*$", name.rstrip(",")) is not None


def _org_candidates(text: str, *, trusted: str = "") -> list[str]:
    """Organizations worth renaming.

    Legal-suffix names ("Aldersgate Software Solutions, Inc.") are always
    candidates. Descriptive names ("Crestview Software Solutions") are only
    candidates when they share a stem with a legal-suffix name or appear in
    ``trusted`` text (header, footer, title block), where names are reliable
    and generic phrases ("Cyber Liability Insurance") do not occur.
    """

    primary: list[str] = []
    secondary: list[str] = []
    trusted_names = set()
    for match in _ORG.finditer(trusted):
        name = _clean_org(" ".join(match.group(1).split()))
        if _stem_tokens(name) and len(name.split()) >= 2:
            trusted_names.add(name)
    for match in _ORG.finditer(text):
        name = _clean_org(" ".join(match.group(1).split()))
        # A caption such as "OFFICER'S CERTIFICATE OF HELIOS BIOSCIENCES, INC."
        # names the organization after "of"; the caption itself is not one.
        parts = re.split(r"\s+(?:of|OF|Of)\s+", name)
        if len(parts) > 1 and _has_legal_suffix(parts[-1]) and _stem_tokens(parts[-1]):
            name = _clean_org(parts[-1])
        stems = _stem_tokens(name)
        if not stems or len(name.split()) < 2:
            continue
        if any(
            token in _LEADING_STOP
            or token.upper()
            in {"OF", "THE", "AND", "FOR", "TO", "IN", "ON", "BY", "FROM", "WITH"}
            for token in name.split()[1:-1]
        ):
            continue
        if any(
            token.rstrip(",.").upper().endswith(("'S", "’S")) for token in name.split()
        ):
            continue
        if _has_legal_suffix(name):
            if name not in primary:
                primary.append(name)
        elif name not in secondary:
            secondary.append(name)
    known = {stem for name in primary for stem in _stem_tokens(name)}
    ordered = list(primary)
    for name in secondary:
        if name in ordered:
            continue
        if name in trusted_names or any(stem in known for stem in _stem_tokens(name)):
            ordered.append(name)
    return ordered


def inventory(text: str, *, header: str = "") -> dict[str, list[str]]:
    """Distinct organizations, people, defined terms, dates, and amounts in a text."""

    haystack = f"{header}\n{text}"
    orgs: Counter = Counter()
    header_orgs = set(_org_candidates(header, trusted=header)) if header else set()
    for name in _org_candidates(haystack, trusted=header):
        orgs[name] += haystack.count(name) + (3 if name in header_orgs else 0)
    people: Counter = Counter()
    for name in _people_in(haystack, orgs):
        people[name] += haystack.count(name)
    terms = [
        term.strip()
        for term in dict.fromkeys(_DEFINED_TERM.findall(haystack))
        if 2 <= len(term.split()) <= 4 or term.istitle()
    ]
    dates = list(
        dict.fromkeys(match.group(0) for match in _LONG_DATE.finditer(haystack))
    )
    amounts = list(dict.fromkeys(match.group(0) for match in _MONEY.finditer(haystack)))
    return {
        "orgs": [name for name, _ in orgs.most_common(24)],
        "people": [name for name, _ in people.most_common(24)],
        "terms": terms[:40],
        "dates": dates[:24],
        "amounts": amounts[:24],
    }


_NAME_TOKEN = re.compile(r"[A-Za-z][A-Za-z'’\-]*\.?")
_HONORIFICS = frozenset(
    {"Mr.", "Ms.", "Mrs.", "Dr.", "Hon.", "Prof.", "Judge", "Justice"}
)
_SURNAME_BLOCK = frozenset(
    {
        "Street",
        "Avenue",
        "Boulevard",
        "Road",
        "Drive",
        "Lane",
        "Plaza",
        "Parkway",
        "Court",
        "Suite",
        "City",
        "County",
        "Bank",
        "Trust",
        "Capital",
        "Partners",
        "Holdings",
        "Group",
        "Fund",
        "Inc",
        "Inc.",
        "LLC",
        "LLP",
        "Ltd",
        "Ltd.",
        "Corp",
        "Corp.",
        "Co",
        "Co.",
    }
)


def _people_in(text: str, orgs: Iterable[str]) -> list[str]:
    """Person names: a lexicon first name (or an honorific) followed by a surname.

    A token scan rather than one regex, so "Contact Rachel Ostroff" yields
    "Rachel Ostroff" instead of consuming "Contact" as the first name.
    """

    org_words = {word.strip(".,") for org in orgs for word in str(org).split()}
    tokens = _NAME_TOKEN.findall(text)
    found: list[str] = []

    def surname_ok(word: str) -> bool:
        clean = word.rstrip(".")
        return (
            len(clean) >= 2
            and clean[0].isupper()
            and clean[1:2].islower()
            and clean not in _COMMON_WORDS
            and clean not in _LEADING_STOP
            and clean not in _SURNAME_BLOCK
            and clean not in FIRST_NAME_LEXICON
        )

    index = 0
    while index < len(tokens) - 1:
        token = tokens[index]
        honorific = token in _HONORIFICS
        first = tokens[index + 1] if honorific else token
        offset = index + 2 if honorific else index + 1
        if offset >= len(tokens):
            break
        if not (honorific or first in FIRST_NAME_LEXICON) or not first[0].isupper():
            index += 1
            continue
        middle = ""
        nxt = tokens[offset]
        if re.fullmatch(r"[A-Z]\.", nxt) and offset + 1 < len(tokens):
            middle = nxt
            offset += 1
            nxt = tokens[offset]
        last = nxt.rstrip(".,;:")
        if surname_ok(last) and not (first in org_words and last in org_words):
            name = " ".join(part for part in (first, middle, last) if part)
            if name not in found:
                found.append(name)
            index = offset + 1
            continue
        index += 1
    return found


def generate_org(rng: Random, like: str = "") -> str:
    """A fresh organization name shaped like ``like`` (suffix family preserved)."""

    stem = rng.choice(ORG_STEMS)
    descriptor = rng.choice(ORG_DESCRIPTORS)
    suffix_match = (
        re.search(_ORG_SUFFIX + r"\s*$", like.strip().rstrip(",")) if like else None
    )
    suffix = suffix_match.group(0) if suffix_match else rng.choice(ORG_SUFFIXES)
    lower = like.lower()
    if any(
        word in lower for word in ("llp", "law", "counsel", "solicitors", "attorneys")
    ):
        return f"{rng.choice(LAST_NAMES)} {rng.choice(LAST_NAMES)} & {rng.choice(LAST_NAMES)} LLP"
    if any(
        word in lower
        for word in (
            "capital",
            "partners",
            "fund",
            "ventures",
            "advisors",
            "holdings",
            "equity",
        )
    ):
        return f"{stem} {rng.choice(('Capital', 'Partners', 'Ventures', 'Holdings', 'Equity Partners'))} {suffix if 'LLP' not in suffix else 'LP'}".replace(
            "  ", " "
        )
    if any(word in lower for word in ("bank", "trust", "financial", "credit")):
        return f"{stem} {rng.choice(('National Bank', 'Trust Company', 'Financial Corporation', 'Credit Union'))}"
    if any(
        word in lower
        for word in ("university", "hospital", "institute", "foundation", "health")
    ):
        return f"{stem} {rng.choice(('Health System', 'Medical Center', 'Research Institute', 'University'))}"
    if any(
        word in lower
        for word in (
            "county",
            "city of",
            "department",
            "authority",
            "commission",
            "agency",
        )
    ):
        return f"{rng.choice(('Cascade', 'Franklin', 'Harlan', 'Pike', 'Summit'))} County {rng.choice(('Housing Authority', 'Planning Commission', 'Department of Revenue', 'Water District'))}"
    return f"{stem} {descriptor} {suffix}"


def generate_person(rng: Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def generate_address(rng: Random) -> str:
    return f"{rng.randrange(100, 9800)} {rng.choice(STREETS)}, Suite {rng.randrange(100, 2400)}, {rng.choice(CITIES)}"


_ONES = (
    "",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
)
_TENS = (
    "",
    "",
    "Twenty",
    "Thirty",
    "Forty",
    "Fifty",
    "Sixty",
    "Seventy",
    "Eighty",
    "Ninety",
)


def number_to_words(value: int) -> str:
    """Integers as legal prose writes them ("Twenty-Five Million Four Hundred Thousand")."""

    if value < 0:
        return "Minus " + number_to_words(-value)
    if value < 20:
        return _ONES[value] or "Zero"
    if value < 100:
        tens, ones = divmod(value, 10)
        return _TENS[tens] + (f"-{_ONES[ones]}" if ones else "")
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        return f"{_ONES[hundreds]} Hundred" + (
            f" {number_to_words(rest)}" if rest else ""
        )
    for scale, label in (
        (1_000_000_000, "Billion"),
        (1_000_000, "Million"),
        (1_000, "Thousand"),
    ):
        if value >= scale:
            major, rest = divmod(value, scale)
            return f"{number_to_words(major)} {label}" + (
                f" {number_to_words(rest)}" if rest else ""
            )
    return str(value)


_WORDS_PERCENT = re.compile(
    r"\b([A-Za-z]+(?:[- ][A-Za-z]+){0,3}) percent \((\d{1,3}(?:\.\d{1,2})?)%\)"
)
_WORDS_DOLLARS = re.compile(
    r"\b([A-Z][A-Za-z]+(?:[- ][A-Z][A-Za-z]+){0,8}) (?:U\.S\. )?Dollars \(\$([\d,]+)(?:\.\d{2})?\)"
)


def _align_number_words(text: str) -> str:
    """After numerals were re-drawn, make the spelled-out form agree with them."""

    def percent(match: re.Match[str]) -> str:
        number = match.group(2)
        if "." in number:
            return match.group(0)
        words = number_to_words(int(number)).lower()
        return f"{words} percent ({number}%)"

    def dollars(match: re.Match[str]) -> str:
        digits = match.group(2).replace(",", "")
        if not digits.isdigit():
            return match.group(0)
        words = number_to_words(int(digits))
        tail = match.group(0)[match.group(0).index(" Dollars") :]
        return f"{words}{tail}"

    text = _WORDS_PERCENT.sub(percent, text)
    return _WORDS_DOLLARS.sub(dollars, text)


def _money_like(original: str, rng: Random) -> str:
    match = re.search(r"\d[\d,]*(?:\.\d+)?", original)
    if not match:
        return original
    digits = match.group(0).replace(",", "")
    try:
        value = float(digits)
    except ValueError:
        return original
    factor = rng.choice((0.6, 0.72, 0.85, 1.15, 1.3, 1.45, 1.6, 2.1))
    scaled = value * factor
    if (
        "." in digits
        and len(digits.split(".")[1]) == 2
        and "million" not in original.lower()
    ):
        text = f"{scaled:,.2f}"
    elif value >= 1000:
        magnitude = 10 ** max(0, len(str(int(value))) - 2)
        text = f"{int(round(scaled / magnitude) * magnitude):,}"
    else:
        text = f"{scaled:.1f}".rstrip("0").rstrip(".")
    return original[: match.start()] + text + original[match.end() :]


def _percent_like(original: str, rng: Random) -> str:
    match = re.search(r"\d{1,3}(?:\.\d{1,2})?", original)
    if not match:
        return original
    value = float(match.group(0))
    options = [
        v
        for v in (
            value * 0.5,
            value * 0.75,
            value * 1.25,
            value * 1.5,
            value + 5,
            max(0.5, value - 5),
        )
        if 0 < v <= 100
    ]
    new = rng.choice(options) if options else value
    text = (
        f"{new:.2f}".rstrip("0").rstrip(".")
        if "." in match.group(0)
        else str(int(round(new)))
    )
    return original[: match.start()] + text + original[match.end() :]


_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _shift_long_date(match: re.Match[str], offset: int) -> str:
    try:
        original = date(
            int(match.group(3)), _MONTHS.index(match.group(1)) + 1, int(match.group(2))
        )
    except ValueError:
        return match.group(0)
    shifted = original + timedelta(days=offset)
    return f"{_MONTHS[shifted.month - 1]} {shifted.day}, {shifted.year}"


def _shift_iso_date(match: re.Match[str], offset: int) -> str:
    try:
        original = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return match.group(0)
    return (original + timedelta(days=offset)).isoformat()


def _match_case(found: str, replacement: str) -> str:
    """Upper-case the replacement when the matched span was shouted."""

    letters = [c for c in found if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return replacement.upper()
    return replacement


class Reskin:
    """A consistent, deterministic substitution map for one document."""

    def __init__(
        self,
        rng: Random,
        *,
        organizations: Mapping[str, str] | None = None,
        people: Mapping[str, str] | None = None,
        date_offset_days: int | None = None,
        avoid: Iterable[str] = (),
    ) -> None:
        self.rng = rng
        self.organizations: dict[str, str] = dict(organizations or {})
        self.people: dict[str, str] = dict(people or {})
        self.date_offset = (
            date_offset_days
            if date_offset_days is not None
            else rng.choice((-400, -365, -290, -210, -120, 120, 200, 275, 365, 430))
        )
        self.avoid = tuple(
            sorted(
                {
                    needle.casefold()
                    for needle in avoid
                    if needle and len(needle.strip()) >= 2
                },
                key=len,
                reverse=True,
            )
        )
        self._tokens: dict[str, str] = {}
        self._addresses: dict[str, str] = {}
        self._emails: dict[str, str] = {}
        self._phones: dict[str, str] = {}
        self._dockets: dict[str, str] = {}
        self._money: dict[str, str] = {}
        self._percent: dict[str, str] = {}
        self._plain_words: set[str] = set()

    # ---- learning
    def learn(self, text: str, *, roles: Sequence[str] = (), trusted: str = "") -> None:
        """Register every organization and person found in ``text``.

        ``roles`` names caller-supplied organizations in order of appearance
        (e.g. the two parties of an agreement); the first unseen organizations
        are mapped onto them so the caller's parties become the document's.
        ``trusted`` is header/title text where descriptive names are reliable.
        """

        pending_roles = list(roles)
        # Words that occur in lowercase somewhere in the prose are English
        # words, not brands ("corporate", "compliance"): never map them alone.
        self._plain_words.update(re.findall(r"\b[a-z]{4,}\b", text))
        for name in _org_candidates(text, trusted=trusted):
            if name in self.organizations:
                continue
            # A descriptive alias of a registered party ("TerraNode Cloud
            # Services" for "TerraNode Cloud Services, Inc.") follows its stem
            # map instead of consuming a caller role.
            stems = _stem_tokens(name)
            if not _has_legal_suffix(name) and any(
                stem in self._tokens for stem in stems
            ):
                continue
            replacement = (
                pending_roles.pop(0) if pending_roles else self._fresh_org(name)
            )
            self._register_org(name, replacement)
        for name in _people_in(text, self.organizations):
            if name in self.people:
                continue
            surname = name.split()[-1]
            fresh = self._fresh_person()
            if surname in self._tokens:
                # One family, one new surname: "Hans Kessler" and
                # "Robert A. Kessler" stay related after the re-skin.
                fresh = f"{fresh.split()[0]} {self._tokens[surname]}"
            self.people[name] = fresh
            self._tokens.setdefault(surname, fresh.split()[-1])

    def _fresh_org(self, like: str) -> str:
        for _ in range(12):
            candidate = generate_org(self.rng, like)
            if (
                candidate.casefold() not in self.avoid
                and candidate not in self.organizations.values()
            ):
                return candidate
        return generate_org(self.rng, like)

    def _fresh_person(self) -> str:
        for _ in range(12):
            candidate = generate_person(self.rng)
            if (
                candidate.casefold() not in self.avoid
                and candidate not in self.people.values()
            ):
                return candidate
        return generate_person(self.rng)

    def _register_org(self, name: str, replacement: str) -> None:
        self.organizations[name] = replacement
        # The descriptive alias ("TerraNode Cloud Services" for "TerraNode
        # Cloud Services, Inc.") follows the parent so prose stays consistent.
        alias = re.sub(r",?\s*" + _LEGAL_SUFFIX + r"\s*$", "", name.rstrip(","))
        alias_new = re.sub(
            r",?\s*" + _LEGAL_SUFFIX + r"\s*$", "", replacement.rstrip(",")
        )
        if alias and alias != name and len(alias.split()) >= 2:
            self.organizations.setdefault(alias, alias_new or replacement)
        # Only the brand token ("TerraNode" in "TerraNode Cloud Services, Inc.")
        # maps on its own, so short references and possessives follow the
        # parent without renaming ordinary words the name happens to contain.
        old_stems = _stem_tokens(name)
        new_stems = _stem_tokens(replacement) or [replacement.split()[0]]
        if (
            old_stems
            and old_stems[0] == name.split()[0].strip(",.")
            and old_stems[0].lower() not in self._plain_words
            and old_stems[0] not in FIRST_NAME_LEXICON
        ):
            self._tokens.setdefault(old_stems[0], new_stems[0])

    # ---- application
    def apply(self, text: str) -> str:
        if not text:
            return text
        for original, replacement in sorted(
            self.organizations.items(), key=lambda item: len(item[0]), reverse=True
        ):
            text = re.sub(
                re.escape(original),
                lambda m, r=replacement: _match_case(m.group(0), r),
                text,
                flags=re.I,
            )
        for original, replacement in sorted(
            self.people.items(), key=lambda item: len(item[0]), reverse=True
        ):
            text = re.sub(
                r"\b" + re.escape(original) + r"\b",
                lambda m, r=replacement: _match_case(m.group(0), r),
                text,
                flags=re.I,
            )
        for original, replacement in sorted(
            self._tokens.items(), key=lambda item: len(item[0]), reverse=True
        ):
            if original != replacement:
                text = re.sub(
                    r"\b" + re.escape(original) + r"(?=s?\b)",
                    lambda m, r=replacement: _match_case(m.group(0), r),
                    text,
                    flags=re.I,
                )
        text = _LONG_DATE.sub(lambda m: _shift_long_date(m, self.date_offset), text)
        text = _ISO_DATE.sub(lambda m: _shift_iso_date(m, self.date_offset), text)
        text = _MONEY.sub(
            lambda m: self._money.setdefault(
                m.group(0), _money_like(m.group(0), self.rng)
            ),
            text,
        )
        text = _PERCENT.sub(
            lambda m: self._percent.setdefault(
                m.group(0), _percent_like(m.group(0), self.rng)
            ),
            text,
        )
        text = _ADDRESS.sub(
            lambda m: self._addresses.setdefault(
                m.group(0), generate_address(self.rng)
            ),
            text,
        )
        text = _EMAIL.sub(self._email, text)
        text = _PHONE.sub(
            lambda m: self._phones.setdefault(m.group(0), self._phone()), text
        )
        text = _DOCKET.sub(
            lambda m: self._dockets.setdefault(m.group(0), self._docket(m.group(0))),
            text,
        )
        text = _align_number_words(text)
        return self.scrub(text)

    def _name_pattern(self) -> re.Pattern[str] | None:
        """One alternation over every original name, longest first.

        A single pass means a replacement is never re-scanned, so a seed
        token can never rewrite part of a caller-supplied party name.
        """

        key = (len(self.organizations), len(self.people), len(self._tokens))
        cached = getattr(self, "_pattern_cache", None)
        if cached and cached[0] == key:
            return cached[1]
        entries: list[str] = []
        for original in self.organizations:
            entries.append(r"(?<![A-Za-z])" + re.escape(original) + r"(?![A-Za-z])")
        for original in self.people:
            entries.append(r"\b" + re.escape(original) + r"\b")
        for original, replacement in self._tokens.items():
            if original != replacement:
                entries.append(r"\b" + re.escape(original) + r"(?=s?\b)")
        if not entries:
            self._pattern_cache = (key, None)
            return None
        ordered = sorted(entries, key=len, reverse=True)
        pattern = re.compile("|".join(ordered), re.I)
        self._pattern_cache = (key, pattern)
        return pattern

    def _substitute_names(self, text: str) -> str:
        pattern = self._name_pattern()
        if pattern is None:
            return text
        lookup: dict[str, str] = {}
        for original, replacement in self.organizations.items():
            lookup[original.casefold()] = replacement
        for original, replacement in self.people.items():
            lookup[original.casefold()] = replacement
        for original, replacement in self._tokens.items():
            lookup.setdefault(original.casefold(), replacement)

        def swap(match: re.Match[str]) -> str:
            found = match.group(0)
            replacement = lookup.get(found.casefold())
            if replacement is None:
                # Token match with a plural "s" outside the group is impossible
                # (lookahead), so this is a case-variant of a known key.
                for original, value in lookup.items():
                    if original == found.casefold():
                        replacement = value
                        break
            return _match_case(found, replacement) if replacement is not None else found

        return pattern.sub(swap, text)

    def _email(self, match: re.Match[str]) -> str:
        original = match.group(0)
        if original in self._emails:
            return self._emails[original]
        local, _, domain = original.partition("@")
        person = (
            self.rng.choice(list(self.people.values()))
            if self.people
            else generate_person(self.rng)
        )
        first, last = person.split()[0].lower(), person.split()[-1].lower()
        org = (
            self.rng.choice(list(self.organizations.values()))
            if self.organizations
            else generate_org(self.rng)
        )
        stem = (_stem_tokens(org) or [org.split()[0]])[0].lower()
        style = self.rng.choice(
            (f"{first[0]}{last}", f"{first}.{last}", f"{last}{first[0]}")
        )
        self._emails[original] = f"{style}@{stem}.example"
        return self._emails[original]

    def _phone(self) -> str:
        return (
            f"({self.rng.randrange(201, 989)}) 555-{self.rng.randrange(100, 200):04d}"
        )

    def _docket(self, original: str) -> str:
        prefix = original.split()[0] if original.split() else "No."
        if "cv" in original.lower():
            return f"{prefix} {self.rng.randrange(22, 27)}-cv-{self.rng.randrange(1000, 9900)}"
        return f"{prefix} {self.rng.randrange(2023, 2027)}-{self.rng.randrange(100, 999)}-{self.rng.randrange(1000, 9999)}"

    # ---- scrubbing
    def scrub(self, text: str) -> str:
        """Rewrite any occurrence of an avoided literal until none remains."""

        if not self.avoid:
            return text
        folded = text.casefold()
        for needle in self.avoid:
            if needle not in folded:
                continue
            text = self._rewrite_needle(text, needle)
            folded = text.casefold()
        return text

    def _rewrite_needle(self, text: str, needle: str) -> str:
        pattern = re.compile(re.escape(needle), re.I)

        def replacement(match: re.Match[str]) -> str:
            found = match.group(0)
            if found.lower().endswith(" means"):
                return found[: -len(" means")] + " refers to"
            if re.search(r"\d", found):
                digits = re.sub(r"\d", lambda d: str((int(d.group(0)) + 3) % 10), found)
                return (
                    digits if digits.casefold() != needle else re.sub(r"\d", "7", found)
                )
            words = found.split()
            if len(words) >= 2:
                if _ORG.fullmatch(found) or found in self.organizations.values():
                    return generate_org(self.rng, found)
                return (
                    f"{generate_person(self.rng)}"
                    if all(word[:1].isupper() for word in words)
                    else " ".join(words[:-1])
                    + " "
                    + self.rng.choice(
                        ("arrangement", "matter", "record", "item", "position")
                    )
                )
            return self.rng.choice(
                ("the foregoing", "such item", "the relevant record", "that matter")
            )

        for _ in range(4):
            text = pattern.sub(replacement, text)
            if needle not in text.casefold():
                break
        return text

    def contains_avoided(self, text: str) -> list[str]:
        folded = text.casefold()
        return [needle for needle in self.avoid if needle in folded]


def parties_of(blocks_text: Iterable[str]) -> list[str]:
    """Organizations named in the title block, in order (the contracting parties)."""

    found: list[str] = []
    for text in blocks_text:
        for name in _org_candidates(text):
            if name not in found:
                found.append(name)
    return found


__all__ = [
    "number_to_words",
    "FIRST_NAMES",
    "LAST_NAMES",
    "ORG_STEMS",
    "Reskin",
    "generate_address",
    "generate_org",
    "generate_person",
    "inventory",
    "parties_of",
]
