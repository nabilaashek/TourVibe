from django import forms
from django.utils import timezone

from userprofile.forms import add_bootstrap

from .models import MONTHS, Category, Division, Review, TourDestination, TourImage

MONTH_CHOICES = [('', 'Any month')] + [(str(i), m) for i, m in enumerate(MONTHS, start=1)]
SORT_CHOICES = [
    ('name', 'Name (A-Z)'),
    ('rating', 'Top rated'),
    ('cheap', 'Price: low to high'),
    ('expensive', 'Price: high to low'),
    ('popular', 'Most reviewed'),
]


class SearchForm(forms.Form):
    q = forms.CharField(label='Search', required=False,
                        widget=forms.TextInput(attrs={'placeholder': 'Search place or district'}))
    division = forms.ModelChoiceField(Division.objects.all(), required=False, empty_label='All divisions',
                                      to_field_name='slug')
    category = forms.ModelChoiceField(Category.objects.all(), required=False, empty_label='All types',
                                      to_field_name='slug')
    month = forms.ChoiceField(choices=MONTH_CHOICES, required=False)
    max_price = forms.IntegerField(required=False, min_value=0,
                                   widget=forms.NumberInput(attrs={'placeholder': 'Max ৳ per day'}))
    sort = forms.ChoiceField(choices=SORT_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)


class TourDestinationForm(forms.ModelForm):
    class Meta:
        model = TourDestination
        fields = ['name', 'division', 'district', 'category', 'short_description', 'description', 'highlights',
                  'tips', 'best_months', 'price_per_day', 'entry_fee', 'latitude', 'longitude', 'cover_image',
                  'is_featured', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'highlights': forms.Textarea(attrs={'rows': 3}),
            'tips': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)


class TourImageForm(forms.ModelForm):
    class Meta:
        model = TourImage
        fields = ['image', 'caption']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(choices=[(i, f'{i} star' + ('s' if i > 1 else '')) for i in range(5, 0, -1)],
                                    coerce=int)

    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment', 'visited_on']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3}),
            'visited_on': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap(self)

    def clean_visited_on(self):
        day = self.cleaned_data.get('visited_on')
        if day and day > timezone.localdate():
            raise forms.ValidationError('Visit date cannot be in the future.')
        return day
