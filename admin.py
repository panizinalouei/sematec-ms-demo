from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (Assignment, AssignmentSubmission, Attendance, AuditLog,
                     Certificate, Certification, ClassSession, Classroom,
                     Course, Department, Education, EducationCategory, Employee,
                     Exam, ExamAnswer, ExamAttempt, Job, Lesson, LessonProgress,
                     Notification, Person, Question, Student,
                     StudentCourseTeacher, StudySession, Teacher,
                     TeacherCertification, Users)


@admin.register(Users)
class UsersAdmin(BaseUserAdmin):
    list_display = ("username", "display_name", "role", "is_active", "last_login")
    list_filter = ("role", "is_active")
    search_fields = ("username", "person__persian_first_name", "person__persian_last_name")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("نقش و دسترسی", {"fields": ("role", "is_active", "is_admin")}),
        ("شخص", {"fields": ("person", "first_name", "last_name")}),
    )
    ordering = ("username",)


admin.site.register([Person, Student, Teacher, Employee, Department, Job, Education,
                     Certification, TeacherCertification, EducationCategory, Course,
                     Lesson, LessonProgress, StudySession, Classroom, ClassSession,
                     Attendance, Assignment, AssignmentSubmission, Question, Exam,
                     ExamAttempt, ExamAnswer, Certificate, Notification, AuditLog,
                     StudentCourseTeacher])

admin.site.site_header = "مدیریت سامانه LMS سماتک"
admin.site.site_title = "LMS سماتک"
admin.site.index_title = "داشبورد مدیریت"
