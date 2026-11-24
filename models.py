
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone



class TimeStamped(models.Model):
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین ویرایش", auto_now=True)

    class Meta:
        abstract = True


class Department(TimeStamped):
    name = models.CharField("نام دپارتمان", max_length=100, unique=True)
    class Meta:
        verbose_name = "دپارتمان"
        verbose_name_plural = "دپارتمان‌ها"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Job(TimeStamped):


    title = models.CharField("عنوان شغلی", max_length=100, unique=True)

    class Meta:
        verbose_name = "عنوان شغلی"
        verbose_name_plural = "عناوین شغلی"
        ordering = ["title"]

    def __str__(self):
        return self.title


class Education(TimeStamped):


    name = models.CharField("مدرک", max_length=100, unique=True)

    class Meta:
        verbose_name = "مدرک تحصیلی"
        verbose_name_plural = "مدارک تحصیلی"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Person(TimeStamped):


    class Sex(models.TextChoices):
        MALE = "M", "مرد"
        FEMALE = "F", "زن"

    persian_first_name = models.CharField("نام (فارسی)", max_length=60)
    english_first_name = models.CharField("نام (انگلیسی)", max_length=60, blank=True)
    persian_last_name = models.CharField("نام خانوادگی (فارسی)", max_length=60)
    english_last_name = models.CharField("نام خانوادگی (انگلیسی)", max_length=60, blank=True)
    national_code = models.CharField(
        "کد ملی", max_length=10, unique=True, null=True, blank=True,
        validators=[RegexValidator(r"^\d{10}$", "کد ملی باید ۱۰ رقم باشد.")],
    )
    sex = models.CharField("جنسیت", max_length=1, choices=Sex.choices, default=Sex.MALE)
    birth_date = models.DateField("تاریخ تولد", null=True, blank=True)
    home_address = models.CharField("آدرس", max_length=300, blank=True)
    phone_number = models.CharField("موبایل", max_length=15, blank=True, db_index=True)
    email_address = models.EmailField("ایمیل", blank=True)
    education = models.ForeignKey(
        Education, verbose_name="مدرک تحصیلی", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="people",
    )
    photo = models.ImageField("عکس", upload_to="people/", null=True, blank=True)

    class Meta:
        verbose_name = "شخص"
        verbose_name_plural = "اشخاص"
        ordering = ["persian_last_name", "persian_first_name"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self) -> str:
        return f"{self.persian_first_name} {self.persian_last_name}".strip()

    @property
    def initials(self) -> str:
        return (self.persian_first_name[:1] + self.persian_last_name[:1]) or "؟"


class Users(AbstractBaseUser, PermissionsMixin, TimeStamped):


    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Role(models.TextChoices):
        ADMIN = "admin", "مدیر سامانه"
        SUPERVISOR = "supervisor", "ناظر آموزشی"
        TEACHER = "teacher", "استاد"
        STUDENT = "student", "دانشجو"
        STAFF = "staff", "کارشناس آموزش"

    username = models.CharField("نام کاربری", max_length=80, unique=True)
    password = models.CharField("رمز عبور (هش)", max_length=128)
    first_name = models.CharField("نام", max_length=60, blank=True)
    last_name = models.CharField("نام خانوادگی", max_length=60, blank=True)
    role = models.CharField("نقش", max_length=20, choices=Role.choices, default=Role.STUDENT)
    person = models.OneToOneField(
        Person, verbose_name="شخص", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="account",
    )
    is_active = models.BooleanField("فعال", default=True)
    is_admin = models.BooleanField("دسترسی ادمین جنگو", default=False)
    last_login = models.DateTimeField("آخرین ورود", null=True, blank=True)
    last_login_ip = models.GenericIPAddressField("IP آخرین ورود", null=True, blank=True)

    class Meta:
        verbose_name = "حساب کاربری"
        verbose_name_plural = "حساب‌های کاربری"
        ordering = ["username"]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def display_name(self) -> str:
        if self.person:
            return self.person.full_name
        return f"{self.first_name} {self.last_name}".strip() or self.username

    @property
    def initials(self) -> str:
        return self.person.initials if self.person else (self.display_name[:2] or "؟")

    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT

    @property
    def is_teacher(self) -> bool:
        return self.role == self.Role.TEACHER

    @property
    def is_manager(self) -> bool:
        return self.role in {self.Role.ADMIN, self.Role.SUPERVISOR}

    @property
    def can_manage(self) -> bool:
        return self.role in {self.Role.ADMIN, self.Role.SUPERVISOR, self.Role.STAFF}



