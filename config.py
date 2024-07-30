from os.path import abspath
from os.path import dirname
from os.path import join

from dynaconf import Dynaconf

_CURRENT_DIR = dirname(abspath(__file__))
CONFIG = Dynaconf(
    envvar_prefix=False,
    merge_enabled=True,
    settings_files=[
        join(_CURRENT_DIR, f)
        for f in [
            "settings/configuration.toml",
            "settings/language_extensions.toml",
            "settings/secret.toml",
        ]
    ],
)
