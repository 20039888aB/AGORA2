from django import forms
from .models import CourseDocument, Course


class CourseDocumentForm(forms.ModelForm):
    """Enhanced form for course documents with PDF support"""
    
    class Meta:
        model = CourseDocument
        fields = [
            'title', 'description', 'file', 'order', 'file_type', 'is_required',
            'is_downloadable', 'is_printable', 'category', 'is_public', 
            'access_level', 'published_at'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
                'placeholder': 'Enter document title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
                'rows': 4,
                'placeholder': 'Enter document description'
            }),
            'file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
                'accept': '.pdf,.doc,.docx,.ppt,.pptx,.txt'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
                'min': 1,
                'placeholder': 'Order in course'
            }),
            'file_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'access_level': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
            }),
            'published_at': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
                'placeholder': 'YYYY-MM-DD HH:MM:SS'
            }),
            'is_required': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'is_downloadable': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'is_printable': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)
        
        # If we have a course, set the initial order
        if self.course:
            last_order = CourseDocument.objects.filter(course=self.course).count()
            self.fields['order'].initial = last_order + 1

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 50MB)
            if file.size > 50 * 1024 * 1024:
                raise forms.ValidationError('File size must be less than 50MB')
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.txt']
            file_extension = file.name.lower().split('.')[-1] if '.' in file.name else ''
            
            if f'.{file_extension}' not in allowed_extensions:
                raise forms.ValidationError(
                    'File type not allowed. Please upload PDF, Word, PowerPoint, or Text files.'
                )
        
        return file

    def clean(self):
        cleaned_data = super().clean()
        
        # Validate published_at is not in the past
        published_at = cleaned_data.get('published_at')
        if published_at and published_at > timezone.now():
            raise forms.ValidationError('Publish date cannot be in the future.')
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.course:
            instance.course = self.course
        
        # Set file size
        if instance.file:
            instance.file_size = instance.file.size
        
        if commit:
            instance.save()
        
        return instance


class CourseDocumentBulkForm(forms.Form):
    """Enhanced form for bulk uploading documents to a course"""
    files = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent',
            'accept': '.pdf,.doc,.docx,.ppt,.pptx,.txt'
        }),
        required=False,
        help_text='Select files to upload. Each file will be created as a separate document.'
    )
    
    category = forms.ChoiceField(
        choices=CourseDocument._meta.get_field('category').choices,
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
        })
    )
    
    is_required = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500'
        })
    )
    
    access_level = forms.ChoiceField(
        choices=CourseDocument._meta.get_field('access_level').choices,
        initial='ENROLLED',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent'
        })
    )
