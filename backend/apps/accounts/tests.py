import json
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase
from .models import VerifiedEmail


class AccountApiTests(TestCase):
	def setUp(self):
		self.client = Client(enforce_csrf_checks=True)
		response = self.client.get(
			'/api/accounts/csrf/', HTTP_ORIGIN='http://127.0.0.1:8080'
		)
		self.csrf_token = response.cookies['csrftoken'].value
		self.headers = {
			'HTTP_X_CSRFTOKEN': self.csrf_token,
			'HTTP_ORIGIN': 'http://127.0.0.1:8080',
		}
		self.assertEqual(
			response['Access-Control-Allow-Origin'], 'http://127.0.0.1:8080'
		)
		self.assertEqual(response['Access-Control-Allow-Credentials'], 'true')

	def post_json(self, path, payload):
		return self.client.post(
			path,
			data=json.dumps(payload),
			content_type='application/json',
			**self.headers,
		)

	def test_register_creates_user_and_starts_session(self):
		response = self.post_json(
			'/api/accounts/register/',
			{
				'full_name': 'Chiamaka Okoro',
				'email': 'chiamaka@example.com',
				'password': 'A-strong-password-42!',
			},
		)

		self.assertEqual(response.status_code, 201)
		self.assertEqual(
			get_user_model().objects.get().email, 'chiamaka@example.com'
		)
		self.assertEqual(
			self.client.get('/api/accounts/me/').json()['user']['full_name'],
			'Chiamaka Okoro',
		)

	def test_login_requires_valid_credentials_and_csrf(self):
		get_user_model().objects.create_user(
			username='holder@example.com',
			email='holder@example.com',
			password='A-strong-password-42!',
		)

		denied = self.client.post(
			'/api/accounts/login/',
			data=json.dumps(
				{'email': 'holder@example.com', 'password': 'wrong-password'}
			),
			content_type='application/json',
		)
		accepted = self.post_json(
			'/api/accounts/login/',
			{'email': 'holder@example.com', 'password': 'A-strong-password-42!'},
		)

		self.assertEqual(denied.status_code, 403)
		self.assertEqual(accepted.status_code, 200)
		self.assertEqual(self.client.get('/api/accounts/me/').status_code, 200)
		self.headers['HTTP_X_CSRFTOKEN'] = self.client.cookies['csrftoken'].value
		signed_out = self.post_json('/api/accounts/logout/', {})
		self.assertEqual(signed_out.status_code, 200)
		self.assertEqual(self.client.get('/api/accounts/me/').status_code, 401)

	def test_duplicate_email_is_rejected(self):
		get_user_model().objects.create_user(
			username='holder@example.com',
			email='holder@example.com',
			password='A-strong-password-42!',
		)

		response = self.post_json(
			'/api/accounts/register/',
			{
				'full_name': 'Another Holder',
				'email': 'HOLDER@example.com',
				'password': 'A-strong-password-42!',
			},
		)

		self.assertEqual(response.status_code, 400)

	def test_password_reset_sends_link_without_disclosing_account_existence(self):
		get_user_model().objects.create_user(
			username='holder@example.com',
			email='holder@example.com',
			password='A-strong-password-42!',
		)

		response = self.post_json(
			'/api/accounts/password-reset/', {'email': 'holder@example.com'}
		)

		self.assertEqual(response.status_code, 200)
		self.assertIn('If an account exists', response.json()['detail'])
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('/api/accounts/password-reset/', mail.outbox[0].body)

	def test_profile_updates_are_scoped_and_email_changes_require_verification(self):
		user = get_user_model().objects.create_user(
			username='admin@example.com',
			email='admin@example.com',
			password='A-strong-password-42!',
		)
		other_user = get_user_model().objects.create_user(
			username='other@example.com',
			email='other@example.com',
			password='A-strong-password-42!',
		)
		self.client.force_login(user)
		profile = self.client.patch(
			'/api/accounts/profile/',
			data=json.dumps({'full_name': 'Ada Admin'}),
			content_type='application/json',
			**self.headers,
		)
		self.assertEqual(profile.status_code, 200)
		user.refresh_from_db()
		self.assertEqual(user.get_full_name(), 'Ada Admin')
		other_user.refresh_from_db()
		self.assertEqual(other_user.first_name, '')
		self.assertEqual(other_user.last_name, '')

		unverified_change = self.post_json(
			'/api/accounts/profile/',
			{'full_name': 'Ada', 'email': 'new@example.com'},
		)
		self.assertEqual(unverified_change.status_code, 405)

		requested = self.post_json(
			'/api/accounts/email-change/',
			{'email': 'new@example.com'},
		)
		self.assertEqual(requested.status_code, 202)
		self.assertEqual(user.email, 'admin@example.com')
		self.assertEqual(len(mail.outbox), 1)
		verification_url = next(
			line for line in mail.outbox[0].body.splitlines()
			if 'email_change=' in line
		)
		token = parse_qs(urlparse(verification_url).query)['email_change'][0]
		confirmed = self.post_json(
			'/api/accounts/email-change/confirm/',
			{'token': token},
		)
		self.assertEqual(confirmed.status_code, 200)
		user.refresh_from_db()
		self.assertEqual(user.email, 'new@example.com')
		self.assertTrue(VerifiedEmail.objects.filter(user=user, email=user.email).exists())
		reused = self.post_json(
			'/api/accounts/email-change/confirm/',
			{'token': token},
		)
		self.assertEqual(reused.status_code, 400)

	def test_account_settings_require_authentication(self):
		unauthenticated = Client()
		for path, method in (
			('/api/accounts/profile/', 'patch'),
			('/api/accounts/email-change/', 'post'),
			('/api/accounts/password-change/', 'post'),
		):
			response = getattr(unauthenticated, method)(path, data='{}', content_type='application/json')
			self.assertEqual(response.status_code, 302)

	def test_password_change_checks_current_password_and_keeps_session(self):
		user = get_user_model().objects.create_user(
			username='password@example.com',
			email='password@example.com',
			password='A-strong-password-42!',
		)
		self.client.force_login(user)
		denied = self.post_json(
			'/api/accounts/password-change/',
			{
				'current_password': 'wrong-password',
				'new_password': 'Another-strong-password-53!',
			},
		)
		self.assertEqual(denied.status_code, 400)
		accepted = self.post_json(
			'/api/accounts/password-change/',
			{
				'current_password': 'A-strong-password-42!',
				'new_password': 'Another-strong-password-53!',
			},
		)
		self.assertEqual(accepted.status_code, 200)
		self.assertTrue(self.client.get('/api/accounts/me/').wsgi_request.user.is_authenticated)
		user.refresh_from_db()
		self.assertTrue(user.check_password('Another-strong-password-53!'))