class EducationCategory(TimeStamped):


    name = models.CharField("نام دسته", max_length=100)
    english_name = models.CharField("نام انگلیسی", max_length=100, blank=True)
    slug = models.SlugField("نامک", max_length=120, unique=True)
    icon = models.CharField("آیکون", max_length=30, default="code")
    color = models.CharField("رنگ", max_length=20, default="#004AAD")
    order = models.PositiveSmallIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "دسته‌بندی دوره"
        verbose_name_plural = "دسته‌بندی دوره‌ها"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Course(TimeStamped):


    class Type(models.TextChoices):
        IN_PERSON = "in_person", "حضوری"
        ONLINE = "online", "آنلاین"
        HYBRID = "hybrid", "ترکیبی"

    class Level(models.TextChoices):
        BASIC = "basic", "مقدماتی"
        INTERMEDIATE = "intermediate", "متوسط"
        ADVANCED = "advanced", "پیشرفته"
        COMPREHENSIVE = "comprehensive", "جامع"

    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        PUBLISHED = "published", "منتشرشده"
        ARCHIVED = "archived", "آرشیو"

    course_code = models.CharField("کد دوره", max_length=20, unique=True)
    name = models.CharField("نام دوره", max_length=160)
    english_name = models.CharField("نام انگلیسی", max_length=160, blank=True)
    slug = models.SlugField("نامک", max_length=180, unique=True)
    duration = models.PositiveSmallIntegerField("مدت (ساعت)", default=0)
    course_type = models.CharField(
        "نوع برگزاری", max_length=20, choices=Type.choices, default=Type.HYBRID
    )
    level = models.CharField(
        "سطح", max_length=20, choices=Level.choices, default=Level.BASIC
    )
    description = models.TextField("توضیحات", blank=True)
    syllabus = models.TextField("سرفصل", blank=True, help_text="هر سرفصل در یک خط")
    syllabus_file = models.FileField(
        "فایل سرفصل", upload_to="syllabi/", null=True, blank=True
    )
    category = models.ForeignKey(
        EducationCategory, verbose_name="دسته‌بندی", on_delete=models.PROTECT,
        related_name="courses",
    )
    teachers = models.ManyToManyField(
        "Teacher", verbose_name="اساتید", related_name="courses", blank=True
    )
    capacity = models.PositiveSmallIntegerField("ظرفیت", default=20)
    tuition = models.PositiveBigIntegerField("شهریه (تومان)", default=0)
    prerequisites = models.ManyToManyField(
        "self", verbose_name="پیش‌نیاز", symmetrical=False,
        related_name="advanced_courses", blank=True,
    )
    cover = models.ImageField("تصویر دوره", upload_to="courses/", null=True, blank=True)
    status = models.CharField(
        "وضعیت", max_length=20, choices=Status.choices, default=Status.PUBLISHED
    )
    published_at = models.DateTimeField("تاریخ انتشار", null=True, blank=True)

    class Meta:
        verbose_name = "دوره"
        verbose_name_plural = "دوره‌ها"
        ordering = ["-published_at", "name"]
        indexes = [models.Index(fields=["status", "category"])]

    def __str__(self):
        return self.name

    @property
    def syllabus_list(self) -> list[str]:
        return [line.strip() for line in self.syllabus.splitlines() if line.strip()]

    @property
    def cover_url(self) -> str:
        return self.cover.url if self.cover else "/static/img/course-placeholder.svg"

    @property
    def enrolled_count(self) -> int:
        return StudentCourseTeacher.objects.filter(is_active=True, course=self).count()

    @property
    def seats_left(self) -> int:
        return max(self.capacity - self.enrolled_count, 0)

    @property
    def level_class(self) -> str:
        return {
            self.Level.BASIC: "badge-green",
            self.Level.INTERMEDIATE: "badge-blue",
            self.Level.ADVANCED: "badge-gold",
            self.Level.COMPREHENSIVE: "badge-navy",
        }.get(self.level, "badge-blue")


