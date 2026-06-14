from django import forms
from .models import User, UserProfile

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'phone', 'role','password' ]
    def clean(self):
        cleaned_data = super(UserForm, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError(
                "Password does not match!"
            )

class LoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control','placeholder': 'Enter Username' })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control','placeholder': 'Enter password' })
    )

    
class UserProfileForm(forms.ModelForm):

    class Meta:
        model = UserProfile
        fields = [
            'picture_profile',
            'cover_photo',
            'country',
            'province',
            'district',
            'sector',
            'cell',
            'village',
            'personal_id'
        ]

        widgets = {
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Select Country'
            }),

            'province': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Province'
            }),

            'district': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter District'
            }),

            'sector': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Sector'
            }),

            'cell': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Cell'
            }),

            'village': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter Village'
            }),

            'personal_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter National ID'
            }),
        }