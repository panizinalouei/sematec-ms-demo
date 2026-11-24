
import json
import random
from datetime import date, time, timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from lms.models import (Assignment, AssignmentSubmission, Attendance, AuditLog,
                        Certificate, Certification, ClassSession, Classroom,
                        Course, Department, Education, EducationCategory,
                        Employee, Exam, ExamAnswer, ExamAttempt, Job, Lesson,
                        LessonProgress, Notification, Person, Question, Student,
                        StudentCourseTeacher, StudySession, Teacher,
                        TeacherCertification, Users)



random.seed(1405)

CATEGORIES = [
    ("برنامه‌نویسی", "programming", "code", "#004AAD"),
    ("شبکه، زیرساخت و DevOps", "network", "network", "#0E7490"),
    ("دیتابیس", "database", "database", "#7C3AED"),
    ("داده، BI و هوش مصنوعی", "data-ai", "brain", "#DB2777"),
    ("امنیت سایبری", "security", "shield", "#DC2626"),
    ("مدیریت IT", "it-management", "briefcase", "#059669"),
    ("تحلیل و طراحی نرم‌افزار", "analysis", "layers", "#EA580C"),
    ("کودکان و نوجوانان", "kids", "sparkles", "#F59E0B"),
    ("مهارت‌های کامپیوتر", "computer-skills", "monitor", "#475569"),
]

