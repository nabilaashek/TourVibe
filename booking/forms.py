from django import forms

from userprofile.forms import add_bootstrap
from userprofile.models import bd_phone


class AddToCartForm(forms.Form):
    travelers = forms.IntegerField(min_value=1, max_value=20, initial=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)


class CheckoutForm(forms.Form):
    contact_name = forms.CharField(max_length=100)
    contact_phone = forms.CharField(max_length=14, validators=[bd_phone],
                                    widget=forms.TextInput(attrs={'placeholder': '01XXXXXXXXX'}))
    note = forms.CharField(max_length=300, required=False,
                           widget=forms.TextInput(attrs={'placeholder': 'Optional, e.g. vegetarian meals'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)