class Student(TimeStamped):


    person = models.OneToOneField(
        Person, verbose_name="شخص", on_delete=models.CASCADE, related_name="student_profile"
    )
    student_code = models.CharField("شماره دانشجویی", max_length=20, unique=True)
    father_name = models.CharField("نام پدر", max_length=60, blank=True)
    work_address = models.CharField("آدرس محل کار", max_length=300, blank=True)
    work_phone = models.CharField("تلفن محل کار", max_length=20, blank=True)

    class Meta:
        verbose_name = "دانشجو"
        verbose_name_plural = "دانشجویان"
        ordering = ["student_code"]

    def __str__(self):
        return f"{self.person.full_name} ({self.student_code})"

    @property
    def account(self):
        return getattr(self.person, "account", None)

    @property
    def full_name(self):
        return self.person.full_name


class Teacher(TimeStamped):


    class Marital(models.TextChoices):
        SINGLE = "single", "مجرد"
        MARRIED = "married", "متاهل"

    person = models.OneToOneField(
        Person, verbose_name="شخص", on_delete=models.CASCADE, related_name="teacher_profile"
    )
    teacher_code = models.CharField("کد استاد", max_length=20, unique=True)
    marital_status = models.CharField(
        "وضعیت تأهل", max_length=10, choices=Marital.choices, default=Marital.SINGLE
    )
    start_date = models.DateField("تاریخ شروع همکاری", null=True, blank=True)
    insurance_number = models.CharField("شماره بیمه", max_length=30, blank=True)
    account_number = models.CharField("شماره حساب", max_length=30, blank=True)
    headline = models.CharField("عنوان تخصصی", max_length=150, blank=True)
    expertise = models.CharField("حوزه تخصص", max_length=200, blank=True)
    bio = models.TextField("درباره استاد", blank=True)
    teaching_hours = models.PositiveIntegerField("ساعت تدریس", default=0)
    years_experience = models.PositiveSmallIntegerField("سال تجربه", default=0)
    is_featured = models.BooleanField("نمایش در صفحه اصلی", default=False)

    class Meta:
        verbose_name = "استاد"
        verbose_name_plural = "اساتید"
        ordering = ["-is_featured", "person__persian_last_name"]

    def __str__(self):
        return self.person.full_name

    @property
    def full_name(self):
        return self.person.full_name


class Employee(TimeStamped):


    person = models.OneToOneField(
        Person, verbose_name="شخص", on_delete=models.CASCADE, related_name="employee_profile"
    )
    employee_code = models.CharField("کد کارمندی", max_length=20, unique=True)
    department = models.ForeignKey(
        Department, verbose_name="دپارتمان", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="employees",
    )
    job = models.ForeignKey(
        Job, verbose_name="عنوان شغلی", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="employees",
    )
    hire_date = models.DateField("تاریخ استخدام", null=True, blank=True)
    account_number = models.CharField("شماره حساب", max_length=30, blank=True)
    insurance_number = models.CharField("شماره بیمه", max_length=30, blank=True)
    manager = models.ForeignKey(
        "self", verbose_name="مدیر مستقیم", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="subordinates",
    )

    class Meta:
        verbose_name = "کارمند"
        verbose_name_plural = "کارمندان"
        ordering = ["employee_code"]

    def __str__(self):
        return f"{self.person.full_name} ({self.employee_code})"


