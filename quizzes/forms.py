"""Forms for the VIEW layer."""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Quiz, User


class BootstrapMixin:
    """Apply Bootstrap classes to every widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check-input")
            elif isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select")
            else:
                w.attrs.setdefault("class", "form-control")


class RegistrationForm(BootstrapMixin, UserCreationForm):
    """Sign up as a Student or a Lecturer."""

    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    role = forms.ChoiceField(
        choices=[(User.Role.STUDENT, "Student"), (User.Role.LECTURER, "Lecturer")],
        initial=User.Role.STUDENT,
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
        return user


class QuizForm(BootstrapMixin, forms.ModelForm):
    """Lecturer creates or edits a quiz."""

    class Meta:
        model = Quiz
        fields = ["topic", "title", "description", "difficulty", "time_limit_minutes", "pass_mark", "is_published"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class QuestionForm(BootstrapMixin, forms.Form):
    """Add one question plus four answer choices in a single step."""

    text = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), label="Question")
    subtopic = forms.CharField(max_length=120, required=False)
    explanation = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False)
    choice_1 = forms.CharField(max_length=255, label="Choice A")
    choice_2 = forms.CharField(max_length=255, label="Choice B")
    choice_3 = forms.CharField(max_length=255, label="Choice C", required=False)
    choice_4 = forms.CharField(max_length=255, label="Choice D", required=False)
    correct = forms.ChoiceField(
        choices=[("1", "A"), ("2", "B"), ("3", "C"), ("4", "D")],
        label="Correct answer",
    )
