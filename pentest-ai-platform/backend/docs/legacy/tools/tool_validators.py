"""
Tool flag validators with FlagSchema pattern (V2 requirement).

Per spec: "Each tool has a FlagSchema that validates flag structure:
- domain: regex ^[a-zA-Z0-9.-]+$
- CIDR: regex ^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}/\\d{1,2}$
- port_list: regex ^[0-9,\\-]+$"
"""
import re
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator


# Regex patterns for validation
DOMAIN_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+$")
CIDR_PATTERN = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$")
PORT_LIST_PATTERN = re.compile(r"^[0-9,\-]+$")
URL_PATTERN = re.compile(r"^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$")


class FlagSchema(BaseModel):
    """Base class for tool flag schemas."""

    class Config:
        extra = "forbid"  # Reject unknown flags


# ===== Stage 1 Tools (V2 MVP) =====

class NmapFlags(FlagSchema):
    """
    Nmap flag schema.

    Allowed flags:
    - target: domain or CIDR
    - ports: port list (e.g., "80,443,8000-9000")
    - scan_type: -sV (service version), -sC (default scripts), -sS (SYN scan)
    - timing: -T0 to -T5
    """
    target: str = Field(..., description="Target domain or CIDR")
    ports: Optional[str] = Field(None, description="Port list (e.g., '80,443,8000-9000')")
    scan_type: Optional[str] = Field("-sV", description="Scan type: -sV, -sC, -sS")
    timing: Optional[str] = Field("-T4", description="Timing template: -T0 to -T5")

    @validator("target")
    def validate_target(cls, v):
        """Validate target is domain or CIDR."""
        if not (DOMAIN_PATTERN.match(v) or CIDR_PATTERN.match(v)):
            raise ValueError(f"Invalid target format. Must be domain or CIDR: {v}")
        return v

    @validator("ports")
    def validate_ports(cls, v):
        """Validate port list format."""
        if v and not PORT_LIST_PATTERN.match(v):
            raise ValueError(f"Invalid port list format: {v}")
        return v

    @validator("scan_type")
    def validate_scan_type(cls, v):
        """Validate scan type."""
        allowed = ["-sV", "-sC", "-sS", "-sT", "-sU"]
        if v and v not in allowed:
            raise ValueError(f"Invalid scan type. Allowed: {allowed}")
        return v

    @validator("timing")
    def validate_timing(cls, v):
        """Validate timing template."""
        allowed = ["-T0", "-T1", "-T2", "-T3", "-T4", "-T5"]
        if v and v not in allowed:
            raise ValueError(f"Invalid timing. Allowed: {allowed}")
        return v


class HttpxFlags(FlagSchema):
    """
    Httpx flag schema.

    Allowed flags:
    - target: URL or domain
    - follow_redirects: bool
    - timeout: int (seconds)
    - status_code: bool (show status code)
    """
    target: str = Field(..., description="Target URL or domain")
    follow_redirects: Optional[bool] = Field(False, description="Follow redirects")
    timeout: Optional[int] = Field(10, description="Timeout in seconds")
    status_code: Optional[bool] = Field(True, description="Show status code")

    @validator("target")
    def validate_target(cls, v):
        """Validate target is URL or domain."""
        if not (URL_PATTERN.match(v) or DOMAIN_PATTERN.match(v)):
            raise ValueError(f"Invalid target format. Must be URL or domain: {v}")
        return v

    @validator("timeout")
    def validate_timeout(cls, v):
        """Validate timeout range."""
        if v and (v < 1 or v > 300):
            raise ValueError(f"Timeout must be 1-300 seconds: {v}")
        return v


class DnsxFlags(FlagSchema):
    """
    Dnsx flag schema.

    Allowed flags:
    - domain: domain name
    - record_type: DNS record type (A, AAAA, CNAME, MX, NS, TXT)
    - resolvers: custom DNS resolvers (optional)
    """
    domain: str = Field(..., description="Domain name")
    record_type: Optional[str] = Field("A", description="DNS record type")
    resolvers: Optional[List[str]] = Field(None, description="Custom DNS resolvers")

    @validator("domain")
    def validate_domain(cls, v):
        """Validate domain format."""
        if not DOMAIN_PATTERN.match(v):
            raise ValueError(f"Invalid domain format: {v}")
        return v

    @validator("record_type")
    def validate_record_type(cls, v):
        """Validate DNS record type."""
        allowed = ["A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA", "PTR"]
        if v and v.upper() not in allowed:
            raise ValueError(f"Invalid record type. Allowed: {allowed}")
        return v.upper() if v else "A"