# (کد, عنوان, انگلیسی, نامک, دسته, سطح, ساعت, قیمت, کاور, شاخص, توضیح)
COURSES = [
    ("PY-101", "برنامه‌نویسی با پایتون Python", "Python Programming", "python-basic",
     "programming", "basic", 40, 7_500_000, "python-basic.webp", True,
     "شروع مسیر برنامه‌نویسی از صفر؛ متغیرها، حلقه‌ها، توابع، شی‌گرایی و کار با فایل.",
     "متغیرها و انواع داده|شرط‌ها و حلقه‌ها|توابع و ماژول‌ها|ساختارهای داده|شی‌گرایی مقدماتی|مدیریت خطا و فایل|کار با SQLite|پروژه پایانی"),
    ("PY-201", "پایتون پیشرفته Advanced Python", "Advanced Python", "python-advanced",
     "programming", "advanced", 40, 8_900_000, "python-advanced.webp", True,
     "ژنراتور، دکوریتور، همزمانی، الگوهای طراحی، تست و بهینه‌سازی کد.",
     "Iterator و Generator|مدیریت پکیج و venv|شی‌گرایی پیشرفته|الگوهای طراحی|عبارات باقاعده|functools و itertools|همزمانی و asyncio|تست و پروفایلینگ"),
    ("WEB-101", "طراحی سایت (HTML, CSS, JavaScript)", "Web Design", "web-design",
     "programming", "basic", 90, 12_900_000, "web-design.webp", True,
     "ساخت صفحات وب واکنش‌گرا با HTML5، CSS3، جاوااسکریپت و بوت‌استرپ.",
     "ساختار HTML|CSS پایه|Flexbox|Grid و Responsive|جاوااسکریپت مقدماتی|اعتبارسنجی فرم|بوت‌استرپ|انتشار سایت"),
    ("WEB-201", "برنامه‌نویسی React JS", "React JS", "react",
     "programming", "advanced", 40, 7_900_000, "react.webp", True,
     "کامپوننت، state management، اتصال به API، روتینگ و بهینه‌سازی performance.",
     "مبانی React و JSX|state و رویدادها|Hooks|روتینگ|اتصال به API|مدیریت state|بهینه‌سازی|پروژه پایانی"),
    ("WEB-301", "Next.js حرفه‌ای", "Next.js", "nextjs",
     "programming", "advanced", 40, 9_900_000, "next.webp", True,
     "App Router، رندر سمت سرور، Server Components، فرم‌ها و استقرار.",
     "معرفی App Router|Server Components|فرم‌ها و Server Actions|دیتابیس و Prisma|احراز هویت|استقرار"),
    ("WEB-251", "TypeScript جامع", "TypeScript", "typescript",
     "programming", "advanced", 32, 7_200_000, "typescript.webp", False,
     "تایپ‌های پیشرفته، generics، ابزارهای build و مهاجرت پروژه‌های JS.",
     "مبانی تایپ|interface و type|Generics|Decorators|ابزارهای build|مهاجرت پروژه"),
    ("DES-101", "طراحی تجربه و رابط کاربری UI/UX", "UI/UX Design", "ui-ux",
     "programming", "basic", 40, 8_900_000, "uiux.webp", True,
     "اصول طراحی، وایرفریم، فیگما، دیزاین سیستم و تست کاربر.",
     "مبانی تجربه کاربری|تحقیق کاربر|وایرفریم و پروتوتایپ|فیگما|دیزاین سیستم|تست کاربر"),
    ("MKT-101", "جامع آموزش سئو (SEO)", "SEO", "seo",
     "programming", "advanced", 30, 6_000_000, "seo.webp", False,
     "سئوی فنی، محتوایی و خارجی، تحلیل رقبا و ابزارهای سرچ کنسول.",
     "مبانی سئو|سئوی فنی|سئوی محتوایی|سئوی خارجی|تحلیل رقبا|ابزارها"),
    ("CS-101", "جامع آموزش سی‌شارپ (#C)", "C# Programming", "csharp",
     "programming", "basic", 60, 13_500_000, "csharp.webp", False,
     "از مبانی C# تا شی‌گرایی، مجموعه‌ها، کار با دیتابیس و رابط ویندوز.",
     "مبانی C#|شرط و حلقه|شی‌گرایی|مجموعه‌ها|اتصال به دیتابیس|رابط کاربری"),
    ("NET-101", "CCNA 200-301 با PNETLab", "CCNA 200-301", "ccna",
     "network", "basic", 60, 7_900_000, "ccna.webp", True,
     "مبانی شبکه، سوئیچینگ، مسیریابی، امنیت و اتوماسیون در آزمایشگاه مجازی.",
     "مبانی شبکه|سوئیچینگ|مسیریابی|سرویس‌های شبکه|امنیت شبکه|اتوماسیون|آزمایشگاه PNETLab"),
    ("SEC-101", "Security+ و مبانی امنیت", "CompTIA Security+", "security-plus",
     "security", "basic", 40, 9_500_000, "security.webp", False,
     "مدیریت ریسک، رمزنگاری، امنیت شبکه و پاسخ به رخداد.",
     "مدیریت ریسک|رمزنگاری|امنیت شبکه|پاسخ به رخداد|سیاست امنیتی"),
    ("OPS-201", "DevOps Administration Pack", "DevOps", "devops",
     "network", "advanced", 72, 18_900_000, "devops.webp", False,
     "Docker، Kubernetes، CI/CD، مانیتورینگ و زیرساخت به‌صورت کد.",
     "Docker|CI/CD|Kubernetes|Ansible|مانیتورینگ|Infrastructure as Code"),
    ("DBA-101", "SQL Server 2025 Implementation", "SQL Server", "sql-server",
     "database", "basic", 40, 11_500_000, "sql.webp", False,
     "طراحی دیتابیس، کوئری‌نویسی، ایندکس، بهینه‌سازی و مدیریت سرور.",
     "طراحی دیتابیس|کوئری‌نویسی|Index و اجرا|Stored Procedure|پشتیبان‌گیری|بهینه‌سازی"),
    ("JV-101", "Java SE 21", "Java SE 21", "java",
     "programming", "advanced", 48, 14_500_000, "java.webp", False,
     "شی‌گرایی، مجموعه‌ها، Stream API، multithreading و آماده‌سازی برای Spring.",
     "شی‌گرایی|مجموعه‌ها|Lambda و Stream|Multithreading|JDBC|آماده‌سازی Spring"),
    ("AI-101", "هوش مصنوعی مولد و ابزارها", "Generative AI", "generative-ai",
     "data-ai", "basic", 20, 6_400_000, "ai.webp", True,
     "کار عملی با مدل‌های زبانی، پرامپت‌نویسی، اتوماسیون و ساخت دستیار.",
     "مبانی مدل‌های زبانی|پرامپت‌نویسی|ابزارهای مولد|اتوماسیون کار|امنیت و اخلاق|پروژه"),
    ("BI-101", "Power BI و هوش تجاری", "Power BI", "powerbi",
     "data-ai", "intermediate", 36, 10_900_000, "bi.webp", False,
     "مدل‌سازی داده، DAX، داشبوردسازی و تحلیل کسب‌وکار.",
     "آشنایی با BI|مدل‌سازی داده|DAX|داشبوردسازی|Power Query|تحلیل کسب‌وکار"),
    ("NET-201", "Node.js و API", "Node.js", "nodejs",
     "programming", "advanced", 48, 8_900_000, "react.webp", False,
     "Express، MongoDB، REST و GraphQL، احراز هویت، تست و استقرار.",
     "مبانی Node|Express|MongoDB|REST API|JWT|تست|Docker"),
    ("SEC-201", "SOC Tier 1 — تحلیلگر امنیت", "SOC Analyst", "soc-tier1",
     "security", "intermediate", 48, 14_900_000, "security.webp", False,
     "پایش رویداد، تحلیل لاگ، پاسخ به رخداد و ابزارهای SIEM.",
     "مبانی SOC|لاگ و SIEM|تحلیل رخداد|Threat Hunting|گزارش‌نویسی"),
    ("ITM-101", "ITIL Foundation", "ITIL Foundation", "itil",
     "it-management", "basic", 24, 8_500_000, "devops.webp", False,
     "اصول مدیریت خدمات فناوری اطلاعات و چرخه عمر خدمت.",
     "مفاهیم ITIL|چرخه عمر خدمت|مدیریت رخداد|مدیریت تغییر"),
    ("ICDL-101", "مهارت‌های هفت‌گانه ICDL", "ICDL", "icdl",
     "computer-skills", "basic", 60, 6_900_000, "bi.webp", False,
     "مهارت‌های پایه کامپیوتر شامل ویندوز، آفیس، اینترنت و امنیت.",
     "ویندوز|Word|Excel|PowerPoint|اینترنت|امنیت پایه|مدیریت فایل"),
]

