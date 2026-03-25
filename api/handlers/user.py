from tornado.web import authenticated

from .auth import AuthHandler
from api.crypto import decrypt_field

class UserHandler(AuthHandler):

    @authenticated
    async def get(self):
        doc = await self.db.users.find_one({'email': self.current_user['email']})

        self.set_status(200)
        self.response['email'] = self.current_user['email']
        self.response['displayName'] = self.current_user['display_name']

        personal_fields = ['fullName', 'address', 'dateOfBirth', 'phoneNumber', 'disabilities']
        try:
            for field in personal_fields:
                if doc.get(field) is not None:
                    self.response[field] = decrypt_field(doc[field], doc[f'{field}_iv'])
        except Exception:
            self.send_error(500, message='Failed to decrypt user data')
            return

        self.write_json()
