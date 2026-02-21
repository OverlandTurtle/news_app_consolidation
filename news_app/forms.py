from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Article, Publisher, Newsletter


class CustomUserCreationForm(UserCreationForm):
    ROLE_EMPTY = ""

    role = forms.ChoiceField(
        choices=[(ROLE_EMPTY, "Select role...")] + CustomUser.ROLE_CHOICES,
        required=True,
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("username", "email", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

        self.fields["role"].widget.attrs["class"] = "form-select"

    def clean_role(self):
        # Defensive check:
        # ensure the user didn’t leave the placeholder selected.

        role = self.cleaned_data.get("role")
        if role == self.ROLE_EMPTY:
            raise forms.ValidationError("Please select a role.")
        return role


class ArticleForm(forms.ModelForm):
    """
    Form for journalists to create/edit an article.

    - only expose fields the journalist should type.
    - journalist and is_approved are controlled in the view.
    """

    class Meta:
        model = Article
        fields = ["publisher", "title", "summary", "body"]

        widgets = {
            "summary": forms.Textarea(attrs={"rows": 3}),
            "body": forms.Textarea(attrs={"rows": 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["publisher"].required = False

        for field_name, field in self.fields.items():
            if field_name == "publisher":
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

    def clean_title(self):
        # Basic validation
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters long.")

        return title

    def clean_body(self):
        # Basic validation
        body = self.cleaned_data.get("body", "").strip()
        if len(body) < 20:
            raise forms.ValidationError("Body must be at least 20 characters long.")

        return body


class PublisherForm(forms.ModelForm):
    """
    Publisher create form (Editor only view will use this).
    - name required
    - website optional
    """

    class Meta:
        model = Publisher
        fields = ["name", "website"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Website is optional
        self.fields["website"].required = False

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()

        if len(name) < 2:
            raise forms.ValidationError(
                "Publisher name must be at least 2 characters long."
            )

        # Avoid duplicates
        qs = Publisher.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("A publisher with this name already exists.")

        return name


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = ["publisher", "title", "body"]

    def __init__(self, *args, **kwargs):
        journalist_user = kwargs.pop("journalist_user", None)
        super().__init__(*args, **kwargs)

        # Publisher optional, independent newsletters allowed.
        self.fields["publisher"].required = False

        # Restrict publisher dropdown to journalist's assigned publishers
        if journalist_user is not None:
            self.fields["publisher"].queryset = Publisher.objects.filter(
                journalists=journalist_user
            ).order_by("name")

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters long.")
        return title

    def clean_body(self):
        body = (self.cleaned_data.get("body") or "").strip()
        if len(body) < 20:
            raise forms.ValidationError("Body must be at least 20 characters long.")
        return body
