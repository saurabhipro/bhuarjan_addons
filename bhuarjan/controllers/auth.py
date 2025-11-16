from .main import *
from datetime import timezone

SECRET_KEY = 'secret'

class JWTAuthController(http.Controller):

    @http.route('/api/auth/request_otp', type='http', auth='none', methods=['POST'], csrf=False)
    def request_otp(self, **kwargs):
        data = json.loads(request.httprequest.data or "{}")
        mobile = data.get('mobile')
        if not mobile:
            return Response(json.dumps({'error': 'Mobile number is missing'}), status=400, content_type='application/json' )

        user = request.env['res.users'].sudo().search([('mobile', '=', mobile)], limit=1)
        if not user:            
            return Response(json.dumps({'error': "User Not Register"}), status=400, content_type='application/json' )


        existing_otp = request.env['mobile.otp'].sudo().search([('mobile', '=', mobile)])
        if existing_otp:
            existing_otp.unlink()

        otp_code = str(random.randint(1000, 9999))
        expire_time = datetime.datetime.now(timezone.utc) + datetime.timedelta(minutes=5)

        request.env['mobile.otp'].sudo().create({
            'mobile': mobile,
            'user_id': user.id,
            'otp': otp_code,
            'expire_date': expire_time,
        })

        try:
            msg = f"Your SELECTIAL OPT {otp_code}"
            api_url = f"https://webmsg.smsbharti.com/app/smsapi/index.php?key=5640415B1D6730&campaign=0&routeid=9&type=text&contacts={mobile}&senderid=SPTSMS&msg=Your%20otp%20is%20{otp_code}%20SELECTIAL&template_id=1707166619134631839"
            response = requests.get(api_url)
            print("\n\n response.status_code - ", response.status_code)
            if response.status_code == 200:
                # return Response(json.dumps({'message': 'OTP sent successfully','details': response.text}), content_type='application/json')
                return Response(json.dumps({'message': 'OTP sent successfully','details': otp_code}), status=200, content_type='application/json')

            else:
                return Response(json.dumps({'error': 'Failed to send OTP via SMS API', 'details': response.text}), status=400, content_type='application/json')

        except Exception as e:
            return Response( json.dumps({'error': 'Error sending SMS', 'details': str(e)}), status=400, content_type='application/json' )
        # return Response(json.dumps({'message': 'OTP sent successfully','details': otp_code}), status=400, content_type='application/json')
               
    @http.route('/api/auth/register', type='http', auth='public', methods=['POST'], csrf=False)
    def create_user(self, **kwargs):
        try:
            # Parse incoming JSON data
            data = json.loads(request.httprequest.data or "{}")

            # Validate that required fields are present in the request data
            required_fields = ['name', 'mobile', 'login', 'password']
            for field in required_fields:
                if field not in data:
                    return Response(
                        json.dumps({'error': f'{field} is required'}),
                        status=400,
                        content_type='application/json'
                    )

            # Extract user details from the request
            name = data.get('name')
            mobile = data.get('mobile')
            login = data.get('login')
            password = data.get('password')

            # Check if the login already exists (limit=1 ensures only 1 user is returned)
            existing_user = request.env['res.users'].sudo().search([('login', '=', login)], limit=1)
            if existing_user:
                return Response(
                    json.dumps({'error': f'User with login {login} already exists'}),
                    status=400,
                    content_type='application/json'
                )

            # Check if the mobile number already exists (limit=1 ensures only 1 user is returned)
            existing_mobile_user = request.env['res.users'].sudo().search([('mobile', '=', mobile)], limit=1)
            if existing_mobile_user:
                return Response(
                    json.dumps({'error': f'User with mobile {mobile} already exists'}),
                    status=400,
                    content_type='application/json'
                )

            # Create the new user
            user_vals = {
                'name': name,
                'mobile': mobile,
                'login': login,
                'password': password,
                'active': True,
                'company_id': 1,  # Set the default company if needed
                'company_ids': [(4, 1)],  # Link the user to the company with ID 1
                'groups_id': [(6, 0, [request.env.ref('base.group_user').id, request.env.ref('jwt_mobile_auth.surveyor_group_ddn').id])],  # Assigning the user to the basic user group
            }

            # Create the user
            user = request.env['res.users'].sudo().create(user_vals)
            # Return a success response with user details
            return Response(
                json.dumps({
                    'message': 'User created successfully',
                    'user_id': user.id,
                    'name': user.name,
                    'mobile': user.mobile,
                    'login': user.login,
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            # Handle any unexpected errors
            return Response(
                json.dumps({'error': str(e)}),
                status=400,
                content_type='application/json'
            )

    @http.route('/api/auth/login', type='http', auth='none', methods=['POST'], csrf=False)
    def login(self, **kwargs):
        data = json.loads(request.httprequest.data or "{}")
        mobile = data.get('mobile')
        otp_input = data.get('otp_input')

        if not mobile or not otp_input:
            return Response(json.dumps({'error': 'Mobile number or OTP is missing'}), status=400, content_type='application/json')

        otp_record = request.env['mobile.otp'].sudo().search([
            ('mobile', '=', mobile),
            ('otp', '=', otp_input)
        ], limit=1)
        if not otp_record:
            return Response( json.dumps({'error': 'Invalid OTP'}), status=400, content_type='application/json' )

        expire_date = otp_record.expire_date
        # Convert expire_date to timezone-aware datetime if needed
        if expire_date:
            # If expire_date is timezone-naive, make it timezone-aware (UTC)
            if expire_date.tzinfo is None:
                expire_date = expire_date.replace(tzinfo=timezone.utc)
            current_time = datetime.datetime.now(timezone.utc)
            if current_time > expire_date:
                otp_record.unlink()
                return Response(json.dumps({'error': 'OTP expired'}), status=400, content_type='application/json')

        user = otp_record.user_id.id
        otp_record.unlink()

        payload = {
            'user_id': user,
            'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        request.env['jwt.token'].sudo().create({'user_id': user, 'token': token})

        return Response(json.dumps({'user_id': user, 'token': token}), status=200, content_type='application/json')

    @http.route('/api/get_contacts', type='json', auth='none', methods=['POST'], csrf=False)
    def get_contacts(self, **kwargs):
        try:
            user_id = check_permission(request.httprequest.headers.get('Authorization'))
            if user_id :
                contacts = request.env['res.partner'].sudo().search([])
                contact_data = []
                for contact in contacts:
                    contact_data.append({
                        'name': contact.name,
                        'phone': contact.phone,
                        'email': contact.email,
                        'company': contact.company_id.name if contact.company_id else ''
                    })

                return {'contacts': contact_data}

        except jwt.ExpiredSignatureError:
            raise AccessError('JWT token has expired')
        except jwt.InvalidTokenError:
            raise AccessError('Invalid JWT token')
        
        
    
