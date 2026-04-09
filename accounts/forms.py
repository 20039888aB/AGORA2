from django import forms
from django.contrib.auth import authenticate, login
from .models import User
from organizations.models import Organization

class SignUpForm(forms.ModelForm):
    """User registration form"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': ' ',
            'required': True
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': ' ',
            'required': True
        })
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.filter(is_active=True).order_by('name'),
        empty_label="Select your organization",
        widget=forms.Select(attrs={
            'class': 'form-input',
            'required': True
        })
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'organization', 'password', 'confirm_password']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': ' ',
                'required': True
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': ' ',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': ' ',
                'required': True
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].label = 'Email Address'
        self.fields['first_name'].label = 'First Name'
        self.fields['last_name'].label = 'Last Name'
        self.fields['password'].label = 'Password'
        self.fields['confirm_password'].label = 'Confirm Password'
        self.fields['organization'].label = 'Organization'
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        # Password validation
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'STUDENT'  # Default role for new signups
        user.organization = self.cleaned_data['organization']
        
        if commit:
            user.save()
        return user
    
    def clean(self):
        cleaned_data = self.cleaned_data
        
        # Custom validation for our fields
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        organization = cleaned_data.get('organization')
        
        # Email validation
        if not email:
            raise forms.ValidationError("Email is required.")
        
        # Password validation
        if not password:
            raise forms.ValidationError("Password is required.")
            
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        
        # Organization validation
        if not organization:
            raise forms.ValidationError("Organization is required.")
        
        return cleaned_data


class ProfileEditForm(forms.ModelForm):
    """Form for editing user profile details"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'bio', 'date_of_birth', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name', 'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name', 'autocomplete': 'family-name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address', 'autocomplete': 'email'}),
            'phone': forms.TextInput(attrs={'placeholder': '+254 700 000 000', 'autocomplete': 'tel'}),
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write a short bio about yourself…'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'avatar': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This email is already in use by another account.')
        return email


class LoginForm(forms.Form):
    """User login form"""
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-input',
        'placeholder': ' ',
        'required': True,
        'autocomplete': 'email'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-input',
        'placeholder': ' ',
        'required': True,
        'autocomplete': 'current-password'
    }))
    remember_me = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={
        'class': 'form-checkbox'
    }))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].label = 'Email Address'
        self.fields['password'].label = 'Password'
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        
        if email and password:
            user = authenticate(request=None, email=email, password=password)
            if not user:
                raise forms.ValidationError("Invalid email or password.")
            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")
            self.user = user
        return self.cleaned_data
