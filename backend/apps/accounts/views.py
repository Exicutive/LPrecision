import json
import hashlib
import secrets
import smtplib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import EmailChangeRequest, VerifiedEmail

User = get_user_model()


def _read_payload(request):
	try:
		payload = json.loads(request.body)
	except (UnicodeDecodeError, json.JSONDecodeError):
		return None
	return payload if isinstance(payload, dict) else None


def _user_data(user):
	# Import here to keep the account app independent during Django startup.
	from apps.companies.models import CompanyMembership
	from apps.platform_admin.permissions import is_platform_admin

	company_memberships = CompanyMembership.objects.filter(
		user=user,
		role=CompanyMembership.Role.COMPANY_ADMIN,
		is_active=True,
		company__status="active",
	).select_related("company") if user.is_authenticated else []
	return {
		'id': user.pk,
		'email': user.email,
		'full_name': user.get_full_name() or user.username,
		'is_staff': user.is_staff,
		'is_platform_admin': is_platform_admin(user),
		'company_admin_companies': [
			{'id': membership.company_id, 'name': membership.company.name}
			for membership in company_memberships
		],
	}


@require_GET
@ensure_csrf_cookie
def csrf_token(request):
	return JsonResponse({'detail': 'CSRF cookie set.'})


@require_POST
def register(request):
	payload = _read_payload(request)
	if payload is None:
		return JsonResponse({'detail': 'Send a valid JSON request.'}, status=400)

	full_name = str(payload.get('full_name', '')).strip()
	email = str(payload.get('email', '')).strip().lower()
	password = payload.get('password', '')
	if not full_name or not email or not isinstance(password, str):
		return JsonResponse(
			{'detail': 'Full name, email address, and password are required.'},
			status=400,
		)
	if len(email) > 150 or '@' not in email:
		return JsonResponse({'detail': 'Enter a valid email address.'}, status=400)
	if User.objects.filter(email__iexact=email).exists():
		return JsonResponse(
			{'detail': 'An account with this email address already exists.'},
			status=400,
		)

	candidate = User(username=email, email=email)
	try:
		validate_password(password, user=candidate)
	except ValidationError as error:
		return JsonResponse({'detail': ' '.join(error.messages)}, status=400)

	name_parts = full_name.split(maxsplit=1)
	user = User.objects.create_user(
		username=email,
		email=email,
		password=password,
		first_name=name_parts[0],
		last_name=name_parts[1] if len(name_parts) > 1 else '',
	)
	login(request, user)
	return JsonResponse({'user': _user_data(user)}, status=201)


@require_POST
def sign_in(request):
	payload = _read_payload(request)
	if payload is None:
		return JsonResponse({'detail': 'Send a valid JSON request.'}, status=400)

	email = str(payload.get('email', '')).strip().lower()
	password = payload.get('password', '')
	if not email or not isinstance(password, str):
		return JsonResponse(
			{'detail': 'Email address and password are required.'}, status=400
		)

	user_record = User.objects.filter(email__iexact=email).first()
	user = authenticate(
		request,
		username=user_record.username if user_record else email,
		password=password,
	)
	if user is None:
		return JsonResponse({'detail': 'Email or password is incorrect.'}, status=401)

	login(request, user)
	return JsonResponse({'user': _user_data(user)})


@require_GET
def current_user(request):
	if not request.user.is_authenticated:
		return JsonResponse({'detail': 'Sign in is required.'}, status=401)
	return JsonResponse({'user': _user_data(request.user)})


@require_POST
def sign_out(request):
	logout(request)
	return JsonResponse({'detail': 'Signed out.'})


@require_POST
def password_reset(request):
	payload = _read_payload(request)
	if payload is None:
		return JsonResponse({'detail': 'Send a valid JSON request.'}, status=400)

	email = str(payload.get('email', '')).strip().lower()
	if not email or '@' not in email:
		return JsonResponse({'detail': 'Enter a valid email address.'}, status=400)

	form = PasswordResetForm({'email': email})
	if form.is_valid():
		form.save(
			request=request,
			use_https=request.is_secure(),
			email_template_name='accounts/password_reset_email.txt',
			subject_template_name='accounts/password_reset_subject.txt',
		)
	return JsonResponse(
		{
			'detail': (
				'If an account exists for that email address, a password reset link has been sent.'
			)
		}
	)


@require_http_methods(['PATCH'])
@login_required
def update_profile(request):
	payload = _read_payload(request)
	if payload is None:
		return JsonResponse({'detail': 'Send a valid JSON request.'}, status=400)
	if set(payload) != {'full_name'}:
		return JsonResponse({'detail': 'Only the account name can be changed here.'}, status=400)
	if not isinstance(payload.get('full_name'), str):
		return JsonResponse({'detail': 'Full name must be text.'}, status=400)
	full_name = payload['full_name'].strip()
	if not full_name or len(full_name) > 200:
		return JsonResponse({'detail': 'Enter a name between 1 and 200 characters.'}, status=400)
	name_parts = full_name.split(maxsplit=1)
	request.user.first_name = name_parts[0]
	request.user.last_name = name_parts[1] if len(name_parts) > 1 else ''
	request.user.save(update_fields=('first_name', 'last_name'))
	return JsonResponse({'user': _user_data(request.user)})


