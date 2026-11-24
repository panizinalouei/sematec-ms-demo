
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import (AssignmentForm, AttendanceFormSet, CourseForm, ExamForm,
                    LoginForm, ProfileForm, RegisterForm, SubmissionForm)
from .models import (Assignment, AssignmentSubmission, Attendance, AuditLog,
                     Certificate, ClassSession, Classroom, Course,
                     EducationCategory, Exam, ExamAnswer, ExamAttempt,
                     Lesson, LessonProgress, Notification, Person, Question,
                     Student, StudentCourseTeacher, StudySession, Teacher,
                     Users)
from .services import (DashboardService, build_serial, progress_of, score_attempt)


def _ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def _enrollment_for(user, slug):
    stu = getattr(getattr(user, "person", None), "student_profile", None)
    if not stu:
        return None
    return (
        StudentCourseTeacher.objects.select_related("course", "teacher__person")
        .filter(student=stu, course__slug=slug, is_active=True)
        .first()
    )


# ---------------------------------------------------------------- ورود
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user, backend="lms.auth_backends.EmailOrUsernameBackend")
        user.last_login = timezone.now()
        user.last_login_ip = _ip(request)
        user.save(update_fields=["last_login", "last_login_ip"])
        AuditLog.objects.create(
            user=user, action=AuditLog.Action.LOGIN,
            entity="Users", entity_id=str(user.id), ip=_ip(request),
        )
        if not form.cleaned_data.get("remember"):
            request.session.set_expiry(0)
        messages.success(request, f"خوش آمدید {user.display_name}")
        return redirect(request.GET.get("next") or "dashboard")
    return render(request, "auth/login.html", {"form": form})


