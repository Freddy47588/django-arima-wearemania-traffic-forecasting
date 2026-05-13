from django import forms


class UploadCSVForm(forms.Form):
    csv_file = forms.FileField(
        label="Upload CSV GA4 / Looker Studio",
        help_text="Format wajib: Date, Page path, Views"
    )