# نگاشت استاد به دوره — بر پایه تخصص واقعی هر استاد
TEACHER_COURSES = {
    "sepide-aliasghari": ["PY-101", "PY-201"],
    "saeed-zamani": ["WEB-101", "WEB-201", "WEB-301", "WEB-251", "CS-101", "MKT-101", "NET-201"],
    "vahid-qorbani": ["BI-101", "DBA-101"],
    "sina-ruzbeh": ["NET-101"],
    "hossein-noruzi": ["NET-101"],
    "poorbagher": ["SEC-101"],
    "arash-furuqi": ["OPS-201"],
    "ali-rahimdabagh": ["SEC-201"],
    "maziar-chitsaz": ["SEC-201"],
    "payam-lahe": ["AI-101"],
    "balal-madhaj": ["JV-101", "ITM-101"],
    "nayyere-bagheri": ["DES-101", "ICDL-101"],
}

STUDENTS = [
    ("سارا", "محمدی", "09120000001", "sara@sematec.ir", "تهران"),
    ("علی", "کریمی", "09120000002", "ali.k@sematec.ir", "کرج"),
    ("نگار", "رستمی", "09120000003", "negar@sematec.ir", "تهران"),
    ("محمد", "حسینی", "09120000004", "mohammad@sematec.ir", "اصفهان"),
    ("فاطمه", "احمدی", "09120000005", "fateme@sematec.ir", "تهران"),
    ("رضا", "نوری", "09120000006", "reza@sematec.ir", "شیراز"),
    ("مریم", "صادقی", "09120000007", "maryam@sematec.ir", "تهران"),
    ("حسین", "موسوی", "09120000008", "hossein@sematec.ir", "مشهد"),
    ("الهام", "کاظمی", "09120000009", "elham@sematec.ir", "تهران"),
    ("پویا", "شریفی", "09120000010", "pouya@sematec.ir", "تبریز"),
    ("زهرا", "یوسفی", "09120000011", "zahra@sematec.ir", "قم"),
    ("امیرحسین", "طاهری", "09120000012", "amir@sematec.ir", "تهران"),
]


