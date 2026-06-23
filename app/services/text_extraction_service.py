from pathlib import Path

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".txt", ".md", ".markdown"})


class UnsupportedFileTypeError(ValueError):
    pass


class TextExtractionService:
    def is_supported(self, filename: str) -> bool:
        return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS

    def extract(self, filename: str, content: bytes) -> str:
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise UnsupportedFileTypeError(
                f"Unsupported file type {ext!r}. Supported types: {supported}"
            )
        return content.decode("utf-8")
