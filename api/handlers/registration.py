from tornado.escape import json_decode

from .base import BaseHandler
from api.crypto import hash_passphrase, encrypt_field

class RegistrationHandler(BaseHandler):

    async def post(self):
        try:
            body = json_decode(self.request.body)
            email = body['email'].lower().strip()
            password = body['password']
            display_name = body.get('displayName')
            if display_name is None:
                display_name = email
            if not isinstance(display_name, str):
                raise Exception('Display name must be a string')
        except Exception:
            self.send_error(400, message='You must provide an email address, password and display name!')
            return

        if not email:
            self.send_error(400, message='The email address is invalid!')
            return

        if not password:
            self.send_error(400, message='The password is invalid!')
            return

        if not display_name:
            self.send_error(400, message='The display name is invalid!')
            return

        user = await self.db.users.find_one({
          'email': email
        })

        if user is not None:
            self.send_error(409, message='A user with the given email address already exists!')
            return

        doc = {
            'email': email,
            'password': hash_passphrase(password),
            'displayName': display_name
        }

        personal_fields = ['fullName', 'address', 'dateOfBirth', 'phoneNumber', 'disabilities']
        for field in personal_fields:
            value = body.get(field)
            if value is not None:
                ciphertext_b64, iv_b64 = encrypt_field(value)
                doc[field] = ciphertext_b64
                doc[f'{field}_iv'] = iv_b64

        await self.db.users.insert_one(doc)

        self.set_status(200)
        self.response['email'] = email
        self.response['displayName'] = display_name

        self.write_json()
