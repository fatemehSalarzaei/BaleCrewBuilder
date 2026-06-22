from app.services.validation_service import KNOWN_MODULES, KNOWN_TEMPLATE_PROFILES


class UnknownTemplateProfileError(Exception):
    pass


class UnknownModuleError(Exception):
    pass


class MissingRequiredTemplateError(Exception):
    pass


class TemplateRegistry:
    def validate_profile(self, profile: str) -> None:
        if profile not in KNOWN_TEMPLATE_PROFILES:
            raise UnknownTemplateProfileError(
                f"Unknown template profile {profile!r}. "
                f"Known profiles: {sorted(KNOWN_TEMPLATE_PROFILES)}."
            )

    def validate_modules(self, modules: list[str]) -> None:
        unknown = sorted(set(modules) - KNOWN_MODULES)
        if unknown:
            raise UnknownModuleError(
                f"Unknown modules: {unknown}. "
                f"Known modules: {sorted(KNOWN_MODULES)}."
            )
