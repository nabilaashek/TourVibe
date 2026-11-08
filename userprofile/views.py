from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import LoginForm, ProfileForm, SignUpForm, StyledPasswordChangeForm


class LoginPage(auth_views.LoginView):
    template_name = 'registration/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class PasswordChangePage(auth_views.PasswordChangeView):
    template_name = 'userprofile/password_change.html'
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        messages.success(self.request, 'Password changed successfully.')
        return super().form_valid(form)


def signup(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome to TourVibe, {user.profile.display_name}!')
        return redirect('dashboard')
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'userprofile/profile.html', {'profile': request.user.profile})


@login_required
def edit_profile(request):
    profile = request.user.profile
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    return render(request, 'userprofile/edit_profile.html', {'form': form})