class SubfinderFlags(FlagSchema):
    """
    Subfinder flag schema.

    Allowed flags:
    - domain: domain name
    - sources: passive sources (optional)
    - timeout: int (seconds)
    """
    domain: str = Field(..., description="Domain name")
    sources: Optional[List[str]] = Field(None, description="Passive sources")
    timeout: Optional[int] = Field(30, description="Timeout in seconds")

    @validator("domain")
    def validate_domain(cls, v):
        """Validate domain format."""
        if not DOMAIN_PATTERN.match(v):
            raise ValueError(f"Invalid domain format: {v}")
        return v

    @validator("timeout")
    def validate_timeout(cls, v):
        """Validate timeout range."""
        if v and (v < 1 or v > 600):
            raise ValueError(f"Timeout must be 1-600 seconds: {v}")
        return v


class KatanaFlags(FlagSchema):
    """
    Katana flag schema (web crawler).

    Allowed flags:
    - url: target URL
    - depth: crawl depth (1-5)
    - timeout: int (seconds)
    - js_crawl: bool (crawl JavaScript)
    """
    url: str = Field(..., description="Target URL")
    depth: Optional[int] = Field(2, description="Crawl depth (1-5)")
    timeout: Optional[int] = Field(60, description="Timeout in seconds")
    js_crawl: Optional[bool] = Field(False, description="Crawl JavaScript")

    @validator("url")
    def validate_url(cls, v):
        """Validate URL format."""
        if not URL_PATTERN.match(v):
            raise ValueError(f"Invalid URL format: {v}")
        return v

    @validator("depth")
    def validate_depth(cls, v):
        """Validate depth range."""
        if v and (v < 1 or v > 5):
            raise ValueError(f"Depth must be 1-5: {v}")
        return v

    @validator("timeout")
    def validate_timeout(cls, v):
        """Validate timeout range."""
        if v and (v < 1 or v > 600):
            raise ValueError(f"Timeout must be 1-600 seconds: {v}")
        return v


class FfufFlags(FlagSchema):
    """
    Ffuf flag schema (fuzzer).

    Allowed flags:
    - url: target URL with FUZZ keyword
    - wordlist: path to wordlist
    - timeout: int (seconds)
    - threads: int (1-50)
    - match_status: status codes to match (e.g., "200,301,302")
    """
    url: str = Field(..., description="Target URL with FUZZ keyword")
    wordlist: str = Field(..., description="Path to wordlist")
    timeout: Optional[int] = Field(60, description="Timeout in seconds")
    threads: Optional[int] = Field(10, description="Number of threads (1-50)")
    match_status: Optional[str] = Field("200,204,301,302,307,401,403,405", description="Status codes to match")

    @validator("url")
    def validate_url(cls, v):
        """Validate URL contains FUZZ keyword."""
        if "FUZZ" not in v:
            raise ValueError("URL must contain FUZZ keyword")
        if not v.startswith("http://") and not v.startswith("https://"):
            raise ValueError("URL must start with http:// or https://")
        return v

    @validator("wordlist")
    def validate_wordlist(cls, v):
        """Validate wordlist path (basic check)."""
        # In production, Worker Runtime will verify file exists
        if not v or len(v) < 1:
            raise ValueError("Wordlist path required")
        return v

    @validator("threads")
    def validate_threads(cls, v):
        """Validate thread count."""
        if v and (v < 1 or v > 50):
            raise ValueError(f"Threads must be 1-50: {v}")
        return v

    @validator("match_status")
    def validate_match_status(cls, v):
        """Validate status code list."""
        if v and not PORT_LIST_PATTERN.match(v):
            raise ValueError(f"Invalid status code format: {v}")
        return v


# Validator registry mapping tool names to FlagSchema classes
FLAG_VALIDATORS = {
    "nmap": NmapFlags,
    "httpx": HttpxFlags,
    "dnsx": DnsxFlags,
    "subfinder": SubfinderFlags,
    "katana": KatanaFlags,
    "ffuf": FfufFlags
}


def validate_tool_flags(method: str, flags: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate tool flags against FlagSchema.

    Args:
        method: Tool method name (e.g., "nmap", "httpx")
        flags: Flags dictionary

    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    method_lower = method.lower()

    if method_lower not in FLAG_VALIDATORS:
        return False, f"No validator for tool: {method}"

    validator_class = FLAG_VALIDATORS[method_lower]

    try:
        # Validate flags using Pydantic model
        validator_class(**flags)
        return True, None
    except Exception as e:
        return False, f"Flag validation failed: {str(e)}"
