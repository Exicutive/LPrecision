from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('csrf/', views.csrf_token, name='csrf-token'),
    path('register/', views.register, name='register'),
    path('login/', views.sign_in, name='login'),
    path('me/', views.current_user, name='current-user'),
    path('profile/', views.update_profile, name='update-profile'),
    path('email-change/', views.request_email_change, name='request-email-change'),
    path('email-change/confirm/', views.confirm_email_change, name='confirm-email-change'),
    path('password-change/', views.change_password, name='change-password'),
    path('logout/', views.sign_out, name='logout'),
    path('password-reset/', views.password_reset, name='password-reset'),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/api/accounts/password-reset-complete/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]
