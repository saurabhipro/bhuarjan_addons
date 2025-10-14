import jwt
import datetime
import random
import logging
import requests  # Import requests to send API call
from odoo import http
from odoo.http import request, Response
from odoo import models, fields
import json
import random

_logger = logging.getLogger(__name__)

import jwt

from odoo.exceptions import AccessError, UserError


def check_permission(token):
    if not token:
        raise AccessError('Authorization header is missing or invalid')

    try:
        if token.startswith("Bearer "):
            token = token[7:]

        decoded_token = jwt.decode(token, options={"verify_signature": False})
        user_id = decoded_token['user_id']
        
        user_id = request.env['res.users'].sudo().search([('id', '=', user_id)])
        if user_id :
            return user_id

    except jwt.ExpiredSignatureError:
            raise AccessError('JWT token has expired')
    except jwt.InvalidTokenError:
        raise AccessError('Invalid JWT token')