def otp_login(request):
    """ورود با موبایل — کد در حالت دمو نمایش داده می‌شود."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        user = Users.objects.filter(person__phone_number=phone, is_active=True).first()
        if not user:
            messages.error(request, "کاربری با این شماره یافت نشد.")
        else:
            request.session["otp_phone"] = phone
            messages.info(
                request, "کد تأیید ارسال شد. (حالت دمو: کد ۱۲۳۴۵۶)"
            )
            return redirect("otp_verify")
    return render(request, "auth/otp.html")


def otp_verify(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    phone = request.session.get("otp_phone")
    if not phone:
        return redirect("otp_login")
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        if code != "123456":
            messages.error(request, "کد وارد شده نادرست است.")
        else:
            user = Users.objects.get(person__phone_number=phone)
            login(request, user, backend="lms.auth_backends.EmailOrUsernameBackend")
            messages.success(request, f"خوش آمدید {user.display_name}")
            return redirect("dashboard")
    return render(request, "auth/otp_verify.html", {"phone": phone})


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="lms.auth_backends.EmailOrUsernameBackend")
        messages.success(request, "ثبت‌نام شما انجام شد.")
        return redirect("courses")
    return render(request, "auth/register.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user.person)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "اطلاعات پروفایل ذخیره شد.")
        return redirect("profile")
    return render(request, "accounts/profile.html", {"form": form})


# ---------------------------------------------------------------- داشبورد
@login_required
def dashboard(request):
    ctx = DashboardService(request.user).build()
    if request.user.role == Users.Role.STUDENT:
        return render(request, "panels/student.html", ctx)
    if request.user.role == Users.Role.TEACHER:
        return render(request, "panels/teacher.html", ctx)
    if request.user.role == Users.Role.STAFF:
        return render(request, "panels/staff.html", ctx)
    if request.user.role == Users.Role.SUPERVISOR:
        return render(request, "panels/supervisor.html", ctx)
    return render(request, "panels/admin.html", ctx)


# ---------------------------------------------------------------- دوره‌ها
def course_list(request):
    courses = (
        Course.objects.filter(status=Course.Status.PUBLISHED)
        .select_related("category")
        .prefetch_related("teachers__person")
    )
    categories = EducationCategory.objects.all()
    cat = request.GET.get("category")
    level = request.GET.get("level")
    q = (request.GET.get("q") or "").strip()
    if cat:
        courses = courses.filter(category__slug=cat)
    if level:
        courses = courses.filter(level=level)
    if q:
        courses = courses.filter(Q(name__icontains=q) | Q(english_name__icontains=q))
    if request.GET.get("sort") == "cheap":
        courses = courses.order_by("tuition")
    elif request.GET.get("sort") == "expensive":
        courses = courses.order_by("-tuition")
    return render(
        request,
        "courses/list.html",
        {
            "courses": courses,
            "categories": categories,
            "active_category": cat,
            "active_level": level,
            "q": q,
        },
    )


def course_detail(request, slug):
    course = get_object_or_404(
        Course.objects.select_related("category").prefetch_related(
            "teachers__person", "lessons", "prerequisites", "classrooms"
        ),
        slug=slug,
    )
    enrollment = _enrollment_for(request.user, slug) if request.user.is_authenticated else None
    return render(
        request,
        "courses/detail.html",
        {"course": course, "enrollment": enrollment},
    )


@login_required
def course_enroll(request, slug):
    course = get_object_or_404(Course, slug=slug)
    student = getattr(getattr(request.user, "person", None), "student_profile", None)
    if not student:
        messages.error(request, "فقط دانشجویان می‌توانند ثبت‌نام کنند.")
        return redirect("course_detail", slug=slug)
    if StudentCourseTeacher.objects.filter(student=student, course=course, is_active=True).exists():
        return redirect("learn_course", slug=slug)
    if course.seats_left <= 0:
        messages.error(request, "ظرفیت دوره تکمیل شده است.")
        return redirect("course_detail", slug=slug)
    teacher = course.teachers.first()
    StudentCourseTeacher.objects.create(
        student=student, course=course, teacher=teacher,
        tuition_paid=0, status=StudentCourseTeacher.Status.PENDING,
    )
    messages.success(request, "ثبت‌نام انجام شد و در انتظار تأیید کارشناس آموزش است.")
    return redirect("learn_course", slug=slug)


@login_required
def teacher_list(request):
    teachers = Teacher.objects.select_related("person").prefetch_related(
        "certifications__certification"
    ).annotate(course_count=Count("classrooms__course", distinct=True))
    return render(request, "courses/teachers.html", {"teachers": teachers})


@login_required
def teacher_detail(request, pk):
    teacher = get_object_or_404(
        Teacher.objects.select_related("person").prefetch_related(
            "certifications__certification", "classrooms__course"
        ),
        pk=pk,
    )
    return render(request, "courses/teacher_detail.html", {"teacher": teacher})


# ---------------------------------------------------------------- یادگیری
@login_required
def my_courses(request):
    student = getattr(getattr(request.user, "person", None), "student_profile", None)
    if not student:
        return redirect("dashboard")
    enrollments = (
        StudentCourseTeacher.objects.filter(student=student, is_active=True)
        .select_related("course", "teacher__person")
        .order_by("-enrolled_at")
    )
    return render(request, "learning/my_courses.html", {"enrollments": enrollments})


@login_required
def learn_course(request, slug):
    en = _enrollment_for(request.user, slug)
    if not en:
        messages.error(request, "شما در این دوره ثبت‌نام نکرده‌اید.")
        return redirect("course_detail", slug=slug)
    lessons = list(en.course.lessons.all())
    done = set(en.lesson_progress.filter(is_completed=True).values_list("lesson_id", flat=True))
    first_lesson = next((l for l in lessons if not l.is_section), None)
    sessions = []
    attendance = {"present": 0, "absent": 0, "late": 0, "excused": 0, "total": 0}
    classroom = en.course.classrooms.filter(is_active=True).first()
    if classroom:
        sessions = list(classroom.sessions.all())
        records = Attendance.objects.filter(enrollment=en)
        attendance["total"] = records.count()
        for r in records:
            attendance[r.status] = attendance.get(r.status, 0) + 1
    return render(
        request,
        "learning/course.html",
        {
            "enrollment": en,
            "course": en.course,
            "lessons": lessons,
            "done_ids": done,
            "first_lesson": first_lesson,
            "sessions": sessions,
            "attendance": attendance,
        },
    )


@login_required
def lesson_view(request, slug, lesson_id):
    en = _enrollment_for(request.user, slug)
    if not en:
        raise Http404
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=en.course)
    lessons = [l for l in en.course.lessons.all() if not l.is_section]
    idx = next((i for i, l in enumerate(lessons) if l.id == lesson.id), 0)
    progress, _ = LessonProgress.objects.get_or_create(enrollment=en, lesson=lesson)
    done = set(en.lesson_progress.filter(is_completed=True).values_list("lesson_id", flat=True))
    return render(
        request,
        "learning/lesson.html",
        {
            "enrollment": en,
            "course": en.course,
            "lessons": lessons,
            "lesson": lesson,
            "progress": progress,
            "done_ids": done,
            "prev_lesson": lessons[idx - 1] if idx > 0 else None,
            "next_lesson": lessons[idx + 1] if idx + 1 < len(lessons) else None,
        },
    )


@login_required
def complete_lesson(request, slug, lesson_id):
    en = _enrollment_for(request.user, slug)
    if not en:
        raise Http404
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=en.course)
    progress, _ = LessonProgress.objects.get_or_create(enrollment=en, lesson=lesson)
    if not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save(update_fields=["is_completed", "completed_at", "updated_at"])
        StudySession.objects.create(
            enrollment=en, minutes=max(lesson.duration_minutes, 5), date=timezone.localdate()
        )
        en.recalculate_progress()
        messages.success(request, "جلسه تکمیل شد.")
    return redirect("lesson_view", slug=slug, lesson_id=lesson_id)


# ---------------------------------------------------------------- تکلیف
@login_required
def assignment_list(request):
    student = getattr(getattr(request.user, "person", None), "student_profile", None)
    if not student:
        return redirect("dashboard")
    enrollments = StudentCourseTeacher.objects.filter(student=student, is_active=True)
    assignments = (
        Assignment.objects.filter(course__in=[e.course for e in enrollments], is_active=True)
        .select_related("course")
    )
    rows = []
    for a in assignments:
        en = next((e for e in enrollments if e.course_id == a.course_id), None)
        sub = AssignmentSubmission.objects.filter(assignment=a, enrollment=en).first() if en else None
        rows.append({"assignment": a, "submission": sub, "enrollment": en})
    rows.sort(key=lambda r: (r["submission"] is not None, r["assignment"].due_date))
    return render(request, "assignments/list.html", {"rows": rows})


@login_required
def assignment_detail(request, pk):
    assignment = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    en = _enrollment_for(request.user, assignment.course.slug) if request.user.is_student else None
    submission = (
        AssignmentSubmission.objects.filter(assignment=assignment, enrollment=en).first()
        if en
        else None
    )
    form = SubmissionForm()
    if request.method == "POST" and en:
        if submission and not assignment.allow_resubmit:
            messages.error(request, "این تکلیف قبلاً ارسال شده است.")
        else:
            form = SubmissionForm(request.POST, request.FILES)
            if form.is_valid():
                obj = submission or AssignmentSubmission(assignment=assignment, enrollment=en)
                obj.note = form.cleaned_data.get("note") or ""
                if form.cleaned_data.get("file"):
                    obj.file = form.cleaned_data["file"]
                obj.status = (
                    AssignmentSubmission.Status.LATE
                    if timezone.now() > assignment.due_date
                    else AssignmentSubmission.Status.SUBMITTED
                )
                obj.save()
                en.recalculate_progress()
                messages.success(request, "تکلیف ارسال شد.")
                return redirect("assignment_detail", pk=pk)
    return render(
        request,
        "assignments/detail.html",
        {
            "assignment": assignment,
            "enrollment": en,
            "submission": submission,
            "form": form,
            "is_late": timezone.now() > assignment.due_date,
        },
    )


@login_required
def grading_queue(request):
    if not (request.user.is_teacher or request.user.can_manage):
        return redirect("dashboard")
    qs = AssignmentSubmission.objects.select_related(
        "assignment__course", "enrollment__student__person"
    )
    if request.user.is_teacher:
        qs = qs.filter(assignment__teacher__person=request.user.person)
    pending = qs.filter(status__in=["submitted", "late"])
    graded = qs.filter(status="graded")[:10]
    return render(request, "assignments/grading.html", {"pending": pending, "graded": graded})


@login_required
def grade_submission(request, pk):
    sub = get_object_or_404(
        AssignmentSubmission.objects.select_related("assignment", "enrollment__student__person"),
        pk=pk,
    )
    if not (request.user.is_teacher or request.user.can_manage):
        return redirect("dashboard")
    if request.method == "POST":
        try:
            score = float(request.POST.get("score", ""))
        except ValueError:
            messages.error(request, "نمره معتبر وارد کنید.")
        else:
            sub.score = min(score, sub.assignment.max_score)
            sub.feedback = request.POST.get("feedback", "")
            sub.status = AssignmentSubmission.Status.GRADED
            sub.graded_at = timezone.now()
            sub.graded_by = request.user
            sub.save()
            sub.enrollment.recalculate_progress()
            Notification.objects.create(
                user=sub.enrollment.student.account,
                kind=Notification.Kind.GRADE,
                title=f"نمره تکلیف «{sub.assignment.title}» ثبت شد",
                body=f"نمره: {sub.score} از {sub.assignment.max_score}",
                url="/assignments/",
            )
            messages.success(request, "نمره ثبت شد.")
            return redirect("grading")
    return render(request, "assignments/grade.html", {"submission": sub})


# ---------------------------------------------------------------- آزمون
@login_required
def exam_list(request):
    student = getattr(getattr(request.user, "person", None), "student_profile", None)
    if not student:
        return redirect("dashboard")
    enrollments = StudentCourseTeacher.objects.filter(student=student, is_active=True)
    exams = Exam.objects.filter(
        course__in=[e.course for e in enrollments], is_active=True
    ).select_related("course")
    rows = []
    for exam in exams:
        en = next((e for e in enrollments if e.course_id == exam.course_id), None)
        attempt = (
            ExamAttempt.objects.filter(
                exam=exam, enrollment=en, is_submitted=True
            ).order_by("-started_at").first()
            if en
            else None
        )
        rows.append({"exam": exam, "attempt": attempt, "enrollment": en})
    return render(request, "exams/list.html", {"rows": rows})


@login_required
def exam_start(request, pk):
    exam = get_object_or_404(Exam.objects.prefetch_related("questions"), pk=pk)
    en = _enrollment_for(request.user, exam.course.slug)
    if not en:
        messages.error(request, "شما در این دوره ثبت‌نام نکرده‌اید.")
        return redirect("exams")
    attempt, _ = ExamAttempt.objects.get_or_create(
        exam=exam, enrollment=en, is_submitted=False
    )
    questions = list(exam.questions.all())
    if exam.shuffle_questions:
        import random

        random.shuffle(questions)

    if request.method == "POST":
        total = 0.0
        needs_manual = False
        for q in questions:
            ans, _ = ExamAnswer.objects.get_or_create(attempt=attempt, question=q)
            if q.kind == Question.Kind.MCQ:
                ans.selected_option = request.POST.get(f"q{q.id}", "")
                ans.is_correct = ans.selected_option == q.correct_option
            elif q.kind == Question.Kind.TRUE_FALSE:
                val = request.POST.get(f"q{q.id}")
                ans.selected_bool = None if val is None else val == "true"
                ans.is_correct = ans.selected_bool == q.correct_bool
            elif q.kind == Question.Kind.BLANK:
                ans.text_answer = request.POST.get(f"q{q.id}", "").strip()
                ans.is_correct = ans.text_answer.lower() == q.correct_text.lower()
            else:
                ans.text_answer = request.POST.get(f"q{q.id}", "")
                needs_manual = True
            ans.awarded_score = q.score if ans.is_correct else 0
            ans.save()
            total += float(ans.awarded_score or 0)
        attempt.score = total
        attempt.is_submitted = True
        attempt.submitted_at = timezone.now()
        attempt.needs_manual_grading = needs_manual
        attempt.save()
        en.recalculate_progress()
        messages.success(request, "آزمون ثبت شد.")
        return redirect("exam_result", pk=attempt.pk)

    return render(
        request,
        "exams/take.html",
        {"exam": exam, "attempt": attempt, "questions": questions},
    )


@login_required
def exam_result(request, pk):
    attempt = get_object_or_404(
        ExamAttempt.objects.select_related("exam__course").prefetch_related(
            "answers__question"
        ),
        pk=pk,
    )
    if attempt.enrollment.student.account != request.user and not request.user.is_teacher:
        raise Http404
    return render(request, "exams/result.html", {"attempt": attempt})


# ---------------------------------------------------------------- حضور
@login_required
def attendance_report(request):
    if request.user.is_student:
        student = request.user.person.student_profile
        records = Attendance.objects.filter(enrollment__student=student).select_related(
            "session__classroom__course"
        )
        scope = "شما"
    elif request.user.is_teacher:
        records = Attendance.objects.filter(
            enrollment__teacher__person=request.user.person
        ).select_related("session__classroom__course", "enrollment__student__person")
        scope = "دانشجویان شما"
    else:
        records = Attendance.objects.all().select_related(
            "session__classroom__course", "enrollment__student__person"
        )
        scope = "کل آموزشگاه"
    summary = {"present": 0, "absent": 0, "late": 0, "excused": 0}
    for r in records:
        summary[r.status] = summary.get(r.status, 0) + 1
    total = sum(summary.values()) or 1
    rate = round((summary["present"] + summary["late"]) / total * 100)
    return render(
        request,
        "attendance/report.html",
        {"records": records[:200], "summary": summary, "rate": rate, "total": total, "scope": scope},
    )


@login_required
def attendance_board(request, classroom_id):
    classroom = get_object_or_404(
        Classroom.objects.select_related("course", "teacher__person"), pk=classroom_id
    )
    if not (request.user.can_manage or request.user.is_teacher):
        return redirect("dashboard")
    sessions = classroom.sessions.all()
    enrollments = classroom.course.enrollments.filter(is_active=True).select_related(
        "student__person"
    )
    session_id = request.GET.get("session") or (sessions.first().id if sessions else None)
    current = sessions.filter(pk=session_id).first() if session_id else None
    if request.method == "POST" and current:
        for en in enrollments:
            status = request.POST.get(f"e{en.id}")
            if status:
                Attendance.objects.update_or_create(
                    session=current, enrollment=en, defaults={"status": status}
                )
        current.is_held = True
        current.save(update_fields=["is_held", "updated_at"])
        messages.success(request, "حضور و غیاب ثبت شد.")
        return redirect(f"{request.path}?session={current.id}")
    existing = (
        {a.enrollment_id: a.status for a in Attendance.objects.filter(session=current)}
        if current
        else {}
    )
    return render(
        request,
        "attendance/board.html",
        {
            "classroom": classroom,
            "sessions": sessions,
            "current": current,
            "enrollments": enrollments,
            "existing": existing,
            "statuses": Attendance.Status.choices,
        },
    )


# ---------------------------------------------------------------- گواهی
@login_required
def certificate_list(request):
    student = getattr(getattr(request.user, "person", None), "student_profile", None)
    certs = Certificate.objects.filter(
        enrollment__student=student
    ).select_related("enrollment__course") if student else Certificate.objects.none()
    return render(request, "certificates/list.html", {"certificates": certs})


@login_required
def certificate_issue(request, enrollment_id):
    en = get_object_or_404(StudentCourseTeacher.objects.select_related("course"), pk=enrollment_id)
    if not (request.user.can_manage or en.student.account == request.user):
        raise Http404
    if hasattr(en, "certificate"):
        return redirect("certificate_detail", serial=en.certificate.serial)
    if en.progress < 100:
        messages.error(request, "پیشرفت دوره باید ۱۰۰٪ باشد.")
        return redirect("learn_course", slug=en.course.slug)
    cert = Certificate.objects.create(
        enrollment=en,
        serial=build_serial(),
        title=f"گواهی پایان دوره {en.course.name}",
        hours=en.course.duration,
        grade=en.score,
    )
    Notification.objects.create(
        user=en.student.account,
        kind=Notification.Kind.CERTIFICATE,
        title="گواهی پایان دوره صادر شد",
        body=cert.title,
        url=f"/verify/{cert.serial}/",
    )
    messages.success(request, "گواهی صادر شد.")
    return redirect("certificate_detail", serial=cert.serial)


def certificate_detail(request, serial):
    cert = get_object_or_404(
        Certificate.objects.select_related(
            "enrollment__course", "enrollment__student__person"
        ),
        serial=serial,
    )
    return render(request, "certificates/detail.html", {"cert": cert})


def certificate_verify(request, serial=None):
    cert, error, code = None, None, (request.GET.get("serial") or "").strip()
    if serial:
        cert = Certificate.objects.select_related(
            "enrollment__student__person", "enrollment__course"
        ).filter(serial__iexact=serial).first()
        if not cert:
            error = "گواهی با این شماره یافت نشد."
    elif code:
        cert = Certificate.objects.select_related(
            "enrollment__student__person", "enrollment__course"
        ).filter(serial__iexact=code).first()
        if not cert:
            error = "گواهی با این شماره یافت نشد."
    return render(
        request, "certificates/verify.html", {"cert": cert, "error": error, "code": code}
    )


# ---------------------------------------------------------------- اعلان
@login_required
def notifications_list(request):
    items = Notification.objects.filter(user=request.user)
    kind = request.GET.get("kind")
    if kind:
        items = items.filter(kind=kind)
    return render(
        request, "notifications/list.html", {"items": items, "active_kind": kind}
    )


@login_required
def notification_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return redirect(request.META.get("HTTP_REFERER") or "notifications")


@login_required
def notifications_read_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications")


# ---------------------------------------------------------------- مدیریت
@login_required
def manage_courses(request):
    if not request.user.can_manage:
        return redirect("dashboard")
    courses = Course.objects.select_related("category").annotate(
        students=Count("enrollments", filter=Q(enrollments__is_active=True))
    )
    return render(request, "manage/courses.html", {"courses": courses})


@login_required
def course_create(request):
    if not request.user.can_manage:
        return redirect("dashboard")
    form = CourseForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        course = form.save(commit=False)
        course.published_at = timezone.now()
        course.save()
        form.save_m2m()
        messages.success(request, "دوره ایجاد شد.")
        return redirect("manage_courses")
    return render(request, "manage/course_form.html", {"form": form, "title": "دوره جدید"})


@login_required
def course_edit(request, pk):
    if not request.user.can_manage:
        return redirect("dashboard")
    course = get_object_or_404(Course, pk=pk)
    form = CourseForm(request.POST or None, request.FILES or None, instance=course)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "دوره ویرایش شد.")
        return redirect("manage_courses")
    return render(
        request, "manage/course_form.html", {"form": form, "title": course.name}
    )


@login_required
def manage_users(request):
    if not request.user.is_manager:
        return redirect("dashboard")
    q = (request.GET.get("q") or "").strip()
    role = request.GET.get("role")
    users = Users.objects.select_related("person")
    if q:
        users = users.filter(
            Q(username__icontains=q)
            | Q(person__persian_first_name__icontains=q)
            | Q(person__persian_last_name__icontains=q)
        )
    if role:
        users = users.filter(role=role)
    return render(
        request,
        "manage/users.html",
        {"users": users, "q": q, "role": role, "roles": Users.Role.choices},
    )


@login_required
def enrollments_admin(request):
    if not request.user.can_manage:
        return redirect("dashboard")
    qs = (
        StudentCourseTeacher.objects.select_related(
            "student__person", "course", "teacher__person"
        )
        .order_by("-enrolled_at")
    )
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status).order_by("-enrolled_at")
    if request.method == "POST":
        en = get_object_or_404(StudentCourseTeacher, pk=request.POST.get("enrollment"))
        new_status = request.POST.get("new_status")
        if new_status in dict(StudentCourseTeacher.Status.choices):
            en.status = new_status
            en.save(update_fields=["status", "updated_at"])
            messages.success(request, "وضعیت ثبت‌نام به‌روزرسانی شد.")
        return redirect("enrollments_admin")
    return render(
        request,
        "manage/enrollments.html",
        {"enrollments": qs, "status": status, "statuses": StudentCourseTeacher.Status.choices},
    )


@login_required
def reports(request):
    if not request.user.can_manage:
        return redirect("dashboard")
    rows = StudentCourseTeacher.objects.select_related(
        "student__person", "course"
    ).order_by("-enrolled_at")
    course_id = request.GET.get("course")
    if course_id:
        rows = rows.filter(course_id=course_id)
    summary = {
        "count": rows.count(),
        "revenue": rows.aggregate(s=Sum("tuition_paid"))["s"] or 0,
        "completed": rows.filter(status="completed").count(),
        "avg_progress": round(rows.aggregate(a=Avg("progress"))["a"] or 0),
    }
    return render(
        request,
        "manage/reports.html",
        {
            "rows": rows[:100],
            "courses": Course.objects.all(),
            "course_id": course_id,
            "summary": summary,
        },
    )


def error_403(request, exception=None):
    return render(request, "errors/error.html", {"code": "۴۰۳", "title": "دسترسی مجاز نیست",
                                                 "message": "شما به این بخش دسترسی ندارید."}, status=403)


def error_404(request, exception=None):
    return render(request, "errors/error.html", {"code": "۴۰۴", "title": "صفحه پیدا نشد",
                                                 "message": "نشانی واردشده در سامانه وجود ندارد."}, status=404)


def error_500(request):
    return render(request, "errors/error.html", {"code": "۵۰۰", "title": "خطای سرور",
                                                 "message": "مشکلی پیش آمد. دوباره تلاش کنید."}, status=500)