def demo_expertise(slug: str, desc: str) -> tuple[str, str]:
    """(عنوان، تخصص) از متن واقعی صفحه استاد."""
    table = {
        "sina-ruzbeh": ("مهندس ارشد اتوماسیون شبکه", "شبکه، سیسکو، اتوماسیون و DevNet"),
        "saeed-zamani": ("مدرس ارشد نرم‌افزار و وب", "C#، .NET، React، TypeScript، SEO"),
        "maziar-chitsaz": ("دکتری منطق، متخصص امنیت", "امنیت شبکه، سیسکو و زیرساخت"),
        "vahid-qorbani": ("تحلیلگر داده و دیتابیس", "داده، BI، Power BI و SQL Server"),
        "ali-rahimdabagh": ("متخصص SOC و DFIR", "امنیت، SOC، DFIR و Threat Hunting"),
        "balal-madhaj": ("متخصص معماری فناوری", "Java، معماری فناوری، ITIL و مدیریت IT"),
        "payam-lahe": ("فعال هوش مصنوعی", "هوش مصنوعی و مارکتینگ دیجیتال"),
        "dariush-tasdiqi": ("مدرس باتجربه شبکه", "شبکه، سیسکو و زیرساخت"),
        "sanaz-abbaszadeh": ("مدرس داده و تحلیل", "داده، تحلیل و هوش تجاری"),
        "sepide-aliasghari": ("مدرس پایتون", "پایتون و برنامه‌نویسی"),
        "sadegh-ahmadi": ("کارشناس امنیت", "امنیت شبکه و پاسخ به رخداد"),
        "mohammdreza-bardal": ("مدرس برنامه‌نویسی", "برنامه‌نویسی و توسعه نرم‌افزار"),
    }
    if slug in table:
        return table[slug]
    if desc and "درباره مدرس" not in desc:
        return ("مدرس تخصصی سماتک", desc[:80])
    return ("مدرس تخصصی سماتک", "دوره‌های تخصصی IT")


