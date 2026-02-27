import os
from jinja2 import Environment, FileSystemLoader

class TemplateEngine:
    _env = None

    @classmethod
    def get_env(cls):
        """Singleton pattern for Jinja Environment"""
        if cls._env is None:
            # Assumes this file is at src/utils/template_engine.py
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            template_dir = os.path.join(base_dir, 'templates')
            
            # Using auto_reload=True to help with development if templates change
            cls._env = Environment(loader=FileSystemLoader(template_dir), auto_reload=True)
            
            # Custom Jinja filters can go here in the future
            # cls._env.filters['my_filter'] = my_filter_function
            
        return cls._env

    @classmethod
    def render_document(cls, template_name: str, model_dict: dict) -> str:
        """
        Master extraction point to render any template.
        Standardizes Jinja context delivery.
        """
        env = cls.get_env()
        template = env.get_template(template_name)
        return template.render(**model_dict)
