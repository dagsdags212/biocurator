from pathlib import Path
import yaml
from biocurator.config.schema import (
    ExportConfig,
    FilterConfig,
    GlobalConfig,
    JobConfig,
    SearchConfig,
)
from biocurator.exceptions import ConfigNotFoundError, InvalidConfigError


class ConfigLoader:
    @staticmethod
    def load(path: str | Path) -> GlobalConfig:
        path = Path(path)
        if not path.exists():
            raise ConfigNotFoundError(f"Config file not found: {path}")
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise InvalidConfigError(f"Invalid YAML: {exc}") from exc
        return ConfigLoader._parse(data)

    @staticmethod
    def _parse(data: dict) -> GlobalConfig:
        if not isinstance(data, dict):
            raise InvalidConfigError("Config must be a YAML mapping")
        email = data.get("email")
        if not email:
            raise InvalidConfigError("'email' is required at the top level")
        raw_jobs = data.get("jobs")
        if not raw_jobs or not isinstance(raw_jobs, dict):
            raise InvalidConfigError("'jobs' must be a non-empty mapping")
        jobs = [ConfigLoader._parse_job(name, job) for name, job in raw_jobs.items()]
        return GlobalConfig(email=email, jobs=jobs)

    @staticmethod
    def _parse_job(name: str, data: dict) -> JobConfig:
        if not isinstance(data, dict):
            raise InvalidConfigError(f"Job '{name}' must be a mapping")
        search_data = data.get("search") or {}
        filter_data = data.get("filter") or {}
        export_data = data.get("export") or {}
        if not search_data.get("databases"):
            raise InvalidConfigError(
                f"Job '{name}': 'search.databases' is required"
            )
        search = SearchConfig(
            databases=search_data["databases"],
            organism=search_data.get("organism"),
            sequence_type=search_data.get("sequence_type", "nucleotide"),
            keywords=search_data.get("keywords", []),
            max_results=search_data.get("max_results", 100),
            date_range=search_data.get("date_range"),
            exclude_terms=search_data.get("exclude_terms", []),
            location=search_data.get("location"),
            taxonomy_filter=search_data.get("taxonomy_filter"),
        )
        filter_cfg = FilterConfig(
            min_length=filter_data.get("min_length"),
            max_length=filter_data.get("max_length"),
            exclude_terms=filter_data.get("exclude_terms", []),
            quality_threshold=filter_data.get("quality_threshold"),
        )
        export = ExportConfig(
            outdir=export_data.get("outdir", "results"),
            formats=export_data.get("formats", ["fasta"]),
            prefix=export_data.get("prefix", "biocurator"),
        )
        return JobConfig(name=name, search=search, filter=filter_cfg, export=export)