class Command(BaseCommand):
    help = "داده نمایشی کامل LMS"

    @transaction.atomic
    def handle(self, *args, **opts):
        self.stdout.write("پاک‌سازی...")
        for m in (Notification, AuditLog, Certificate, ExamAnswer, ExamAttempt, Exam,
                  Question, AssignmentSubmission, Assignment, Attendance, ClassSession,
                  Classroom, LessonProgress, StudySession, Lesson,
                  StudentCourseTeacher, TeacherCertification, Certification,
                  Teacher, Student, Employee, Users, Person, Course, EducationCategory,
                  Department, Job, Education):
            m.objects.all().delete()

        self.stdout.write("دپارتمان، شغل، تحصیلات...")
        dept_it, _ = Department.objects.get_or_create(name="فناوری اطلاعات")
        dept_edu, _ = Department.objects.get_or_create(name="آموزش")
        Department.objects.get_or_create(name="شبکه")
        job_teacher, _ = Job.objects.get_or_create(title="مدرس")
        Job.objects.get_or_create(title="کارشناس آموزش")
        Job.objects.get_or_create(title="ناظر آموزشی")
        Job.objects.get_or_create(title="مدیر آموزش")
        bsc, _ = Education.objects.get_or_create(name="کارشناسی")
        msc, _ = Education.objects.get_or_create(name="کارشناسی ارشد")
        phd, _ = Education.objects.get_or_create(name="دکتری")

        self.stdout.write("دسته‌بندی‌ها...")
        cats = {}
        for i, (name, slug, icon, color) in enumerate(CATEGORIES):
            cats[slug] = EducationCategory.objects.create(
                name=name, slug=slug, icon=icon, color=color, order=i
            )

        self.stdout.write("دوره‌ها...")
        course_map = {}
        for code, title, en, slug, cat, level, hours, price, cover, featured, desc, syllabus in COURSES:
            c = Course.objects.create(
                course_code=code, name=title, english_name=en, slug=slug,
                category=cats[cat], level=level, duration=hours, tuition=price,
                description=desc,
                syllabus="\n".join(syllabus.split("|")),
                course_type=random.choice(["hybrid", "online", "in_person"]),
                capacity=random.choice([20, 25, 30]), status="published",
                published_at=timezone.now() - timedelta(days=random.randint(20, 400)),
            )
            cover_path = Path(settings.MEDIA_ROOT) / "courses" / cover
            if cover_path.exists():
                c.cover.name = f"courses/{cover}"
                c.save(update_fields=["cover"])
            course_map[code] = c
            # جلسات
            items = syllabus.split("|")
            order = 1
            for i, item in enumerate(items):
                Lesson.objects.create(
                    course=c, title=f"جلسه {i+1}: {item}", order=order,
                    description=f"در این جلسه {item} به‌صورت عملی بررسی می‌شود.",
                    duration_minutes=random.choice([90, 120, 150]),
                    kind=Lesson.Kind.VIDEO,
                    is_preview=(i == 0),
                )
                order += 1

        self.stdout.write("اساتید...")
        teachers_data = json.load(open(
            Path(settings.BASE_DIR) / "lms" / "seed_data" / "teachers_raw.json",
            encoding="utf-8"))
        teachers = {}
        for i, t in enumerate(teachers_data):
            name = t["name"].strip()
            parts = name.split()
            first, last = (parts[0], " ".join(parts[1:])) if len(parts) > 1 else (name, "")
            title, expertise = demo_expertise(t["slug"], t.get("desc", ""))
            person = Person.objects.create(
                persian_first_name=first, persian_last_name=last or "—",
                phone_number=f"0935{1000000 + i}", email_address=f"{t['slug']}@sematec.ir",
                education=random.choice([bsc, msc, msc, phd]),
                home_address="تهران",
            )
            if t.get("photo_file"):
                person.photo.name = f"teachers/{t['photo_file']}"
                person.save(update_fields=["photo"])
            teacher = Teacher.objects.create(
                person=person,
                teacher_code=f"TC-{1000 + i}",
                headline=title, expertise=expertise,
                bio=t.get("desc", "")[:400] if "درباره" not in t.get("desc", "") else
                    f"{name}، {title} در آموزشگاه سماتک.",
                teaching_hours=random.choice([1200, 2400, 3800, 5200, 15000]),
                years_experience=random.randint(3, 18),
                is_featured=(t["slug"] in {"sina-ruzbeh", "maziar-chitsaz",
                                            "vahid-qorbani", "saeed-zamani",
                                            "sepide-aliasghari"}),
                start_date=date(2020, 1, 1) + timedelta(days=random.randint(0, 1500)),
            )
            cert_title = expertise.split("،")[0]
            cert, _ = Certification.objects.get_or_create(
                title=cert_title[:120], vendor="آموزشگاه سماتک"
            )
            TeacherCertification.objects.create(
                teacher=teacher, certification=cert,
                expire_date=date(2027, 6, 30),
            )
            teachers[t["slug"]] = teacher
            Users.objects.create(
                username=t["slug"], password=make_password("Demo@1405"),
                role=Users.Role.TEACHER, person=person,
                first_name=first, last_name=last or "—",
            )

        # تخصیص درس‌ها — بقیه اساتید به دوره‌های مرتبط
        all_teachers = list(teachers.values())
        for code, course in course_map.items():
            assigned = []
            for slug, codes in TEACHER_COURSES.items():
                if code in codes and slug in teachers:
                    assigned.append(teachers[slug])
            if not assigned:
                assigned = [random.choice(all_teachers)]
            course.teachers.set(assigned)
            # کلاس
            start = date.today() + timedelta(days=random.randint(-30, 25))
            classroom = Classroom.objects.create(
                course=course, teacher=assigned[0],
                name=random.choice(["کلاس پاییزی", "گروه عصر", "گروه صبح", "کلاس زمستانی"]),
                mode=random.choice(["hybrid", "online", "in_person"]),
                start_date=start, end_date=start + timedelta(days=90),
                capacity=course.capacity,
                meeting_days=random.choice(["دوشنبه", "سه‌شنبه", "شنبه", "چهارشنبه"]),
                meeting_time="۱۶:۳۰ - ۲۰:۳۰",
                online_link="https://meet.sematec.ir/class",
                location="سهروردی شمالی، پلاک ۱",
            )
            for n in range(1, 7):
                sdate = start + timedelta(days=7 * (n - 1))
                ClassSession.objects.create(
                    classroom=classroom, number=n,
                    title=f"جلسه {n}",
                    date=sdate, start_time=time(16, 30), end_time=time(20, 30),
                    is_held=sdate < date.today(),
                )

        self.stdout.write("کاربران مدیریتی...")
        def staff_user(username, first, last, role, title, phone, job):
            person = Person.objects.create(
                persian_first_name=first, persian_last_name=last,
                phone_number=phone, email_address=f"{username}@sematec.ir",
                education=msc, home_address="تهران",
            )
            Employee.objects.create(
                person=person, employee_code=f"EMP-{Employee.objects.count()+1001}",
                department=dept_edu if role == Users.Role.STAFF else dept_it,
                job=job, hire_date=date(2021, 5, 1),
            )
            return Users.objects.create(
                username=username, password=make_password("Demo@1405"),
                role=role, person=person, first_name=first, last_name=last,
                is_admin=(role == Users.Role.ADMIN),
            )

        admin_user = staff_user("admin", "مدیر", "سامانه", Users.Role.ADMIN,
                                "مدیر سامانه", "09120000000", Job.objects.get(title="مدیر آموزش"))
        staff_user("supervisor", "نگار", "نظری", Users.Role.SUPERVISOR,
                   "ناظر آموزشی", "09120000020", Job.objects.get(title="ناظر آموزشی"))
        staff_user("staff", "نگین", "کریمی", Users.Role.STAFF,
                   "کارشناس آموزش", "09120000021", Job.objects.get(title="کارشناس آموزش"))

        self.stdout.write("دانشجویان...")
        students = []
        for i, (first, last, phone, email, city) in enumerate(STUDENTS, start=1):
            person = Person.objects.create(
                persian_first_name=first, persian_last_name=last,
                phone_number=phone, email_address=email,
                education=random.choice([bsc, msc]), home_address=city,
            )
            st = Student.objects.create(
                person=person, student_code=f"ST-{1000 + i}",
                father_name="—", work_address="",
            )
            username = email.split("@")[0]
            Users.objects.create(
                username=username, password=make_password("Demo@1405"),
                role=Users.Role.STUDENT, person=person,
                first_name=first, last_name=last,
            )
            students.append(st)
        # دانشجوی اصلی برای دمو
        main = students[0]

        self.stdout.write("ثبت‌نام‌ها و پیشرفت...")
        all_courses = list(course_map.values())
        main_courses = [course_map["PY-101"], course_map["WEB-201"], course_map["NET-101"]]
        for i, course in enumerate(main_courses):
            en = StudentCourseTeacher.objects.create(
                student=main, course=course, teacher=course.teachers.first(),
                status="active", tuition_paid=course.tuition // 2,
                progress=0,
            )
            lessons = list(course.lessons.all())
            done_count = 4 + i * 2
            for lesson in lessons[:done_count]:
                LessonProgress.objects.create(
                    enrollment=en, lesson=lesson, is_completed=True,
                    completed_at=timezone.now() - timedelta(days=random.randint(2, 30)),
                )
            en.recalculate_progress()

        for student in students[1:]:
            for course in random.sample(all_courses, random.randint(1, 3)):
                progress = random.choice([0, 15, 25, 40, 55, 70, 85, 100])
                en = StudentCourseTeacher.objects.create(
                    student=student, course=course, teacher=course.teachers.first(),
                    status="completed" if progress == 100 else "active",
                    tuition_paid=course.tuition if progress > 60 else course.tuition // 2,
                    progress=progress,
                    enrolled_at=timezone.now() - timedelta(days=random.randint(2, 240)),
                )
                lessons = list(course.lessons.all())
                for lesson in lessons[: int(len(lessons) * progress / 100)]:
                    LessonProgress.objects.create(enrollment=en, lesson=lesson, is_completed=True)
                if progress == 100:
                    en.completed_at = timezone.now() - timedelta(days=random.randint(1, 40))
                    en.save()
                # حضور
                classroom = course.classrooms.first()
                if classroom:
                    for s in classroom.sessions.filter(is_held=True):
                        Attendance.objects.create(
                            session=s, enrollment=en,
                            status=random.choices(
                                ["present", "late", "absent", "excused"],
                                weights=[76, 12, 8, 4])[0],
                        )

        self.stdout.write("تکالیف...")
        for course in [course_map["PY-101"], course_map["WEB-201"], course_map["NET-101"]]:
            for n, (title, desc, delta) in enumerate([
                ("تمرین اول", "تمرین‌های فصل اول را حل و فایل پاسخ را ارسال کنید.", -14),
                ("پروژه میانی", "پروژه کوچک مطابق توضیحات کلاس را به‌صورت ZIP ارسال کنید.", 6),
                ("پروژه پایانی", "پروژه نهایی را با مستندات کامل ارسال کنید.", 20),
            ], start=1):
                a = Assignment.objects.create(
                    course=course, teacher=course.teachers.first(),
                    title=f"{title} — {course.name}",
                    description=desc,
                    due_date=timezone.now() + timedelta(days=delta),
                    max_score=100,
                )
                for en in course.enrollments.filter(is_active=True)[:7]:
                    if random.random() < 0.65:
                        sub = AssignmentSubmission.objects.create(
                            assignment=a, enrollment=en,
                            note="پاسخ تمرین پیوست شد.",
                            status="submitted",
                        )
                        if delta < 0:
                            sub.score = random.choice([68, 74, 82, 88, 94])
                            sub.feedback = random.choice([
                                "ساختار کد تمیز است؛ مستندسازی را کامل کنید.",
                                "عالی بود، خروجی مطابق انتظار است.",
                                "به بخش مدیریت خطا بیشتر دقت کنید.",
                            ])
                            sub.status = "graded"
                            sub.graded_at = timezone.now() - timedelta(days=random.randint(1, 8))
                            sub.graded_by = course.teachers.first().person.account
                            sub.save()

        self.stdout.write("آزمون‌ها...")
        bank = {
            "PY-101": [
                ("خروجی type(3/2) در پایتون چیست؟", "mcq", ["float", "int", "str", "خطا"], "a"),
                ("کدام ساختار قابل تغییر نیست؟", "mcq", ["لیست", "تاپل", "دیکشنری", "مجموعه"], "b"),
                ("شمارش ایندکس پایتون از صفر شروع می‌شود.", "true_false", [], True),
                ("تفاوت لیست و تاپل را بنویسید.", "descriptive", [], None),
            ],
            "WEB-201": [
                ("کدام hook برای state است؟", "mcq", ["useEffect", "useState", "useRef", "useMemo"], "b"),
                ("props از داخل کامپوننت فرزند قابل تغییر است.", "true_false", [], False),
                ("مفهوم Virtual DOM را توضیح دهید.", "descriptive", [], None),
            ],
            "NET-101": [
                ("مسیریابی در کدام لایه OSI انجام می‌شود؟", "mcq", ["۲", "۳", "۴", "۷"], "b"),
                ("VLAN دامنه broadcast را جدا می‌کند.", "true_false", [], True),
                ("پورت پیش‌فرض SSH کدام است؟", "mcq", ["21", "22", "23", "443"], "b"),
            ],
        }
        for code, qs in bank.items():
            course = course_map[code]
            q_objs = []
            for text, kind, options, correct in qs:
                q_objs.append(Question.objects.create(
                    course=course, text=text, kind=kind,
                    option_a=options[0] if len(options) > 0 else "",
                    option_b=options[1] if len(options) > 1 else "",
                    option_c=options[2] if len(options) > 2 else "",
                    option_d=options[3] if len(options) > 3 else "",
                    correct_option=correct or "",
                    score=random.choice([1, 1, 2]),
                ))
            exam = Exam.objects.create(
                course=course, teacher=course.teachers.first(),
                title=f"آزمون میان‌دوره {course.name}",
                duration_minutes=30, pass_score=50,
                start_at=timezone.now() - timedelta(days=3),
                end_at=timezone.now() + timedelta(days=12),
            )
            exam.questions.set(q_objs)
            en = course.enrollments.filter(student=main).first()
            if en:
                attempt = ExamAttempt.objects.create(
                    exam=exam, enrollment=en, is_submitted=True,
                    submitted_at=timezone.now() - timedelta(days=2),
                )
                total = 0
                for q in q_objs:
                    ans = ExamAnswer.objects.create(attempt=attempt, question=q)
                    if q.kind == "mcq":
                        ans.selected_option = random.choice(["a", "b", "c", "d"])
                        ans.is_correct = ans.selected_option == q.correct_option
                        ans.awarded_score = q.score if ans.is_correct else 0
                    elif q.kind == "true_false":
                        ans.selected_bool = random.choice([True, False])
                        ans.is_correct = ans.selected_bool == q.correct_bool
                        ans.awarded_score = q.score if ans.is_correct else 0
                    else:
                        ans.text_answer = "پاسخ تشریحی نمونه"
                        ans.awarded_score = float(q.score) * 0.8
                    ans.save()
                    total += float(ans.awarded_score or 0)
                attempt.score = total
                attempt.save()
                en.recalculate_progress()

        # دانشجوی اصلی: یک دوره کامل + گواهی، برای نمایش کامل چرخه
        main_en = StudentCourseTeacher.objects.filter(student=main, course=course_map["PY-101"]).first()
        if main_en:
            for lesson in main_en.course.lessons.all():
                LessonProgress.objects.get_or_create(
                    enrollment=main_en, lesson=lesson,
                    defaults={"is_completed": True, "completed_at": timezone.now()},
                )
            for a in main_en.course.assignments.all():
                AssignmentSubmission.objects.update_or_create(
                    assignment=a, enrollment=main_en,
                    defaults={"status": AssignmentSubmission.Status.GRADED,
                              "score": 90, "feedback": "ارزیابی استاد ثبت شد.",
                              "graded_at": timezone.now()},
                )
            main_en.score = 18.5
            main_en.recalculate_progress()
            if main_en.progress >= 100:
                Certificate.objects.create(
                    enrollment=main_en, serial="SMTC-2026-2001",
                    title=f"گواهی پایان دوره {main_en.course.name}",
                    hours=main_en.course.duration, grade=18.5,
                )

        self.stdout.write("گواهی و اعلان...")
        for i, en in enumerate(StudentCourseTeacher.objects.filter(progress=100)[:6]):
            Certificate.objects.get_or_create(
                enrollment=en, defaults=dict(serial=f"SMTC-2026-{1000 + i}",
                title=f"گواهی پایان دوره {en.course.name}",
                hours=en.course.duration,
                grade=random.choice([16.5, 17.25, 18.0, 19.0]),
            ))

        for user in Users.objects.filter(role__in=["student", "teacher"]).order_by("id")[:3]:
            Notification.objects.create(
                user=user, kind="assignment", title="تکلیف جدید",
                body="برای دوره‌های شما تکلیف ثبت شد.", url="/assignments/",
            )
        Notification.objects.create(
            user=admin_user, kind="system", title="گزارش ماهانه آماده است",
            body="گزارش ثبت‌نام و درآمد در بخش گزارش‌ها.", url="/reports/",
        )

        self.stdout.write(self.style.SUCCESS(
            f"آماده شد — دوره: {Course.objects.count()} | استاد: {Teacher.objects.count()} | "
            f"دانشجو: {Student.objects.count()} | ثبت‌نام: {StudentCourseTeacher.objects.count()} | "
            f"آزمون: {Exam.objects.count()} | گواهی: {Certificate.objects.count()}"))
        self.stdout.write("ورود مدیر: admin / Demo@1405")
        self.stdout.write("ورود دانشجو: sara / Demo@1405")
