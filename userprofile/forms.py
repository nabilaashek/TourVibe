from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile, bd_phone


def add_bootstrap(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
            widget.attrs.setdefault('class', 'form-check-input')
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            widget.attrs.setdefault('class', 'form-select')
        else:
            widget.attrs.setdefault('class', 'form-control')


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)


class SignUpForm(UserCreationForm):
    email = forms.EmailField()
    full_name = forms.CharField(max_length=100)
    phone_number = forms.CharField(max_length=14, required=False, validators=[bd_phone])

    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'phone_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        # Public sign-up always creates a normal traveler, never an admin
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            profile = user.profile
            profile.full_name = self.cleaned_data['full_name']
            profile.phone_number = self.cleaned_data.get('phone_number', '')
            profile.save()
        return user


class ProfileForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = UserProfile
        fields = ['image', 'full_name', 'email', 'phone_number', 'home_city', 'address']
        widgets = {'address': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].initial = self.instance.user.email
        add_bootstrap(self)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.user.pk).exists():
            raise forms.ValidationError('Another account already uses this email.')
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.email = self.cleaned_data['email']
        if commit:
            profile.user.save()
            profile.save()
        return profile


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)
