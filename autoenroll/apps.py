from django.apps import AppConfig

MODULE_NAME = "autoenroll"

DEFAULT_CFG = {
    "autoenroll_product_minors": "NOT_CONFIGURED",
    "autoenroll_product_elderly": "NOT_CONFIGURED",
    "autoenroll_product_pregnant_women": "NOT_CONFIGURED",
    "autoenroll_product_indigents": "NOT_CONFIGURED",
}


class AutoenrollConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = MODULE_NAME

    autoenroll_product_minors = None
    autoenroll_product_elderly = None
    autoenroll_product_pregnant_women = None
    autoenroll_product_indigents = None

    def _configure_autoenroll(self, cfg):
        AutoenrollConfig.autoenroll_product_minors = cfg["autoenroll_product_minors"]
        AutoenrollConfig.autoenroll_product_elderly = cfg["autoenroll_product_elderly"]
        AutoenrollConfig.autoenroll_product_pregnant_women = cfg["autoenroll_product_pregnant_women"]
        AutoenrollConfig.autoenroll_product_indigents = cfg["autoenroll_product_indigents"]

    def ready(self):
        from core.models import ModuleConfiguration

        cfg = ModuleConfiguration.get_or_default(MODULE_NAME, DEFAULT_CFG)
        self._configure_autoenroll(cfg)
