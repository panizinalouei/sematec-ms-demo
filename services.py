
import secrets
from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from .models import (Assignment, AssignmentSubmission, Attendance, Certificate,
                     ClassSession, Classroom, Course, Exam, ExamAttempt,
                     Lesson, LessonProgress, Notification, Student,
                     StudentCourseTeacher, StudySession, Teacher, Users)


def build_serial() -> str:
    return f"SMTC-{timezone.now().year}-{secrets.token_hex(3).upper()}"


def progress_of(enrollment: StudentCourseTeacher) -> int:
    return enrollment.recalculate_progress()


def score_attempt(attempt: ExamAttempt) -> float:
    return float(attempt.score or 0)


class DashboardService:

    def __init__(self, user: Users):
        self.user = user

    def build(self) -> dict:
        role = self.user.role
        base = {"unread": Notification.objects.filter(user=self.user, is_read=False).count()}
        if role == Users.Role.STUDENT:
            base.update(self._student())
        elif role == Users.Role.TEACHER:
            base.update(self._teacher())
        elif role == Users.Role.STAFF:
            base.update(self._staff())
        elif role == Users.Role.SUPERVISOR:
            base.update(self._supervisor())
        else:
            base.update(self._admin())
        return base


    def _student(self):
        student = getattr(self.user.person, "student_profile", None)
        if not student:
            return {}
        enrollments = StudentCourseTeacher.objects.filter(
            student=student, is_active=True
        ).select_related("course", "teacher__person")
        active = enrollments.exclude(status=StudentCourseTeacher.Status.COMPLETED)
        submitted = AssignmentSubmission.objects.filter(
            enrollment__in=enrollments
        ).values_list("assignment_id", flat=True)
        pending_assignments = (
            Assignment.objects.filter(
                course__in=enrollments.values_list("course_id", flat=True),
                is_active=True,
            )
            .exclude(id__in=submitted)
            .order_by("due_date")[:5]
        )
        exams = (
            Exam.objects.filter(
                course__in=enrollments.values_list("course_id", flat=True),
                is_active=True,
            )
            .exclude(attempts__enrollment__in=enrollments, attempts__is_submitted=True)[:4]
        )
        next_session = (
            ClassSession.objects.filter(
                classroom__course__in=enrollments.values_list("course_id", flat=True),
                date__gte=timezone.localdate(),
            )
            .select_related("classroom__course")
            .order_by("date", "start_time")
            .first()
        )
        minutes = (
            StudySession.objects.filter(enrollment__in=enrollments).aggregate(s=Sum("minutes"))["s"]
            or 0
        )
        attendance = Attendance.objects.filter(enrollment__in=enrollments)
        att_total = attendance.count()
        att_present = attendance.filter(status__in=["present", "late"]).count()
        return {
            "enrollments": enrollments,
            "active_count": active.count(),
            "completed_count": enrollments.filter(status="completed").count(),
            "avg_progress": round(enrollments.aggregate(a=Avg("progress"))["a"] or 0),
            "pending_assignments": pending_assignments,
            "exams": exams,
            "next_session": next_session,
            "study_hours": round(minutes / 60, 1),
            "certificates": Certificate.objects.filter(enrollment__in=enrollments).count(),
            "attendance_rate": round(att_present / att_total * 100) if att_total else 0,
            "continue_enrollment": enrollments.order_by("progress").first(),
            "progress_items": [
                {"title": e.course.name, "progress": e.progress} for e in enrollments
            ],
        }


    def _teacher(self):
        teacher = getattr(self.user.person, "teacher_profile", None)
        if not teacher:
            return {}
        classrooms = Classroom.objects.filter(teacher=teacher, is_active=True)
        courses = Course.objects.filter(classrooms__in=classrooms).distinct()
        enrollments = StudentCourseTeacher.objects.filter(
            course__in=courses, is_active=True
        )
        pending = AssignmentSubmission.objects.filter(
            assignment__course__in=courses, status__in=["submitted", "late"]
        ).count()
        today = timezone.localdate()
        today_sessions = ClassSession.objects.filter(
            classroom__in=classrooms, date=today
        ).select_related("classroom__course")
        attendance = Attendance.objects.filter(enrollment__in=enrollments)
        total_att = attendance.count()
        present = attendance.filter(status__in=["present", "late"]).count()
        recent = AssignmentSubmission.objects.filter(
            assignment__course__in=courses
        ).select_related("assignment", "enrollment__student__person")[:5]
        return {
            "student_count": enrollments.values("student").distinct().count(),
            "course_count": courses.count(),
            "classroom_count": classrooms.count(),
            "pending_grading": pending,
            "today_sessions": today_sessions,
            "attendance_rate": round(present / total_att * 100) if total_att else 0,
            "recent_submissions": recent,
            "course_rows": courses.annotate(
                students=Count("enrollments", filter=Q(enrollments__is_active=True), distinct=True),
                avg=Avg("enrollments__progress"),
            ),
            "teacher": teacher,
        }


    def _staff(self):
        today = timezone.localdate()
        enrollments = StudentCourseTeacher.objects.filter(is_active=True)
        return {
            "new_today": enrollments.filter(enrolled_at__date=today).count(),
            "pending": enrollments.filter(status="pending").count(),
            "total_enrollments": enrollments.count(),
            "recent": enrollments.select_related("student__person", "course")[:8],
            "cohorts": Classroom.objects.filter(is_active=True)
            .select_related("course", "teacher__person")
            .annotate(seats=Count("course__enrollments", filter=Q(course__enrollments__is_active=True)))[:6],
            "sessions_today": ClassSession.objects.filter(date=today).select_related(
                "classroom__course"
            ),
        }


    def _supervisor(self):
        teachers = (
            Teacher.objects.select_related("person")
            .annotate(
                classroom_count=Count("classrooms", distinct=True),
                student_count=Count("classrooms__course__enrollments", distinct=True),
            )
            .order_by("-classroom_count")[:6]
        )
        attendance = Attendance.objects.all()
        total = attendance.count()
        present = attendance.filter(status__in=["present", "late"]).count()
        courses = Course.objects.annotate(
            enrollment_count=Count("enrollments", filter=Q(enrollments__is_active=True)),
            avg_progress=Avg("enrollments__progress"),
        ).order_by("-enrollment_count")[:6]
        return {
            "teachers": teachers,
            "attendance_rate": round(present / total * 100) if total else 0,
            "quality_courses": courses,
            "completion_rate": round(
                StudentCourseTeacher.objects.filter(status="completed").count()
                / max(StudentCourseTeacher.objects.count(), 1)
                * 100
            ),
        }


    def _admin(self):
        today = timezone.localdate()
        enrollments = StudentCourseTeacher.objects.all()
        revenue = enrollments.aggregate(s=Sum("tuition_paid"))["s"] or 0
        teachers = Teacher.objects.select_related("person").annotate(
            classroom_count=Count("classrooms", distinct=True),
            student_count=Count("classrooms__course__enrollments", distinct=True),
        )[:5]
        top_courses = (
            Course.objects.annotate(
                enrollment_count=Count("enrollments", filter=Q(enrollments__is_active=True))
            ).order_by("-enrollment_count")[:5]
        )
        by_category = Course.objects.values("category__name").annotate(
            c=Count("id")
        ).order_by("-c")[:6]
        recent = enrollments.select_related("student__person", "course")[:6]
        return {
            "total_students": Student.objects.count(),
            "total_teachers": Teacher.objects.count(),
            "total_courses": Course.objects.filter(status="published").count(),
            "active_classrooms": Classroom.objects.filter(is_active=True).count(),
            "total_enrollments": enrollments.filter(is_active=True).count(),
            "revenue": revenue,
            "series": self._series(8),
            "top_courses": top_courses,
            "by_category": by_category,
            "recent": recent,
            "teachers": teachers,
        }

    def _series(self, months: int):
        from .utils.jalali import jalali_month

        today = timezone.localdate()
        out = []
        for i in range(months - 1, -1, -1):
            year, month = today.year, today.month - i
            while month <= 0:
                month += 12
                year -= 1
            start = today.replace(year=year, month=month, day=1)
            nxt = (start + timedelta(days=32)).replace(day=1)
            count = StudentCourseTeacher.objects.filter(
                enrolled_at__gte=start, enrolled_at__lt=nxt
            ).count()
            out.append({"label": jalali_month(start), "count": count})
        return out