class Certification(TimeStamped):


    title = models.CharField("عنوان مدرک", max_length=150)
    vendor = models.CharField("شرکت صادرکننده", max_length=100, blank=True)
    start_date = models.DateField("تاریخ اخذ", null=True, blank=True)

    class Meta:
        verbose_name = "مدرک بین‌المللی"
        verbose_name_plural = "مدارک بین‌المللی"
        ordering = ["vendor", "title"]

    def __str__(self):
        return f"{self.title} — {self.vendor}".strip(" —")


class TeacherCertification(TimeStamped):


    teacher = models.ForeignKey(
        Teacher, verbose_name="استاد", on_delete=models.CASCADE, related_name="certifications"
    )
    certification = models.ForeignKey(
        Certification, verbose_name="مدرک", on_delete=models.CASCADE,
        related_name="holders",
    )
    score = models.DecimalField(
        "نمره", max_digits=5, decimal_places=2, null=True, blank=True
    )
    expire_date = models.DateField("تاریخ انقضا", null=True, blank=True)

    class Meta:
        verbose_name = "مدرک استاد"
        verbose_name_plural = "مدارک اساتید"
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "certification"], name="unique_teacher_certification"
            )
        ]

    def __str__(self):
        return f"{self.teacher} — {self.certification}"


class StudentCourseTeacher(TimeStamped):


    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار تأیید"
        ACTIVE = "active", "فعال"
        COMPLETED = "completed", "تکمیل‌شده"
        CANCELLED = "cancelled", "انصراف"

    student = models.ForeignKey(
        Student, verbose_name="دانشجو", on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        Course, verbose_name="دوره", on_delete=models.CASCADE, related_name="enrollments"
    )
    teacher = models.ForeignKey(
        Teacher, verbose_name="استاد", on_delete=models.PROTECT,
        null=True, blank=True, related_name="enrollments",
    )
    term_number = models.PositiveSmallIntegerField("ترم", default=1)
    score = models.DecimalField(
        "نمره نهایی", max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    status = models.CharField(
        "وضعیت", max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    progress = models.PositiveSmallIntegerField("درصد پیشرفت", default=0)
    tuition_paid = models.PositiveBigIntegerField("شهریه پرداخت‌شده", default=0)
    is_active = models.BooleanField("فعال", default=True)
    enrolled_at = models.DateTimeField("تاریخ ثبت‌نام", auto_now_add=True)
    completed_at = models.DateTimeField("تاریخ تکمیل", null=True, blank=True)

    class Meta:
        verbose_name = "ثبت‌نام"
        verbose_name_plural = "ثبت‌نام‌ها"
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                condition=models.Q(is_active=True),
                name="unique_active_enrollment",
            )
        ]
        indexes = [models.Index(fields=["student", "status"])]

    def __str__(self):
        return f"{self.student.person.full_name} → {self.course.name}"

    @property
    def balance(self) -> int:
        return max(self.course.tuition - self.tuition_paid, 0)

    def recalculate_progress(self) -> int:

        from django.db.models import Avg

        total_lessons = self.course.lessons.filter(is_section=False).count() or 1
        done = self.lesson_progress.filter(is_completed=True).count()
        lesson_part = done / total_lessons * 60

        assignments = self.course.assignments.filter(is_active=True)
        total_a = assignments.count()
        assignment_part = 20
        if total_a:
            submitted = AssignmentSubmission.objects.filter(
                assignment__in=assignments, enrollment=self
            ).count()
            assignment_part = submitted / total_a * 20

        exams = self.course.exams.filter(is_active=True)
        total_e = exams.count()
        exam_part = 20
        if total_e:
            passed = ExamAttempt.objects.filter(
                exam__in=exams, enrollment=self, is_submitted=True
            ).count()
            exam_part = passed / total_e * 20

        self.progress = min(round(lesson_part + assignment_part + exam_part), 100)
        if self.progress >= 100 and self.status != self.Status.COMPLETED:
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()
        self.save(update_fields=["progress", "status", "completed_at", "updated_at"])
        return self.progress



