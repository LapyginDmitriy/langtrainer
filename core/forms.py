from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Word

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class WordForm(forms.ModelForm):
    class Meta:
        model = Word
        fields = ['word', 'translation', 'transcription', 'part_of_speech', 'audio_file', 'lesson']