@require_POST
@login_required
def request_email_change(request):
	payload = _read_payload(request)
	if payload is None:
		return JsonResponse({'detail': 'Send a valid JSON request.'}, status=400)
	if set(payload) != {'email'} or not isinstance(payload.get('email'), str):
		return JsonResponse({'detail': 'Provide only the new email address.'}, status=400)
	email = payload['email'].strip().lower()
	try:
		validate_email(email)
	except ValidationError:
		return JsonResponse({'detail': 'Enter a valid email address.'}, status=400)
	if len(email) > 254:
		return JsonResponse({'detail': 'Email address must be 254 characters or fewer.'}, status=400)
	if email.casefold() == request.user.email.casefold():
		return JsonResponse({'detail': 'This is already your account email address.'}, status=400)
	if User.objects.filter(email__iexact=email).exists():
		return JsonResponse({'detail': 'An account with this email address already exists.'}, status=400)
	if VerifiedEmail.objects.filter(email__iexact=email).exclude(user=request.user).exists():
		return JsonResponse({'detail': 'This email address is verified on another account.'}, status=400)

	raw_token = secrets.token_urlsafe(32)
	with transaction.atomic():
		EmailChangeRequest.objects.filter(user=request.user, used_at__isnull=True).update(
			used_at=timezone.now()
		)
		change = EmailChangeRequest.objects.create(
			user=request.user,
			email=email,
			token_hash=hashlib.sha256(raw_token.encode('utf-8')).hexdigest(),
			expires_at=timezone.now() + timedelta(hours=24),
		)
	verification_url = (
		f'{settings.FRONTEND_URL}/admin/?email_change={raw_token}'
	)
	try:
		sent = send_mail(
			'Verify your TerraLedger account email',
			(
				'Confirm your new TerraLedger account email within 24 hours by opening '
				f'this link: {verification_url}\n\n'
				'If you did not request this change, you can ignore this message.'
			),
			settings.DEFAULT_FROM_EMAIL,
			[email],
			fail_silently=False,
		)
	except (OSError, smtplib.SMTPException, RuntimeError):
		change.delete()
		return JsonResponse(
			{'detail': 'The verification email could not be sent. Your account email was not changed.'},
			status=503,
		)
	if sent != 1:
		change.delete()
		return JsonResponse(
			{'detail': 'The email provider did not accept the verification message.'},
			status=503,
		)
	return JsonResponse(
		{'detail': f'A verification link was sent to {email}. It expires in 24 hours.'},
		status=202,
	)


@require_POST
def confirm_email_change(request):
	payload = _read_payload(request)
	token = str((payload or {}).get('token', ''))
	if not token or len(token) > 200:
		return JsonResponse({'detail': 'A valid email verification token is required.'}, status=400)
	token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
	with transaction.atomic():
		change = (
			EmailChangeRequest.objects.select_for_update()
			.select_related('user')
			.filter(token_hash=token_hash, used_at__isnull=True)
			.first()
		)
		if not change:
			return JsonResponse({'detail': 'This email verification link is invalid or already used.'}, status=400)
		if change.expires_at <= timezone.now():
			change.used_at = timezone.now()
			change.save(update_fields=('used_at',))
			return JsonResponse({'detail': 'This email verification link has expired.'}, status=400)
		if User.objects.filter(email__iexact=change.email).exclude(pk=change.user_id).exists():
			return JsonResponse({'detail': 'This email address is now associated with another account.'}, status=409)
		if VerifiedEmail.objects.filter(email__iexact=change.email).exclude(user_id=change.user_id).exists():
			return JsonResponse({'detail': 'This email address is verified on another account.'}, status=409)
		change.user.email = change.email
		change.user.save(update_fields=('email',))
		if not VerifiedEmail.objects.filter(email__iexact=change.email).exists():
			VerifiedEmail.objects.create(user=change.user, email=change.email)
		change.used_at = timezone.now()
		change.save(update_fields=('used_at',))
		EmailChangeRequest.objects.filter(
			user=change.user, used_at__isnull=True
		).exclude(pk=change.pk).update(used_at=timezone.now())
	return JsonResponse({
		'detail': 'Your TerraLedger account email has been verified and updated.',
		'user': _user_data(change.user),
	})


@require_POST
@login_required
def change_password(request):
	payload = _read_payload(request)
	if payload is None:
		return JsonResponse({'detail': 'Send a valid JSON request.'}, status=400)
	current_password = payload.get('current_password')
	new_password = payload.get('new_password')
	if not isinstance(current_password, str) or not isinstance(new_password, str):
		return JsonResponse({'detail': 'Current and new passwords are required.'}, status=400)
	if not request.user.check_password(current_password):
		return JsonResponse({'detail': 'Current password is incorrect.'}, status=400)
	try:
		validate_password(new_password, user=request.user)
	except ValidationError as error:
		return JsonResponse({'detail': ' '.join(error.messages)}, status=400)
	request.user.set_password(new_password)
	request.user.save(update_fields=('password',))
	update_session_auth_hash(request, request.user)
	return JsonResponse({'detail': 'Your password has been updated.'})
