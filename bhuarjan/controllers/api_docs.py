from odoo import http
from odoo.http import request, Response
import json

class ApiDocsController(http.Controller):

    @http.route('/bhuarjan/api/docs', type='http', auth='user')
    def api_docs(self, **kwargs):
        # Only allow administrators (base.group_system)
        if not request.env.user.has_group('base.group_system'):
             return request.not_found()
        
        swagger_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Bhuarjan API Documentation</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
    <style>
        body { margin: 0; padding: 0; }
    </style>
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js" crossorigin></script>
<script>
    window.onload = () => {
    window.ui = SwaggerUIBundle({
        url: '/bhuarjan/api/openapi.json',
        dom_id: '#swagger-ui',
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout",
    });
    };
</script>
</body>
</html>
        """
        return swagger_html

    @http.route('/bhuarjan/api/openapi.json', type='http', auth='user', cors='*')
    def openapi_spec(self, **kwargs):
        if not request.env.user.has_group('base.group_system'):
             return request.not_found()

        # Construct basic spec
        base_url = request.httprequest.host_url.rstrip('/')
        
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Bhuarjan REST API",
                "description": "API documentation for Bhuarjan Mobile App integration. You can test endpoints directly here.",
                "version": "1.0.0"
            },
            "servers": [
                {"url": base_url} 
            ],
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT"
                    }
                }
            },
            "paths": {
                "/api/auth/request_otp": {
                    "post": {
                        "tags": ["Authentication"],
                        "summary": "Request OTP",
                        "description": "Request an OTP for a mobile number. If the user is a Patwari, the OTP is returned in the response (Auto-Login). Otherwise, it is sent via SMS.",
                         "requestBody": {
                             "required": True,
                             "content": {
                                 "application/json": {
                                     "schema": {
                                         "type": "object",
                                         "required": ["mobile"],
                                         "properties": {
                                             "mobile": {"type": "string", "example": "9990649990"}
                                         }
                                     }
                                 }
                             }
                         },
                        "responses": {
                             "200": {
                                 "description": "OTP Generated/Sent",
                                 "content": {
                                     "application/json": {
                                         "schema": {
                                              "type": "object",
                                              "properties": {
                                                  "message": {"type": "string"},
                                                  "details": {"type": "string", "description": "OTP code (only for Patwari/Static)"},
                                                  "auto_fill": {"type": "boolean"},
                                                  "role": {"type": "string"}
                                              }
                                         }
                                     }
                                 }
                             },
                             "400": {"description": "Bad Request"},
                             "500": {"description": "Server Error"}
                        }
                    }
                },
                "/api/auth/login": {
                     "post": {
                         "tags": ["Authentication"],
                         "summary": "Login with OTP",
                         "description": "Validate OTP and get JWT token.",
                         "requestBody": {
                             "required": True,
                             "content": {
                                 "application/json": {
                                     "schema": {
                                         "type": "object",
                                         "required": ["mobile", "otp_input"],
                                         "properties": {
                                             "mobile": {"type": "string", "example": "9990649990"},
                                             "otp_input": {"type": "string", "example": "1234"}
                                         }
                                     }
                                 }
                             }
                         },
                         "responses": {
                             "200": {
                                 "description": "Successful Login",
                                 "content": {
                                     "application/json": {
                                         "schema": {
                                              "type": "object",
                                              "properties": {
                                                  "token": {"type": "string", "description": "JWT Token"},
                                                  "user_id": {"type": "integer"},
                                                  "roles": {"type": "array"}
                                              }
                                         }
                                     }
                                 }
                             },
                             "400": {"description": "Invalid OTP or Mobile"}
                         }
                     }
                },
                "/api/get_contacts": {
                    "post": {
                        "tags": ["Resources"],
                        "summary": "Get Contacts",
                        "description": "Example protected endpoint.",
                        "security": [{"bearerAuth": []}],
                        "responses": {
                            "200": {"description": "List of contacts"}
                        }
                    }
                }
            }
        }
        return request.make_response(json.dumps(spec), headers=[('Content-Type', 'application/json')])
