from django import forms
from django.utils import timezone

from booking.models import Transport
from tour.forms import MONTH_CHOICES
from tour.models import Category, TourDestination
from userprofile.forms import add_bootstrap

from .models import TripPlan


class PlannerForm(forms.Form):
    places = forms.ModelMultipleChoiceField(
        queryset=TourDestination.objects.active().select_related('division').order_by('division__name', 'name'),
        to_field_name='slug',
        widget=forms.CheckboxSelectMultiple,
        help_text='Tick up to 8 places. We will find a short route for you.',
    )
    days = forms.IntegerField(min_value=1, max_value=30, initial=3)
    travelers = forms.IntegerField(min_value=1, max_value=20, initial=2)
    budget = forms.ChoiceField(choices=TripPlan.BUDGET_CHOICES, initial='STANDARD')
    transport = forms.ChoiceField(choices=Transport.choices, initial='BUS')
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    title = forms.CharField(max_length=120, required=False,
                            widget=forms.TextInput(attrs={'placeholder': 'e.g. Winter trip with friends'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)
        self.fields['places'].label_from_instance = lambda p: f'{p.name} ({p.division.name})'
        self.fields['start_date'].widget.attrs['min'] = timezone.localdate().isoformat()

    def clean_start_date(self):
        day = self.cleaned_data['start_date']
        if day < timezone.localdate():
            raise forms.ValidationError('Start date cannot be in the past.')
        return day

    def clean(self):
        data = super().clean()
        places, days = data.get('places'), data.get('days')
        if places and len(places) > 8:
            self.add_error('places', 'Choose at most 8 places.')
        if places and days and days < len(places):
            self.add_error('days', 'Keep at least one day for each place.')
        return data


class RecommendForm(forms.Form):
    month = forms.ChoiceField(choices=MONTH_CHOICES[1:])
    daily_budget = forms.IntegerField(label='Daily budget per person (৳)', min_value=500, max_value=100000,
                                      required=False, widget=forms.NumberInput(attrs={'placeholder': 'e.g. 3000'}))
    categories = forms.ModelMultipleChoiceField(Category.objects.all(), required=False,
                                                widget=forms.CheckboxSelectMultiple, label='Interests')
    max_km = forms.IntegerField(label='Max distance from Dhaka (km)', min_value=10, max_value=1000, required=False,
                                widget=forms.NumberInput(attrs={'placeholder': 'Any'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)
