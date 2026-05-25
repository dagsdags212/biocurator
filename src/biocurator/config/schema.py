from dataclasses import dataclass, field


@dataclass
class RetryConfig:
    max_attempts: int | None = None
    backoff_factor: float | None = None
    max_delay: int | None = None
    timeout: int | None = None

    def resolve(self, defaults: "RetryConfig | None" = None) -> "RetryConfig":
        resolved = RetryConfig(
            max_attempts=self.max_attempts,
            backoff_factor=self.backoff_factor,
            max_delay=self.max_delay,
            timeout=self.timeout,
        )
        if defaults:
            if resolved.max_attempts is None:
                resolved.max_attempts = defaults.max_attempts
            if resolved.backoff_factor is None:
                resolved.backoff_factor = defaults.backoff_factor
            if resolved.max_delay is None:
                resolved.max_delay = defaults.max_delay
            if resolved.timeout is None:
                resolved.timeout = defaults.timeout

        # Fallback to default values if not provided by user
        if resolved.max_attempts is None:
            resolved.max_attempts = 3
        if resolved.backoff_factor is None:
            resolved.backoff_factor = 2.0
        if resolved.max_delay is None:
            resolved.max_delay = 60
        if resolved.timeout is None:
            resolved.timeout = 30
        return resolved

    @classmethod
    def defaults(cls) -> "RetryConfig":
        return cls().resolve()

    @classmethod
    def from_dict(cls, data: dict | None) -> "RetryConfig | None":
        if not data:
            return None
        return cls(
            max_attempts=data.get("max_attempts"),
            backoff_factor=data.get("backoff_factor"),
            max_delay=data.get("max_delay"),
            timeout=data.get("timeout"),
        )


@dataclass
class BreakerConfig:
    """Circuit breaker configuration for a database provider.

    Maps to pybreaker.CircuitBreaker parameters:
      fail_max               -> fail_max
      recovery_timeout       -> reset_timeout
      half_open_max_successes -> success_threshold

    All fields are None by default so existing configs without
    breaker blocks parse without error.
    """

    fail_max: int | None = None
    recovery_timeout: int | None = None
    half_open_max_successes: int | None = None

    def resolve(self, defaults: "BreakerConfig | None" = None) -> "BreakerConfig":
        """Resolve all None fields with defaults, then pybreaker defaults."""
        resolved = BreakerConfig(
            fail_max=self.fail_max,
            recovery_timeout=self.recovery_timeout,
            half_open_max_successes=self.half_open_max_successes,
        )
        if defaults:
            if resolved.fail_max is None:
                resolved.fail_max = defaults.fail_max
            if resolved.recovery_timeout is None:
                resolved.recovery_timeout = defaults.recovery_timeout
            if resolved.half_open_max_successes is None:
                resolved.half_open_max_successes = defaults.half_open_max_successes

        # Fallback to pybreaker default values
        if resolved.fail_max is None:
            resolved.fail_max = 5
        if resolved.recovery_timeout is None:
            resolved.recovery_timeout = 60
        if resolved.half_open_max_successes is None:
            resolved.half_open_max_successes = 1
        return resolved

    @classmethod
    def defaults(cls) -> "BreakerConfig":
        return cls().resolve()

    @classmethod
    def from_dict(cls, data: dict | None) -> "BreakerConfig | None":
        if not data:
            return None
        return cls(
            fail_max=data.get("fail_max"),
            recovery_timeout=data.get("recovery_timeout"),
            half_open_max_successes=data.get("half_open_max_successes"),
        )


@dataclass
class SearchConfig:
    databases: list[str]
    organism: str | None = None
    sequence_type: str = "nucleotide"
    keywords: list[str] = field(default_factory=list)
    max_results: int = 100
    date_range: dict | None = None
    exclude_terms: list[str] = field(default_factory=list)
    location: str | None = None
    taxonomy_filter: str | None = None
    retry: dict[str, RetryConfig] | None = None


@dataclass
class FilterConfig:
    min_length: int | None = None
    max_length: int | None = None
    exclude_terms: list[str] = field(default_factory=list)
    quality_threshold: float | None = None


@dataclass
class ExportConfig:
    outdir: str = "results"
    formats: list[str] = field(default_factory=lambda: ["fasta"])
    prefix: str = "biocurator"


@dataclass
class JobConfig:
    name: str
    search: SearchConfig
    filter: FilterConfig
    export: ExportConfig


@dataclass
class GlobalConfig:
    email: str
    jobs: list[JobConfig]
    retry: RetryConfig | None = None
