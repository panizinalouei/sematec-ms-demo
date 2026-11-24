from django.urls import path

from . import views

urlpatterns = [
    # ورود — صفحه اول سامانه
    path("", views.login_view, name="login"),
    path("login/", views.login_view, name="login_alias"),
    path("login/otp/", views.otp_login, name="otp_login"),
    path("login/otp/verify/", views.otp_verify, name="otp_verify"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("courses/", views.course_list, name="courses"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
    path("courses/<slug:slug>/enroll/", views.course_enroll, name="course_enroll"),
    path("teachers/", views.teacher_list, name="teachers"),
    path("teachers/<int:pk>/", views.teacher_detail, name="teacher_detail"),

    path("my-courses/", views.my_courses, name="my_courses"),
    path("learn/<slug:slug>/", views.learn_course, name="learn_course"),
    path("learn/<slug:slug>/lesson/<int:lesson_id>/", views.lesson_view, name="lesson_view"),
    path("learn/<slug:slug>/lesson/<int:lesson_id>/complete/", views.complete_lesson, name="complete_lesson"),

    path("assignments/", views.assignment_list, name="assignments"),
    path("assignments/<int:pk>/", views.assignment_detail, name="assignment_detail"),
    path("grading/", views.grading_queue, name="grading"),
    path("grading/<int:pk>/", views.grade_submission, name="grade_submission"),

    path("exams/", views.exam_list, name="exams"),
    path("exams/<int:pk>/", views.exam_start, name="exam_start"),
    path("exams/result/<int:pk>/", views.exam_result, name="exam_result"),

    path("attendance/", views.attendance_report, name="attendance"),
    path("attendance/classroom/<int:classroom_id>/", views.attendance_board, name="attendance_board"),

    path("certificates/", views.certificate_list, name="certificates"),
    path("certificates/issue/<int:enrollment_id>/", views.certificate_issue, name="certificate_issue"),
    path("verify/", views.certificate_verify, name="verify"),
    path("verify/<str:serial>/", views.certificate_verify, name="verify_serial"),
    path("certificates/<str:serial>/", views.certificate_detail, name="certificate_detail"),

    path("notifications/", views.notifications_list, name="notifications"),
    path("notifications/<int:pk>/read/", views.notification_read, name="notification_read"),
    path("notifications/read-all/", views.notifications_read_all, name="notifications_read_all"),

    path("manage/courses/", views.manage_courses, name="manage_courses"),
    path("manage/courses/new/", views.course_create, name="course_create"),
    path("manage/courses/<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("manage/users/", views.manage_users, name="manage_users"),
    path("manage/enrollments/", views.enrollments_admin, name="enrollments_admin"),
    path("reports/", views.reports, name="reports"),
]

handler403 = "lms.views.error_403"
handler404 = "lms.views.error_404"
handler500 = "lms.views.error_500"