class Lesson(TimeStamped):

    class Kind(models.TextChoices):
        VIDEO = "video", "ویدئو"
        PDF = "pdf", "فایل PDF"
        SLIDE = "slide", "پاورپوینت"
        ARCHIVE = "archive", "فایل فشرده"
        LINK = "link", "لینک خارجی"
        SCORM = "scorm", "بسته SCORM"
        TEXT = "text", "متن"

    course = models.ForeignKey(
        Course, verbose_name="دوره", on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField("عنوان", max_length=160)
    description = models.TextField("توضیح", blank=True)
    order = models.PositiveSmallIntegerField("ترتیب", default=0)
    is_section = models.BooleanField("سرفصل اصلی", default=False)
    kind = models.CharField("نوع محتوا", max_length=20, choices=Kind.choices, default=Kind.VIDEO)
    duration_minutes = models.PositiveSmallIntegerField("مدت (دقیقه)", default=90)
    video_url = models.URLField("لینک ویدئو", blank=True)
    file = models.FileField("فایل محتوا", upload_to="lessons/", null=True, blank=True)
    external_url = models.URLField("لینک منبع خارجی", blank=True)
    is_preview = models.BooleanField("پیش‌نمایش رایگان", default=False)

    class Meta:
        verbose_name = "جلسه"
        verbose_name_plural = "جلسات"
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "order"], name="unique_lesson_order"
            )
        ]

    def __str__(self):
        return f"{self.course.name} — {self.title}"


class LessonProgress(TimeStamped):
    enrollment = models.ForeignKey(
        StudentCourseTeacher, verbose_name="ثبت‌نام", on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey(
        Lesson, verbose_name="جلسه", on_delete=models.CASCADE, related_name="progress_records"
    )
    is_completed = models.BooleanField("تکمیل‌شده", default=False)
    watched_seconds = models.PositiveIntegerField("ثانیه تماشا", default=0)
    last_position = models.PositiveIntegerField("آخرین نقطه", default=0)
    completed_at = models.DateTimeField("زمان تکمیل", null=True, blank=True)

    class Meta:
        verbose_name = "پیشرفت جلسه"
        verbose_name_plural = "پیشرفت جلسات"
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "lesson"], name="unique_lesson_progress"
            )
        ]

    def __str__(self):
        return f"{self.enrollment} — {self.lesson.title}"


class StudySession(TimeStamped):
    enrollment = models.ForeignKey(
        StudentCourseTeacher, verbose_name="ثبت‌نام", on_delete=models.CASCADE,
        related_name="study_sessions",
    )
    minutes = models.PositiveSmallIntegerField("دقیقه مطالعه", default=0)
    date = models.DateField("تاریخ")

    class Meta:
        verbose_name = "زمان مطالعه"
        verbose_name_plural = "زمان‌های مطالعه"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.enrollment} — {self.minutes} دقیقه"



class Classroom(TimeStamped):
    """کلاس برگزارشده از یک دوره (Cohort)."""

    class Mode(models.TextChoices):
        IN_PERSON = "in_person", "حضوری"
        ONLINE = "online", "آنلاین"
        HYBRID = "hybrid", "ترکیبی"

    course = models.ForeignKey(
        Course, verbose_name="دوره", on_delete=models.CASCADE, related_name="classrooms"
    )
    teacher = models.ForeignKey(
        Teacher, verbose_name="استاد", on_delete=models.PROTECT,
        null=True, blank=True, related_name="classrooms",
    )
    name = models.CharField("نام کلاس", max_length=100)
    mode = models.CharField("نوع", max_length=20, choices=Mode.choices, default=Mode.HYBRID)
    start_date = models.DateField("تاریخ شروع")
    end_date = models.DateField("تاریخ پایان", null=True, blank=True)
    capacity = models.PositiveSmallIntegerField("ظرفیت", default=20)
    meeting_days = models.CharField("روزهای برگزاری", max_length=60, default="دوشنبه")
    meeting_time = models.CharField("ساعت", max_length=30, default="۱۶:۳۰ - ۲۰:۳۰")
    online_link = models.URLField("لینک کلاس آنلاین", blank=True)
    location = models.CharField("مکان", max_length=120, blank=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "کلاس"
        verbose_name_plural = "کلاس‌ها"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.course.name} — {self.name}"


