import os
import re
import logging
from jinja2 import Environment, FileSystemLoader, Template

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TemplateEngine:
    _env = None
    
    # Modes: STRICT (fail on missing) vs PRODUCTION (safe defaults)
    # Controlled by GST_TEMPLATE_MODE environment variable
    MODE = os.environ.get("GST_TEMPLATE_MODE", "PRODUCTION").upper()

    @classmethod
    def get_env(cls):
        """Singleton pattern for Jinja Environment"""
        if cls._env is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            template_dir = os.path.join(base_dir, 'templates')
            cls._env = Environment(loader=FileSystemLoader(template_dir), auto_reload=True)
        return cls._env

    @classmethod
    def render_document(cls, template_name: str, model_dict: dict) -> str:
        """Master extraction point to render any template."""
        env = cls.get_env()
        template = env.get_template(template_name)
        return template.render(**model_dict)

    @staticmethod
    def render_issue_template(template_html: str, context: dict) -> str:
        """
        Renders a raw HTML template string with a context dictionary.
        Centralized logic for placeholder validation and missing variable handling.
        """
        if not template_html:
            return ""
        
        # Ensure context is a dict
        render_context = context if isinstance(context, dict) else {}

        # 1. Extract Placeholders for Validation
        placeholders = set(re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", template_html))
        
        # 2. Registry Validation (Lazy Import to avoid circularity)
        from src.utils.placeholder_registry import get_standard_placeholders
        standard_placeholders = get_standard_placeholders()
        valid_tags = {p['name'] for p in standard_placeholders}
        # Allow system variables
        valid_tags.add("summary_table")

        unknown_tags = placeholders - valid_tags
        if unknown_tags:
            logger.warning(f"[TemplateEngine] Unknown placeholders detected (Registry Mismatch): {unknown_tags}")

        # 3. Missing Variable Handling (STRICT vs PRODUCTION)
        missing_vars = [p for p in placeholders if p not in render_context]
        
        if missing_vars:
            msg = f"[TemplateEngine] Missing variables in context: {missing_vars}"
            if TemplateEngine.MODE == "STRICT":
                logger.error(f"FATAL: {msg}")
                raise ValueError(msg)
            else:
                logger.warning(msg)
                # Inject safe defaults for production
                for var in missing_vars:
                    # Heuristic: if it looks like a formatted number, default to "0"
                    if "formatted" in var or "shortfall" in var:
                        render_context[var] = "0"
                    else:
                        render_context[var] = "-"

        try:
            template = Template(template_html)
            return template.render(**render_context)
        except Exception as e:
            logger.error(f"[TemplateEngine] Rendering failed: {e}")
            return template_html # Absolute fallback to original on crash

