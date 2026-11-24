
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator
from django.db import transaction

from .models import (Assignment, Course, EducationCategory, Exam, Lesson,
                     Notification, Person, Student, StudentCourseTeacher,
                     Teacher, Users)

phone_validator = RegexValidator(r"^09\d{9}$", "شماره موبایل باید ۱۱ رقم و با ۰۹ شروع شود.")


class LoginForm(forms.Form):
    username = forms.CharField(
        label="نام کاربری یا ایمیل",
        widget=forms.TextInput(
            attrs={"placeholder": "student یا student@sematec.ir", "autocomplete": "username"}
        ),
    )
    password = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput(
            attrs={"placeholder": "••••••••", "autocomplete": "current-password"}
        ),
    )
    remember = forms.BooleanField(label="مرا به خاطر بسپار", required=False)

    def clean(self):
        data = super().clean()
        username, password = data.get("username"), data.get("password")
        if username and password:
            user = authenticate(self.request, username=username, password=password)
            if not user:
                raise forms.ValidationError("نام کاربری یا رمز عبور نادرست است.")
            data["user"] = user
        return data

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)


class RegisterForm(forms.Form):
    first_name = forms.CharField(label="نام", max_length=60)
    last_name = forms.CharField(label="نام خانوادگی", max_length=60)
    phone = forms.CharField(label="موبایل", max_length=11, validators=[phone_validator])
    email = forms.EmailField(label="ایمیل")
    password1 = forms.CharField(label="رمز عبور", min_length=8,
                                widget=forms.PasswordInput(attrs={"placeholder": "حداقل ۸ کاراکتر"}))
    password2 = forms.CharField(label="تکرار رمز عبور", widget=forms.PasswordInput)

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        if Person.objects.filter(phone_number=phone).exists():
            raise forms.ValidationError("این شماره قبلاً ثبت شده است.")
        return phone

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if Person.objects.filter(email_address__iexact=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            raise forms.ValidationError("رمز عبور و تکرار آن یکسان نیستند.")
        return data

    @transaction.atomic
    def save(self):
        d = self.cleaned_data
        person = Person.objects.create(
            persian_first_name=d["first_name"],
            persian_last_name=d["last_name"],
            phone_number=d["phone"],
            email_address=d["email"],
        )
        student = Student.objects.create(
            person=person, student_code=f"ST-{Student.objects.count() + 1001}"
        )
        base = d["email"].split("@")[0]
        username = base
        n = 1
        while Users.objects.filter(username=username).exists():
            n += 1
            username = f"{base}{n}"
        user = Users.objects.create(
            username=username,
            password=make_password(d["password1"]),
            first_name=d["first_name"],
            last_name=d["last_name"],
            role=Users.Role.STUDENT,
            person=person,
        )
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ["persian_first_name", "persian_last_name", "phone_number",
                  "email_address", "home_address", "photo"]
        labels = {
            "persian_first_name": "نام",
            "persian_last_name": "نام خانوادگی",
            "phone_number": "موبایل",
            "email_address": "ایمیل",
            "home_address": "آدرس",
            "photo": "تصویر پروفایل",
        }


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["course_code", "name", "english_name", "slug", "category", "level",
                  "course_type", "duration", "capacity", "tuition", "description",
                  "syllabus", "cover", "status", "prerequisites"]
        labels = {
            "course_code": "کد دوره", "name": "نام دوره", "english_name": "نام انگلیسی",
            "slug": "نامک (آدرس)", "category": "دسته‌بندی", "level": "سطح",
            "course_type": "نوع برگزاری", "duration": "مدت (ساعت)", "capacity": "ظرفیت",
            "tuition": "شهریه (تومان)", "description": "توضیحات", "syllabus": "سرفصل",
            "cover": "تصویر دوره", "status": "وضعیت", "prerequisites": "پیش‌نیاز",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "syllabus": forms.Textarea(attrs={"rows": 6}),
        }


class SubmissionForm(forms.Form):
    note = forms.CharField(
        label="توضیح", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )
    file = forms.FileField(label="فایل پاسخ", required=False)


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ["course", "title", "description", "due_date", "max_score",
                  "allow_resubmit", "attachment"]


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ["course", "title", "description", "duration_minutes", "start_at",
                  "end_at", "pass_score", "max_attempts", "negative_marking",
                  "shuffle_questions", "questions"]


AttendanceFormSet = forms.modelformset_factory(
    StudentCourseTeacher, fields=[], extra=0
)