class ClassSession(TimeStamped):


    classroom = models.ForeignKey(
        Classroom, verbose_name="کلاس", on_delete=models.CASCADE, related_name="sessions"
    )
    number = models.PositiveSmallIntegerField("شماره جلسه", default=1)
    title = models.CharField("موضوع", max_length=160, blank=True)
    date = models.DateField("تاریخ")
    start_time = models.TimeField("ساعت شروع")
    end_time = models.TimeField("ساعت پایان")
    is_held = models.BooleanField("برگزار شد", default=False)
    note = models.TextField("یادداشت", blank=True)

    class Meta:
        verbose_name = "جلسه کلاس"
        verbose_name_plural = "جلسات کلاس"
        ordering = ["date", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["classroom", "number"], name="unique_session_number"
            )
        ]

    def __str__(self):
        return f"{self.classroom} — جلسه {self.number}"


class Attendance(TimeStamped):
    class Status(models.TextChoices):
        PRESENT = "present", "حاضر"
        ABSENT = "absent", "غایب"
        LATE = "late", "تأخیر"
        EXCUSED = "excused", "موجه"

    session = models.ForeignKey(
        ClassSession, verbose_name="جلسه", on_delete=models.CASCADE,
        related_name="attendances",
    )
    enrollment = models.ForeignKey(
        StudentCourseTeacher, verbose_name="ثبت‌نام", on_delete=models.CASCADE,
        related_name="attendances",
    )
    status = models.CharField(
        "وضعیت", max_length=10, choices=Status.choices, default=Status.PRESENT
    )
    minutes_late = models.PositiveSmallIntegerField("دقیقه تأخیر", default=0)
    note = models.CharField("یادداشت", max_length=200, blank=True)

    class Meta:
        verbose_name = "حضور و غیاب"
        verbose_name_plural = "حضور و غیاب"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "enrollment"], name="unique_attendance"
            )
        ]

    def __str__(self):
        return f"{self.enrollment.student.person.full_name} — {self.get_status_display()}"



class Assignment(TimeStamped):
    course = models.ForeignKey(
        Course, verbose_name="دوره", on_delete=models.CASCADE, related_name="assignments"
    )
    teacher = models.ForeignKey(
        Teacher, verbose_name="استاد", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assignments",
    )
    title = models.CharField("عنوان", max_length=160)
    description = models.TextField("توضیحات")
    attachment = models.FileField(
        "فایل پیوست", upload_to="assignments/", null=True, blank=True
    )
    due_date = models.DateTimeField("مهلت ارسال")
    max_score = models.PositiveSmallIntegerField("نمره کل", default=100)
    allow_resubmit = models.BooleanField("امکان ارسال مجدد", default=False)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "تکلیف"
        verbose_name_plural = "تکالیف"
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.title} — {self.course.name}"


class AssignmentSubmission(TimeStamped):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "ارسال‌شده"
        GRADED = "graded", "تصحیح‌شده"
        LATE = "late", "ارسال دیرهنگام"

    assignment = models.ForeignKey(
        Assignment, verbose_name="تکلیف", on_delete=models.CASCADE,
        related_name="submissions",
    )
    enrollment = models.ForeignKey(
        StudentCourseTeacher, verbose_name="ثبت‌نام", on_delete=models.CASCADE,
        related_name="submissions",
    )
    file = models.FileField("فایل ارسالی", upload_to="submissions/", null=True, blank=True)
    note = models.TextField("توضیح دانشجو", blank=True)
    status = models.CharField(
        "وضعیت", max_length=20, choices=Status.choices, default=Status.SUBMITTED
    )
    score = models.DecimalField(
        "نمره", max_digits=5, decimal_places=1, null=True, blank=True
    )
    feedback = models.TextField("بازخورد استاد", blank=True)
    graded_at = models.DateTimeField("زمان تصحیح", null=True, blank=True)
    graded_by = models.ForeignKey(
        Users, verbose_name="تصحیح‌کننده", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="graded_submissions",
    )

    class Meta:
        verbose_name = "تحویل تکلیف"
        verbose_name_plural = "تحویل تکالیف"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "enrollment"], name="unique_submission"
            )
        ]

    def __str__(self):
        return f"{self.enrollment.student.person.full_name} — {self.assignment.title}"


