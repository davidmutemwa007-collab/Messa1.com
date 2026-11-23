"""Administrator authorization and management regression tests."""
import json
import tempfile
import unittest
from pathlib import Path
from app import MesaApplication

class AdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = MesaApplication(Path(self.tmp.name)/'mesa.sqlite3', 'test-secret')
        status, body, headers = self.request('POST','/api/register',{'name':'Admin Candidate','email':'admin@test.local','password':'VeryStrongPass123'})
        self.assertEqual(status,201)
        self.cookie = headers['Set-Cookie'].split(';',1)[0]
    def tearDown(self): self.tmp.cleanup()
    def request(self, method, path, payload=None, cookie=None):
        headers={'Host':'localhost'}
        if cookie: headers['Cookie']=cookie
        status, body, response_headers = self.app.handle(method,path,headers,json.dumps(payload or {}).encode())
        try: body=json.loads(body)
        except Exception: pass
        return status,body,response_headers
    def promote(self):
        with self.app._db() as db: db.execute("UPDATE users SET role='super_admin' WHERE email='admin@test.local'")
    def test_customer_cannot_access_admin_routes(self):
        self.assertEqual(self.request('GET','/api/admin/summary',cookie=self.cookie)[0],403)
    def test_admin_dashboard_and_management_routes(self):
        self.promote()
        self.assertEqual(self.request('GET','/api/admin/me',cookie=self.cookie)[1]['user']['role'],'super_admin')
        self.assertEqual(self.request('GET','/api/admin/summary',cookie=self.cookie)[0],200)
        self.assertEqual(self.request('GET','/api/admin/users',cookie=self.cookie)[0],200)
        self.assertEqual(self.request('GET','/api/admin/orders',cookie=self.cookie)[0],200)
        self.assertEqual(self.request('GET','/api/admin/bookings',cookie=self.cookie)[0],200)
        self.assertEqual(self.request('GET','/api/admin/audit',cookie=self.cookie)[0],200)
        self.assertEqual(len(self.request('GET','/api/admin/menu',cookie=self.cookie)[1]['items']),8)
    def test_customer_access_can_be_disabled_and_restored(self):
        self.promote()
        customer_status, customer, headers = self.request('POST','/api/register',{'name':'Customer','email':'customer@test.local','password':'StrongCustomer123'})
        self.assertEqual(customer_status,201)
        customer_id = customer['user']['id']
        self.assertEqual(self.request('POST','/api/admin/users/access',{'user_id':customer_id,'active':False},self.cookie)[0],200)
        customer_cookie = headers['Set-Cookie'].split(';',1)[0]
        self.assertIsNone(self.request('GET','/api/me',cookie=customer_cookie)[1]['user'])
        self.assertEqual(self.request('POST','/api/admin/users/access',{'user_id':customer_id,'active':True},self.cookie)[0],200)
    def test_order_and_booking_statuses_are_managed(self):
        self.promote()
        _, order, _ = self.request('POST','/api/orders',{'name':'Guest','email':'guest@example.com','phone':'+260971234567','fulfilment':'pickup','payment':'pay-at-counter','items':[{'id':'mesa-smash','quantity':1}]})
        _, booking, _ = self.request('POST','/api/bookings',{'name':'Guest','email':'guest@example.com','phone':'+260971234567','date':'2099-06-20','time':'18:00','guests':2})
        self.assertEqual(self.request('POST','/api/admin/orders/status',{'id':1,'status':'Preparing'},self.cookie)[0],200)
        self.assertEqual(self.request('POST','/api/admin/bookings/status',{'id':1,'status':'Confirmed'},self.cookie)[0],200)
        self.assertEqual(self.request('GET','/api/admin/orders',cookie=self.cookie)[1]['orders'][0]['status'],'Preparing')
        self.assertEqual(self.request('GET','/api/admin/bookings',cookie=self.cookie)[1]['bookings'][0]['status'],'Confirmed')
    def test_builtin_menu_items_can_be_archived_and_restored(self):
        self.promote()
        self.assertEqual(self.request('POST','/api/admin/menu/delete',{'id':'mesa-smash'},self.cookie)[0],200)
        self.assertNotIn('mesa-smash',[item['id'] for item in self.request('GET','/api/menu')[1]['items']])
        self.assertEqual(self.request('POST','/api/admin/menu/restore',{'id':'mesa-smash'},self.cookie)[0],200)
        self.assertIn('mesa-smash',[item['id'] for item in self.request('GET','/api/menu')[1]['items']])
    def test_menu_create_publishes_and_order_can_use_new_item(self):
        self.promote()
        payload={'id':'admin-special','name':'Admin Special','description':'Fresh special','price':99,'category':'Mains','tag':'New'}
        self.assertEqual(self.request('POST','/api/admin/menu/save',payload,self.cookie)[0],200)
        self.assertTrue(any(i['id']=='admin-special' for i in self.request('GET','/api/menu')[1]['items']))
        order={'name':'Guest','email':'guest@example.com','phone':'+260971234567','fulfilment':'pickup','payment':'pay-at-counter','items':[{'id':'admin-special','quantity':1}]}
        self.assertEqual(self.request('POST','/api/orders',order,self.cookie)[0],201)
    def test_menu_price_must_be_a_whole_number(self):
        self.promote()
        payload={'id':'fractional-item','name':'Fractional','description':'Invalid price','price':1.5,'category':'Mains','tag':'New'}
        self.assertEqual(self.request('POST','/api/admin/menu/save',payload,self.cookie)[0],400)

    def test_delivery_zone_pricing_is_server_configured(self):
        self.promote()
        self.assertEqual(self.request('POST', '/api/admin/delivery/zones/save', {
            'id': 'test-zone', 'name': 'Test Zone', 'region': 'Lusaka', 'fee': 25,
            'estimated_minutes': 45, 'minimum_order': 80, 'free_threshold': 200,
            'active': True, 'instructions': ''
        }, self.cookie)[0], 200)
        order = {
            'name': 'Guest', 'email': 'guest@example.com', 'phone': '+260971234567',
            'fulfilment': 'delivery', 'delivery_zone_id': 'test-zone', 'address': 'House 12, Test Road',
            'payment': 'cash-on-delivery', 'items': [{'id': 'mesa-smash', 'quantity': 1}]
        }
        status, result, _ = self.request('POST', '/api/orders', order)
        self.assertEqual(status, 201, result)
        self.assertEqual(result['total'], 113)
        order['items'] = [{'id': 'mesa-smash', 'quantity': 1}, {'id': 'garden-stack', 'quantity': 2}]
        status, result, _ = self.request('POST', '/api/orders', order)
        self.assertEqual(status, 201, result)
        self.assertEqual(result['total'], 240)
        order['items'] = [{'id': 'golden-fries', 'quantity': 1}]
        self.assertEqual(self.request('POST', '/api/orders', order)[0], 400)

    def test_mobile_payment_requires_enabled_method_and_manual_review(self):
        self.promote()
        _, user, headers = self.request('POST', '/api/register', {
            'name': 'Customer', 'email': 'pay@test.local', 'password': 'StrongCustomer123'
        })
        customer_cookie = headers['Set-Cookie'].split(';', 1)[0]
        order = {
            'name': 'Customer', 'email': 'pay@test.local', 'phone': '+260971234567',
            'fulfilment': 'pickup', 'payment': 'mtn-mobile-money',
            'items': [{'id': 'mesa-smash', 'quantity': 1}]
        }
        self.assertEqual(self.request('POST', '/api/orders', order, customer_cookie)[0], 400)
        self.assertEqual(self.request('POST', '/api/admin/payment-methods/save', {
            'id': 'mtn-mobile-money', 'name': 'MTN Mobile Money', 'business_number': '0970000000',
            'registered_name': 'MESA TEST MERCHANT', 'merchant_info': '', 'instructions': '',
            'qr_image_url': '', 'enabled': True
        }, self.cookie)[0], 200)
        status, created, _ = self.request('POST', '/api/orders', order, customer_cookie)
        self.assertEqual(status, 201, created)
        self.assertEqual(self.request('POST', '/api/payments/submit', {
            'order_reference': created['reference'], 'transaction_reference': 'MTN-TEST-001'
        }, customer_cookie)[0], 201)
        with self.app._db() as db:
            payment = db.execute('SELECT status FROM payments').fetchone()
            self.assertEqual(payment['status'], 'Payment Submitted')
        self.assertEqual(self.request('POST', '/api/admin/payments/status', {
            'id': 1, 'status': 'Verified'
        }, self.cookie)[0], 200)
        with self.app._db() as db:
            self.assertEqual(db.execute('SELECT status FROM payments').fetchone()['status'], 'Verified')

    def test_payment_review_cannot_be_called_by_customer(self):
        _, _, headers = self.request('POST', '/api/register', {
            'name': 'Customer', 'email': 'pay@test.local', 'password': 'StrongCustomer123'
        })
        customer_cookie = headers['Set-Cookie'].split(';', 1)[0]
        self.assertEqual(self.request('POST', '/api/admin/payments/status', {
            'id': 1, 'status': 'Verified'
        }, customer_cookie)[0], 403)

    def test_temporary_staff_password_must_change_before_admin_api_access(self):
        self.promote()
        with self.app._db() as db:
            db.execute("UPDATE users SET must_change_password=1 WHERE email='admin@test.local'")
        self.assertEqual(self.request('GET', '/api/admin/summary', cookie=self.cookie)[0], 403)
        status, result, headers = self.request('POST', '/api/password/change', {
            'current_password': 'VeryStrongPass123', 'new_password': 'AnEvenStrongerPass456'
        }, self.cookie)
        self.assertEqual(status, 200, result)
        new_cookie = headers['Set-Cookie'].split(';', 1)[0]
        self.assertEqual(self.request('GET', '/api/admin/summary', cookie=new_cookie)[0], 200)

    def test_delivery_staff_cannot_update_another_staff_assignment(self):
        self.promote()
        _, _, staff_headers = self.request('POST', '/api/register', {
            'name': 'Delivery Staff', 'email': 'courier@test.local', 'password': 'StrongCourier123'
        })
        with self.app._db() as db:
            staff_id = db.execute("SELECT id FROM users WHERE email='courier@test.local'").fetchone()[0]
            db.execute("UPDATE users SET role='delivery_staff' WHERE id=?", (staff_id,))
        staff_status, _, login_headers = self.request('POST', '/api/login', {
            'email': 'courier@test.local', 'password': 'StrongCourier123'
        })
        self.assertEqual(staff_status, 200)
        staff_cookie = login_headers['Set-Cookie'].split(';', 1)[0]
        self.assertEqual(self.request('POST', '/api/admin/deliveries/status', {
            'order_id': 1, 'status': 'Delivered'
        }, staff_cookie)[0], 404)

    def test_payment_methods_are_not_public_until_configured(self):
        status, payload, _ = self.request('GET', '/api/payment-methods')
        self.assertEqual(status, 200)
        self.assertEqual(payload['methods'], [])

    def test_orders_csv_escapes_spreadsheet_formulas(self):
        self.promote()
        self.assertEqual(self.request('POST', '/api/orders', {
            'name': '=HYPERLINK("https://example.invalid")',
            'email': 'formula@example.com', 'phone': '+260971234567',
            'fulfilment': 'pickup', 'payment': 'pay-at-counter',
            'items': [{'id': 'mesa-smash', 'quantity': 1}]
        })[0], 201)
        status, content, headers = self.request('GET', '/api/admin/reports/orders.csv', cookie=self.cookie)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn(b'\'=HYPERLINK', content)

    def test_role_assignment_and_last_super_admin_protection(self):
        self.promote()
        self.assertEqual(self.request('POST', '/api/admin/users/role', {
            'user_id': 1, 'role': 'manager'
        }, self.cookie)[0], 400)
        _, _, headers = self.request('POST', '/api/register', {
            'name': 'Staff Candidate', 'email': 'staff@test.local', 'password': 'StrongStaff123'
        })
        with self.app._db() as db:
            staff_id = db.execute("SELECT id FROM users WHERE email='staff@test.local'").fetchone()[0]
        self.assertEqual(self.request('POST', '/api/admin/users/role', {
            'user_id': staff_id, 'role': 'delivery_staff'
        }, self.cookie)[0], 200)
        self.assertEqual(self.request('GET', '/api/admin/delivery/staff', cookie=self.cookie)[1]['staff'][0]['id'], staff_id)

    def test_admin_can_save_content_and_uploads_reject_non_images(self):
        self.promote()
        self.assertEqual(self.request('POST', '/api/admin/content/save', {
            'content': {'announcement': 'Welcome to MESA'}
        }, self.cookie)[0], 200)
        self.assertEqual(self.request('GET', '/api/content')[1]['content']['announcement'], 'Welcome to MESA')
        self.assertEqual(self.request('POST', '/api/admin/uploads/image', {
            'data': 'data:image/png;base64,SGVsbG8='
        }, self.cookie)[0], 400)
    def test_customer_role_cannot_be_requested_during_registration(self):
        status, body, _=self.request('POST','/api/register',{'name':'Bad Role','email':'badrole@test.local','password':'VeryStrongPass123','role':'admin'})
        self.assertEqual(status,201)
        with self.app._db() as db:
            self.assertEqual(db.execute("SELECT role FROM users WHERE email='badrole@test.local'").fetchone()[0],'customer')

if __name__=='__main__': unittest.main(verbosity=2)
