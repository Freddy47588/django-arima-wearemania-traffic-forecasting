from django import forms


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Pilih file CSV",
        help_text="Upload file CSV dengan kolom wajib: date, page_path, views.",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "file-input",
                "accept": ".csv,text/csv",
            }
        ),
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data.get("csv_file")

        if not csv_file:
            raise forms.ValidationError("File CSV wajib diupload.")

        file_name = csv_file.name.lower()

        if not file_name.endswith(".csv"):
            raise forms.ValidationError("File harus berformat .csv.")

        max_size = 20 * 1024 * 1024  # 20 MB

        if csv_file.size > max_size:
            raise forms.ValidationError("Ukuran file maksimal 20 MB.")

        return csv_file