class Question(TimeStamped):
    class Kind(models.TextChoices):
        MCQ = "mcq", "چهارگزینه‌ای"
        TRUE_FALSE = "true_false", "صحیح / غلط"
        DESCRIPTIVE = "descriptive", "تشریحی"
        BLANK = "blank", "جای خالی"

    course = models.ForeignKey(
        Course, verbose_name="دوره", on_delete=models.CASCADE, related_name="questions"
    )
    text = models.TextField("متن سوال")
    kind = models.CharField("نوع", max_length=20, choices=Kind.choices, default=Kind.MCQ)
    option_a = models.CharField("گزینه ۱", max_length=300, blank=True)
    option_b = models.CharField("گزینه ۲", max_length=300, blank=True)
    option_c = models.CharField("گزینه ۳", max_length=300, blank=True)
    option_d = models.CharField("گزینه ۴", max_length=300, blank=True)
    correct_option = models.CharField(
        "پاسخ صحیح", max_length=1, blank=True, help_text="a / b / c / d"
    )
    correct_bool = models.BooleanField("پاسخ صحیح (صحیح/غلط)", default=True)
    correct_text = models.CharField("پاسخ صحیح (جای خالی)", max_length=200, blank=True)
    score = models.DecimalField("بارم", max_digits=5, decimal_places=1, default=1)
    difficulty = models.CharField(
        "سختی", max_length=10,
        choices=[("easy", "آسان"), ("medium", "متوسط"), ("hard", "سخت")],
        default="medium",
    )

    class Meta:
        verbose_name = "سوال"
        verbose_name_plural = "بانک سوالات"
        ordering = ["course", "id"]

    def __str__(self):
        return self.text[:60]


class Exam(TimeStamped):
    course = models.ForeignKey(
        Course, verbose_name="دوره", on_delete=models.CASCADE, related_name="exams"
    )
    teacher = models.ForeignKey(
        Teacher, verbose_name="استاد", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="exams",
    )
    title = models.CharField("عنوان", max_length=160)
    description = models.TextField("توضیح", blank=True)
    questions = models.ManyToManyField(Question, verbose_name="سوالات", related_name="exams")
    duration_minutes = models.PositiveSmallIntegerField("مدت (دقیقه)", default=30)
    start_at = models.DateTimeField("شروع", null=True, blank=True)
    end_at = models.DateTimeField("پایان", null=True, blank=True)
    pass_score = models.PositiveSmallIntegerField("نمره قبولی", default=50)
    max_attempts = models.PositiveSmallIntegerField("حداکثر تلاش", default=1)
    negative_marking = models.BooleanField("نمره منفی", default=False)
    shuffle_questions = models.BooleanField("سوالات تصادفی", default=True)
    is_active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "آزمون"
        verbose_name_plural = "آزمون‌ها"
        ordering = ["-start_at"]

    def __str__(self):
        return f"{self.title} — {self.course.name}"

    @property
    def total_score(self):
        return sum(q.score for q in self.questions.all()) or 1


class ExamAttempt(TimeStamped):
    exam = models.ForeignKey(
        Exam, verbose_name="آزمون", on_delete=models.CASCADE, related_name="attempts"
    )
    enrollment = models.ForeignKey(
        StudentCourseTeacher, verbose_name="ثبت‌نام", on_delete=models.CASCADE,
        related_name="exam_attempts",
    )
    started_at = models.DateTimeField("شروع", auto_now_add=True)
    submitted_at = models.DateTimeField("ارسال", null=True, blank=True)
    score = models.DecimalField(
        "نمره", max_digits=6, decimal_places=1, null=True, blank=True
    )
    is_submitted = models.BooleanField("ارسال‌شده", default=False)
    needs_manual_grading = models.BooleanField("نیازمند تصحیح", default=False)

    class Meta:
        verbose_name = "تلاش آزمون"
        verbose_name_plural = "تلاش‌های آزمون"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.enrollment} — {self.exam.title}"

    @property
    def percent(self) -> int:
        if self.score is None:
            return 0
        return round(float(self.score) / float(self.exam.total_score) * 100)


