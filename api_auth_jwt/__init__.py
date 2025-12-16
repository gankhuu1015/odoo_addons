# -*- coding: utf-8 -*-
import os
import secrets
from . import models
from . import controllers


def _install_jwt(env):
    file_for_secret = str(os.path.join(os.path.dirname(__file__), 'setup/.translator'))
    jwt_secret = secrets.token_hex(32)
    with open(file_for_secret, 'w') as file:
        file.write(jwt_secret)