from typing import Any

from app.generator.renderer import Renderer


def _pascal_case(snake: str) -> str:
    return "".join(word.capitalize() for word in snake.split("_"))


_SHARED_INIT_PATHS = [
    "bale/__init__.py",
    "bale/shared/__init__.py",
    "bale/tests/__init__.py",
]

_SHARED_TEMPLATES: list[tuple[str, str]] = [
    ("bale/shared/client.py.j2", "bale/shared/client.py"),
    ("bale/shared/backend_client.py.j2", "bale/shared/backend_client.py"),
    ("bale/shared/webhook.py.j2", "bale/shared/webhook.py"),
    ("bale/shared/idempotency.py.j2", "bale/shared/idempotency.py"),
]

# Audience-specific bot templates — selected by bot["audience"] value.
_USER_BOT_TEMPLATES: list[tuple[str, str]] = [
    ("bale/user_bot/webhook.py.j2", "bale/{bot_key}/webhook.py"),
    ("bale/user_bot/commands.py.j2", "bale/{bot_key}/commands.py"),
]

_ADMIN_BOT_TEMPLATES: list[tuple[str, str]] = [
    ("bale/admin_bot/webhook.py.j2", "bale/{bot_key}/webhook.py"),
    ("bale/admin_bot/commands.py.j2", "bale/{bot_key}/commands.py"),
]

# Fallback templates for OPERATORS, CUSTOM, or any unrecognised audience.
_DEFAULT_BOT_TEMPLATES: list[tuple[str, str]] = [
    ("bale/bot/webhook.py.j2", "bale/{bot_key}/webhook.py"),
    ("bale/bot/commands.py.j2", "bale/{bot_key}/commands.py"),
]

_BOT_TEST_TEMPLATE = ("bale/tests/test_bot_webhook.py.j2", "bale/tests/test_{bot_key}_webhook.py")


def _select_bot_templates(bot: dict[str, Any]) -> list[tuple[str, str]]:
    audience = bot.get("audience", "")
    if audience == "admins":
        return _ADMIN_BOT_TEMPLATES
    if audience == "users":
        return _USER_BOT_TEMPLATES
    return _DEFAULT_BOT_TEMPLATES


class BaleBotsModule:
    def generate_pre_manifest(self, renderer: Renderer, context: dict[str, Any]) -> list[str]:
        generated: list[str] = []

        for rel_path in _SHARED_INIT_PATHS:
            renderer.write_file(rel_path, "")
            generated.append(rel_path)

        for template_name, output_path in _SHARED_TEMPLATES:
            renderer.render_template(template_name, output_path, context)
            generated.append(output_path)

        for bot in context["bots"]:
            bot_key = bot["key"]
            bot_class_name = _pascal_case(bot_key)
            bot_context = {
                **context,
                "bot": bot,
                "bot_class_name": bot_class_name,
            }

            renderer.write_file(f"bale/{bot_key}/__init__.py", "")
            generated.append(f"bale/{bot_key}/__init__.py")

            bot_templates = _select_bot_templates(bot)
            for template_name, output_pattern in bot_templates:
                output_path = output_pattern.format(bot_key=bot_key)
                renderer.render_template(template_name, output_path, bot_context)
                generated.append(output_path)

            test_template, test_pattern = _BOT_TEST_TEMPLATE
            test_path = test_pattern.format(bot_key=bot_key)
            renderer.render_template(test_template, test_path, bot_context)
            generated.append(test_path)

        return generated