class ExamAnswer(TimeStamped):
    attempt = models.ForeignKey(
        ExamAttempt, verbose_name="تلاش", on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        Question, verbose_name="سوال", on_delete=models.CASCADE, related_name="answers"
    )
    selected_option = models.CharField("گزینه", max_length=1, blank=True)
    selected_bool = models.BooleanField("صحیح/غلط", null=True, blank=True)
    text_answer = models.TextField("پاسخ", blank=True)
    is_correct = models.BooleanField("درست", null=True, blank=True)
    awarded_score = models.DecimalField(
        "نمره داده‌شده", max_digits=5, decimal_places=1, null=True, blank=True
    )

    class Meta:
        verbose_name = "پاسخ آزمون"
        verbose_name_plural = "پاسخ‌های آزمون"
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="unique_answer")
        ]

    def __str__(self):
        return f"{self.attempt_id} — {self.question_id}"



class Certificate(TimeStamped):
    """گواهی پایان دوره."""

    enrollment = models.OneToOneField(
        StudentCourseTeacher, verbose_name="ثبت‌نام", on_delete=models.CASCADE,
        related_name="certificate",
    )
    serial = models.CharField("شماره سریال", max_length=24, unique=True, db_index=True)
    title = models.CharField("عنوان گواهی", max_length=200)
    issued_at = models.DateTimeField("تاریخ صدور", default=timezone.now)
    grade = models.DecimalField(
        "معدل", max_digits=5, decimal_places=2, null=True, blank=True
    )
    hours = models.PositiveSmallIntegerField("ساعت آموزش", default=0)
    is_valid = models.BooleanField("معتبر", default=True)

    class Meta:
        verbose_name = "گواهی پایان دوره"
        verbose_name_plural = "گواهی‌های پایان دوره"
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.serial} — {self.enrollment.student.person.full_name}"


class Notification(TimeStamped):
    class Kind(models.TextChoices):
        ASSIGNMENT = "assignment", "تکلیف"
        EXAM = "exam", "آزمون"
        CLASS = "class", "کلاس"
        GRADE = "grade", "نمره"
        CERTIFICATE = "certificate", "گواهی"
        TUITION = "tuition", "شهریه"
        SYSTEM = "system", "سیستمی"

    user = models.ForeignKey(
        Users, verbose_name="کاربر", on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField("نوع", max_length=20, choices=Kind.choices, default=Kind.SYSTEM)
    title = models.CharField("عنوان", max_length=160)
    body = models.CharField("متن", max_length=300, blank=True)
    url = models.CharField("لینک", max_length=200, blank=True)
    is_read = models.BooleanField("خوانده‌شده", default=False)

    class Meta:
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان‌ها"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return f"{self.user.username} — {self.title}"


class AuditLog(TimeStamped):


    class Action(models.TextChoices):
        LOGIN = "login", "ورود"
        LOGOUT = "logout", "خروج"
        CREATE = "create", "ایجاد"
        UPDATE = "update", "ویرایش"
        DELETE = "delete", "حذف"
        GRADE = "grade", "ثبت نمره"
        ISSUE = "issue", "صدور گواهی"

    user = models.ForeignKey(
        Users, verbose_name="کاربر", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="audit_logs",
    )
    action = models.CharField("اقدام", max_length=20, choices=Action.choices)
    entity = models.CharField("موجودیت", max_length=80)
    entity_id = models.CharField("شناسه", max_length=40, blank=True)
    detail = models.JSONField("جزئیات", default=dict, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)

    class Meta:
        verbose_name = "لاگ فعالیت"
        verbose_name_plural = "لاگ فعالیت‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.get_action_display()}"
