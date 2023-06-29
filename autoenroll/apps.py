from django.apps import AppConfig

MODULE_NAME = "autoenroll"

DEFAULT_CFG = {
    "autoenroll_product_code": "DENTAL",
}


class AutoenrollConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = MODULE_NAME

    autoenroll_product_code = None


    def _configure_autoenroll(self, cfg):
        AutoenrollConfig.autoenroll_product_code = cfg["autoenroll_product_code"]

    def ready(self):
        from core.models import ModuleConfiguration

        cfg = ModuleConfiguration.get_or_default(MODULE_NAME, DEFAULT_CFG)
        self._configure_autoenroll(cfg)
