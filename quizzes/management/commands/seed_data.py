"""Seed EduHub with Software Engineering topics, quizzes, questions and demo users.

Run:  python manage.py seed_data
      python manage.py seed_data --fresh   (wipe quiz data first)
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from quizzes.models import (
    Answer, Attempt, Choice, Question, Quiz, Topic, User,
)

# --------------------------------------------------------------------------- #
# The Software Engineering question bank.
# Each choice is (text, is_correct). Exactly one correct answer per question.
# --------------------------------------------------------------------------- #
CONTENT = [
    {
        "name": "Introduction to Software Engineering",
        "icon": "bi-mortarboard", "color": "#3b5b8c", "difficulty": "BEGINNER",
        "description": "Foundations: what software engineering is, software characteristics, the SE layers, myths and ethics.",
        "questions": [
            ("Which statement best defines software engineering?", "Definition",
             "The IEEE defines SE as a systematic, disciplined, quantifiable approach to software.",
             [("A systematic, disciplined, quantifiable approach to the development, operation and maintenance of software", True),
              ("Writing code as quickly as possible", False),
              ("Designing computer hardware", False),
              ("Only the testing stage of a program", False)]),
            ("Which is NOT one of Pressman's four layers of software engineering?", "SE layers",
             "The layers are a quality focus, process, methods and tools - hardware is not one of them.",
             [("Hardware", True), ("Quality focus", False), ("Process", False), ("Tools", False)]),
            ("How does software differ from hardware?", "Software characteristics",
             "Software is engineered/developed, not manufactured, and it does not physically wear out.",
             [("Software is engineered, not manufactured in the classical sense", True),
              ("Software wears out due to friction", False),
              ("Software is built only from raw materials", False),
              ("Software cost is mostly raw materials", False)]),
            ("Complete the statement: 'Software does not wear out, but it ___.'", "Software characteristics",
             "Maintenance changes introduce defects over time, so software deteriorates.",
             [("deteriorates", True), ("rusts", False), ("evaporates", False), ("melts", False)]),
            ("Which is a classic management software myth?", "Software myths",
             "Brooks's Law: adding people to a late project usually makes it later.",
             [("If we fall behind, we can just add more programmers to catch up", True),
              ("Requirements must be documented", False),
              ("Testing reduces defects", False),
              ("Design before coding helps", False)]),
            ("Maintainability, reliability and security are examples of:", "Quality",
             "These '-ilities' are quality attributes / non-functional requirements.",
             [("Quality attributes", True), ("Algorithms", False), ("Compilers", False), ("Data types", False)]),
            ("Which is part of professional and ethical responsibility in SE?", "Ethics",
             "Codes of ethics (ACM/IEEE) require confidentiality and respect for intellectual property.",
             [("Respecting confidentiality and intellectual property", True),
              ("Sharing client data freely", False),
              ("Copying competitor code", False),
              ("Ignoring quality to hit deadlines", False)]),
        ],
    },
    {
        "name": "Software Process Models",
        "icon": "bi-diagram-3", "color": "#2f7a78", "difficulty": "BEGINNER",
        "description": "Waterfall, incremental, prototyping, spiral, RAD and the V-model.",
        "questions": [
            ("In the Waterfall model, the phases are:", "Waterfall",
             "Waterfall is a linear sequential model - each phase finishes before the next starts.",
             [("Sequential, each completed before the next begins", True),
              ("Executed fully in parallel", False),
              ("Repeated in short sprints", False),
              ("Optional and skippable", False)]),
            ("A major drawback of the Waterfall model is that it:", "Waterfall",
             "Requirements are frozen early, so change is costly and hard to accommodate.",
             [("Cannot easily accommodate changing requirements", True),
              ("Produces no documentation", False),
              ("Requires no planning", False),
              ("Only works for games", False)]),
            ("Which model builds a quick mock-up to clarify unclear requirements?", "Prototyping",
             "Prototyping creates a throwaway/evolutionary version to refine requirements with users.",
             [("Prototyping model", True), ("Waterfall", False), ("V-model", False), ("Big-bang", False)]),
            ("The Spiral model is primarily driven by:", "Spiral",
             "Boehm's Spiral model performs risk analysis in every loop.",
             [("Risk analysis in each cycle", True), ("Fixed-price contracts", False),
              ("Daily stand-ups", False), ("Writing tests first", False)]),
            ("The Incremental model delivers software by:", "Incremental",
             "It delivers usable increments of functionality progressively.",
             [("Building and delivering it in increments of functionality", True),
              ("Delivering everything only at the very end", False),
              ("Never delivering until it is perfect", False),
              ("Skipping the design phase", False)]),
            ("RAD (Rapid Application Development) emphasizes:", "RAD",
             "RAD uses reusable components and very short development cycles.",
             [("Short cycles using component-based construction", True),
              ("Multi-year monolithic builds", False),
              ("No user involvement", False),
              ("Hardware design", False)]),
            ("The V-model extends Waterfall by emphasizing:", "V-model",
             "Each development phase is paired with a corresponding testing phase.",
             [("The link between development phases and their testing phases", True),
              ("Continuous deployment", False), ("Pair programming", False), ("Risk loops", False)]),
        ],
    },
    {
        "name": "Agile & Scrum",
        "icon": "bi-lightning-charge", "color": "#a87b1f", "difficulty": "INTERMEDIATE",
        "description": "The Agile Manifesto, Scrum roles, artifacts and events, plus XP and Kanban.",
        "questions": [
            ("The Agile Manifesto values 'individuals and interactions over ___'.", "Agile Manifesto",
             "The first value: individuals and interactions over processes and tools.",
             [("processes and tools", True), ("working software", False),
              ("documentation", False), ("contracts", False)]),
            ("In Scrum, who owns and prioritizes the Product Backlog?", "Scrum roles",
             "The Product Owner maximizes product value and manages the backlog.",
             [("Product Owner", True), ("Scrum Master", False), ("Developers", False), ("Stakeholders", False)]),
            ("The Scrum Master's main responsibility is to:", "Scrum roles",
             "A servant-leader who facilitates the process and removes impediments.",
             [("Facilitate the process and remove impediments", True),
              ("Assign daily tasks to developers", False),
              ("Own the product vision", False),
              ("Approve the budget", False)]),
            ("Which of these is a Scrum artifact?", "Scrum artifacts",
             "Artifacts are the Product Backlog, Sprint Backlog and Increment.",
             [("Product Backlog", True), ("Gantt chart", False),
              ("Sprint Retrospective", False), ("Daily Scrum", False)]),
            ("A typical Scrum sprint lasts:", "Scrum events",
             "Sprints are time-boxed, usually one to four weeks.",
             [("1 to 4 weeks", True), ("1 day", False), ("6 months", False), ("2 years", False)]),
            ("In Extreme Programming (XP), pair programming means:", "XP",
             "Two developers share one workstation - a driver and a navigator.",
             [("Two programmers work together at one workstation", True),
              ("Two teams compete", False),
              ("A tester pairs with a manager", False),
              ("Code is written in pairs of files", False)]),
            ("Kanban primarily focuses on:", "Kanban",
             "Kanban visualizes workflow on a board and limits work in progress (WIP).",
             [("Visualizing workflow and limiting work in progress", True),
              ("Fixed-length sprints", False),
              ("Removing all documentation", False),
              ("Big upfront design", False)]),
        ],
    },
    {
        "name": "Requirements Engineering",
        "icon": "bi-card-checklist", "color": "#5f7a52", "difficulty": "BEGINNER",
        "description": "Functional vs non-functional requirements, elicitation, the SRS, validation and user stories.",
        "questions": [
            ("A functional requirement specifies:", "Functional vs non-functional",
             "Functional requirements describe specific behaviours the system must perform.",
             [("What the system should do (a specific behaviour)", True),
              ("How fast the system responds", False),
              ("The hardware budget", False),
              ("The programming language", False)]),
            ("'The system shall respond within 2 seconds' is a:", "Functional vs non-functional",
             "Response-time/performance is a non-functional (quality) requirement.",
             [("Non-functional requirement", True), ("Functional requirement", False),
              ("Use case", False), ("Test case", False)]),
            ("Gathering requirements from stakeholders is called:", "Elicitation",
             "Elicitation discovers requirements via interviews, observation, workshops, etc.",
             [("Requirements elicitation", True), ("Requirements coding", False),
              ("Requirements deployment", False), ("Requirements compilation", False)]),
            ("The document that formally records software requirements is the:", "SRS",
             "The Software Requirements Specification captures functional and non-functional requirements.",
             [("SRS (Software Requirements Specification)", True),
              ("User manual", False), ("Test plan", False), ("Release note", False)]),
            ("Requirements validation mainly checks that:", "Validation",
             "Validation ensures the requirements define the system the customer actually wants.",
             [("The requirements define what the customer really wants", True),
              ("The code compiles", False),
              ("The database is normalized", False),
              ("The UI is colourful", False)]),
            ("A short feature description from the user's perspective is a:", "User stories",
             "'As a <role>, I want <goal> so that <benefit>' is a user story.",
             [("User story", True), ("Gantt chart", False),
              ("Class diagram", False), ("Stored procedure", False)]),
            ("Which technique is used to prioritize requirements?", "Prioritization",
             "MoSCoW = Must have, Should have, Could have, Won't have.",
             [("MoSCoW", True), ("COCOMO", False), ("UML", False), ("SQL", False)]),
        ],
    },
    {
        "name": "Software Design & Architecture",
        "icon": "bi-bezier2", "color": "#7a4a68", "difficulty": "INTERMEDIATE",
        "description": "Cohesion and coupling, architectural patterns, design patterns and the SOLID principles.",
        "questions": [
            ("High cohesion within a module means:", "Cohesion",
             "Its elements are strongly related and focused on a single responsibility (good).",
             [("Its elements are strongly related and focused on one task", True),
              ("It depends on many other modules", False),
              ("It contains no functions", False),
              ("It is very large", False)]),
            ("Low coupling between modules is desirable because:", "Coupling",
             "Independent modules are easier to change and test. Aim: high cohesion, low coupling.",
             [("Modules become more independent and easier to change/test", True),
              ("It increases interdependencies", False),
              ("It removes all interfaces", False),
              ("It slows the system down", False)]),
            ("The MVC architectural pattern separates an application into:", "Architecture",
             "Model (data), View (UI) and Controller (logic).",
             [("Model, View and Controller", True),
              ("Module, Variable, Class", False),
              ("Method, Value, Constant", False),
              ("Memory, Video, CPU", False)]),
            ("The Singleton design pattern ensures that a class:", "Design patterns",
             "Has only one instance with a single global access point.",
             [("Has only one instance with a global access point", True),
              ("Has many instances", False),
              ("Cannot be instantiated", False),
              ("Runs in parallel", False)]),
            ("In SOLID, the 'O' stands for:", "SOLID",
             "Open/Closed Principle: open for extension, closed for modification.",
             [("Open/Closed Principle", True), ("Object Principle", False),
              ("Operation Principle", False), ("Output Principle", False)]),
            ("Which category does the 'Factory Method' pattern belong to?", "Design patterns",
             "Factory Method is a creational pattern (it deals with object creation).",
             [("Creational", True), ("Structural", False), ("Behavioural", False), ("Architectural", False)]),
            ("The Observer pattern is used to:", "Design patterns",
             "It defines a one-to-many dependency so dependents are notified of state changes.",
             [("Notify dependent objects automatically when state changes", True),
              ("Create a single instance", False),
              ("Wrap an incompatible interface", False),
              ("Sort data efficiently", False)]),
        ],
    },
    {
        "name": "UML & System Modeling",
        "icon": "bi-diagram-2", "color": "#a3493a", "difficulty": "INTERMEDIATE",
        "description": "Use case, class, sequence, activity and state diagrams and their notation.",
        "questions": [
            ("A Use Case diagram primarily models:", "Use case diagram",
             "It shows system functionality from the actors' (users') perspective.",
             [("System functionality from the user's perspective", True),
              ("The internal class structure", False),
              ("The database schema", False),
              ("The deployment hardware", False)]),
            ("In a class diagram, a solid line with a hollow triangle arrowhead means:", "Class diagram",
             "A hollow triangle denotes generalization / inheritance.",
             [("Inheritance (generalization)", True), ("Association", False),
              ("Aggregation", False), ("Dependency", False)]),
            ("A filled (solid) diamond in a class diagram denotes:", "Class diagram",
             "A filled diamond is composition - a strong 'owns' where parts die with the whole.",
             [("Composition", True), ("Aggregation", False), ("Inheritance", False), ("Realization", False)]),
            ("A hollow diamond in a class diagram denotes:", "Class diagram",
             "A hollow diamond is aggregation - a weaker 'has-a' relationship.",
             [("Aggregation", True), ("Composition", False), ("Inheritance", False), ("Dependency", False)]),
            ("Which UML diagram shows time-ordered messages between objects?", "Sequence diagram",
             "Sequence diagrams emphasize the order of messages over time.",
             [("Sequence diagram", True), ("Class diagram", False),
              ("Use case diagram", False), ("Component diagram", False)]),
            ("An Activity diagram is most like a:", "Activity diagram",
             "It models workflow/control flow, similar to a flowchart.",
             [("Flowchart showing workflow/control flow", True),
              ("Database ER diagram", False), ("Bar chart", False), ("Network map", False)]),
            ("A State machine diagram models:", "State diagram",
             "It shows an object's states and the event-driven transitions between them.",
             [("The states of an object and transitions between them", True),
              ("Only class attributes", False), ("Physical servers", False), ("Lines of code", False)]),
        ],
    },
    {
        "name": "Software Testing",
        "icon": "bi-bug", "color": "#b5562d", "difficulty": "INTERMEDIATE",
        "description": "Verification vs validation, test levels, black/white-box, test design, TDD and regression.",
        "questions": [
            ("Verification answers the question:", "V&V",
             "Verification = 'building the product right' (conformance to specification).",
             [("Are we building the product right?", True),
              ("Are we building the right product?", False),
              ("Is the customer happy?", False),
              ("Is the budget enough?", False)]),
            ("Validation answers the question:", "V&V",
             "Validation = 'building the right product' (meets user needs).",
             [("Are we building the right product?", True),
              ("Are we building the product right?", False),
              ("Is the code formatted?", False),
              ("Is it documented?", False)]),
            ("White-box testing is based on:", "Black vs white box",
             "White-box (structural) testing uses knowledge of the internal code and paths.",
             [("Knowledge of the internal code/structure", True),
              ("Only the requirements, ignoring code", False),
              ("User interviews", False),
              ("Random guesses", False)]),
            ("Black-box testing focuses on:", "Black vs white box",
             "Black-box (functional) testing checks inputs and outputs against the spec.",
             [("Inputs and expected outputs, without knowing the code", True),
              ("Code coverage metrics", False),
              ("Internal loops", False),
              ("Compiler flags", False)]),
            ("Testing individual components in isolation is called:", "Test levels",
             "Unit testing targets the smallest testable parts of the software.",
             [("Unit testing", True), ("System testing", False),
              ("Acceptance testing", False), ("Integration testing", False)]),
            ("In Test-Driven Development (TDD) you:", "TDD",
             "TDD cycle: write a failing test (red), make it pass (green), then refactor.",
             [("Write a failing test first, then code to pass it", True),
              ("Write all code, then never test", False),
              ("Test only after release", False),
              ("Skip refactoring", False)]),
            ("Boundary Value Analysis is a technique to:", "Test design",
             "BVA tests at the edges of input ranges, where defects often hide.",
             [("Test at the edges of input ranges", True),
              ("Test the database only", False),
              ("Measure performance", False),
              ("Generate UML", False)]),
            ("Re-running tests after changes to ensure nothing broke is:", "Regression",
             "Regression testing confirms existing functionality still works after a change.",
             [("Regression testing", True), ("Load testing", False),
              ("Alpha testing", False), ("Usability testing", False)]),
        ],
    },
    {
        "name": "Software Quality & Maintenance",
        "icon": "bi-patch-check", "color": "#4f6d5e", "difficulty": "INTERMEDIATE",
        "description": "Quality assurance vs control, maintenance types, refactoring, technical debt and metrics.",
        "questions": [
            ("Quality Assurance (QA) is mainly:", "QA vs QC",
             "QA is process-oriented (preventing defects); QC is product-oriented (finding them).",
             [("Process-oriented (preventing defects)", True),
              ("Product-oriented (finding defects)", False),
              ("Only about coding", False),
              ("Only about marketing", False)]),
            ("Fixing defects discovered after delivery is which maintenance type?", "Maintenance types",
             "Corrective maintenance repairs faults found after release.",
             [("Corrective", True), ("Adaptive", False), ("Perfective", False), ("Preventive", False)]),
            ("Modifying software to run on a new OS or hardware is:", "Maintenance types",
             "Adaptive maintenance adapts software to a changed environment.",
             [("Adaptive maintenance", True), ("Corrective", False),
              ("Perfective", False), ("Preventive", False)]),
            ("Adding new features or improving performance on request is:", "Maintenance types",
             "Perfective maintenance enhances or improves the software.",
             [("Perfective maintenance", True), ("Corrective", False),
              ("Adaptive", False), ("Preventive", False)]),
            ("Refactoring means:", "Refactoring",
             "Improving internal code structure without changing external behaviour.",
             [("Improving internal structure without changing behaviour", True),
              ("Adding new features", False),
              ("Rewriting from scratch in a new language", False),
              ("Deleting all tests", False)]),
            ("'Technical debt' refers to:", "Technical debt",
             "The future rework cost implied by choosing a quick, easy solution now.",
             [("The future cost of choosing a quick/easy solution now", True),
              ("Money owed to vendors", False),
              ("Server hosting fees", False),
              ("Open-source licensing", False)]),
            ("Cyclomatic complexity measures:", "Metrics",
             "McCabe's metric counts the number of independent paths through a program.",
             [("The number of independent paths through a program", True),
              ("Lines of comments", False),
              ("Number of developers", False),
              ("Disk usage", False)]),
        ],
    },
    {
        "name": "Project Management & Estimation",
        "icon": "bi-kanban", "color": "#8a5a2b", "difficulty": "ADVANCED",
        "description": "Estimation (COCOMO, function points), scheduling, the critical path and risk management.",
        "questions": [
            ("COCOMO is a model used for:", "Estimation",
             "The Constructive Cost Model estimates effort/cost, typically from size (KLOC).",
             [("Software cost/effort estimation", True),
              ("Test automation", False), ("UML modelling", False), ("Version control", False)]),
            ("Function Point Analysis estimates size based on:", "Estimation",
             "FPA measures functionality (inputs, outputs, inquiries, files, interfaces), language-independent.",
             [("System functionality (inputs, outputs, files, interfaces)", True),
              ("Lines of code only", False),
              ("Number of bugs", False),
              ("Team size", False)]),
            ("The Critical Path in a schedule is:", "Scheduling",
             "The longest chain of dependent tasks; it determines the minimum project duration.",
             [("The longest path of dependent tasks setting the minimum duration", True),
              ("The shortest task", False),
              ("The cheapest path", False),
              ("The path with the most people", False)]),
            ("A Gantt chart is used to:", "Scheduling",
             "It visualizes the schedule - tasks and their durations over time.",
             [("Visualize the project schedule over time", True),
              ("Model classes", False), ("Store data", False), ("Write code", False)]),
            ("Risk exposure is typically calculated as:", "Risk",
             "Risk exposure = probability of the risk × its impact/loss.",
             [("Probability × Impact", True), ("Cost + Time", False),
              ("Lines of code / team", False), ("Bugs × testers", False)]),
            ("A strategy that reduces a risk's probability or impact is:", "Risk",
             "Risk mitigation proactively lowers likelihood and/or impact.",
             [("Risk mitigation", True), ("Risk acceptance", False),
              ("Risk ignorance", False), ("Risk creation", False)]),
            ("Brooks's Law states that:", "Team",
             "From 'The Mythical Man-Month': adding manpower to a late project makes it later.",
             [("Adding manpower to a late project makes it later", True),
              ("More testing finds all bugs", False),
              ("Code doubles every year", False),
              ("Documentation is optional", False)]),
        ],
    },
    {
        "name": "Configuration Management & DevOps",
        "icon": "bi-git", "color": "#4a6378", "difficulty": "ADVANCED",
        "description": "Version control, branching, CI/CD, baselines and DevOps culture.",
        "questions": [
            ("The primary purpose of version control (e.g., Git) is to:", "Version control",
             "A VCS tracks and manages changes to source code, enabling history and collaboration.",
             [("Track and manage changes to source code over time", True),
              ("Compile the code", False), ("Host the website", False), ("Design the UI", False)]),
            ("In Git, a separate line of development is called a:", "Version control",
             "Branches isolate work; merging integrates it back.",
             [("Branch", True), ("Commit", False), ("Clone", False), ("Merge", False)]),
            ("Continuous Integration (CI) primarily means:", "CI/CD",
             "Frequently merging code and running automated builds and tests.",
             [("Frequently merging code with automated builds/tests", True),
              ("Deploying to production by hand hourly", False),
              ("Writing code without tests", False),
              ("Integrating once a year", False)]),
            ("Continuous Delivery means:", "CI/CD",
             "The software is always kept in a deployable, release-ready state.",
             [("Code is always in a deployable state, release is a button press", True),
              ("Code is never released", False),
              ("Designs are delivered to clients", False),
              ("Databases are deleted", False)]),
            ("DevOps mainly aims to:", "DevOps",
             "DevOps bridges Development and Operations with automation and collaboration.",
             [("Bridge development and operations for faster, reliable delivery", True),
              ("Replace all developers", False),
              ("Eliminate testing", False),
              ("Focus only on hardware", False)]),
            ("Software Configuration Management (SCM) includes:", "SCM",
             "SCM covers change control, version control and build/release management.",
             [("Change control, version control and build management", True),
              ("Only writing code", False),
              ("Only UI design", False),
              ("Only marketing", False)]),
            ("A 'baseline' in configuration management is:", "SCM",
             "A formally reviewed, agreed reference point that changes only via formal control.",
             [("A formally reviewed, agreed-upon reference point", True),
              ("A random code snapshot", False),
              ("A type of bug", False),
              ("A server", False)]),
        ],
    },
]

DIFF_TIME = {"BEGINNER": 8, "INTERMEDIATE": 10, "ADVANCED": 12}


class Command(BaseCommand):
    help = "Seed EduHub with Software Engineering quizzes and demo users."

    def add_arguments(self, parser):
        parser.add_argument("--fresh", action="store_true", help="Delete existing quiz data first.")

    def handle(self, *args, **options):
        random.seed(42)
        if options["fresh"]:
            self.stdout.write("Wiping existing data...")
            Attempt.objects.all().delete()
            Topic.objects.all().delete()
            Quiz.objects.all().delete()
            User.objects.exclude(is_superuser=True).delete()

        # --- Users ---------------------------------------------------------
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={"first_name": "Platform", "last_name": "Admin",
                      "email": "admin@eduhub.test", "role": User.Role.ADMIN,
                      "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password("admin123")
            admin.save()

        lecturer, created = User.objects.get_or_create(
            username="lecturer",
            defaults={"first_name": "Dr. Demo", "last_name": "Lecturer",
                      "email": "lecturer@eduhub.test", "role": User.Role.LECTURER},
        )
        if created:
            lecturer.set_password("teach123")
            lecturer.save()

        students = {}
        for uname, first, last in [("alice", "Alice", "Tan"), ("bob", "Bob", "Lim"),
                                    ("carol", "Carol", "Nair"), ("student", "Demo", "Student")]:
            u, created = User.objects.get_or_create(
                username=uname,
                defaults={"first_name": first, "last_name": last,
                          "email": f"{uname}@eduhub.test", "role": User.Role.STUDENT},
            )
            if created:
                u.set_password("learn123")
                u.save()
            students[uname] = u

        # --- Topics, quizzes, questions, choices ---------------------------
        quizzes_in_order = []
        for order, block in enumerate(CONTENT):
            topic, _ = Topic.objects.get_or_create(
                name=block["name"],
                defaults={"description": block["description"], "icon": block["icon"],
                          "color": block["color"], "order": order},
            )
            quiz, q_created = Quiz.objects.get_or_create(
                topic=topic, title=block["name"],
                defaults={"description": block["description"], "difficulty": block["difficulty"],
                          "time_limit_minutes": DIFF_TIME[block["difficulty"]],
                          "author": lecturer, "is_published": True},
            )
            quizzes_in_order.append(quiz)
            if q_created or quiz.questions.count() == 0:
                for q_order, (text, subtopic, explanation, choices) in enumerate(block["questions"], start=1):
                    question = Question.objects.create(
                        quiz=quiz, text=text, subtopic=subtopic,
                        explanation=explanation, order=q_order,
                    )
                    for c_order, (ctext, correct) in enumerate(choices, start=1):
                        Choice.objects.create(
                            question=question, text=ctext, is_correct=correct, order=c_order
                        )

        # --- Demo attempts (for leaderboard + admin charts) ----------------
        specs = [
            ("alice", 0, 0.9, 6), ("alice", 1, 0.8, 5), ("alice", 2, 1.0, 4), ("alice", 6, 0.85, 1),
            ("bob", 0, 0.6, 5), ("bob", 3, 0.5, 3), ("bob", 4, 0.7, 1),
            ("carol", 2, 0.8, 4), ("carol", 5, 0.9, 2), ("carol", 7, 0.6, 0), ("carol", 0, 0.7, 1),
        ]
        made = 0
        for uname, qidx, accuracy, days_ago in specs:
            student = students[uname]
            quiz = quizzes_in_order[qidx]
            if Attempt.objects.filter(student=student, quiz=quiz).exists():
                continue
            completed = timezone.now() - timedelta(days=days_ago, minutes=random.randint(0, 300))
            questions = list(quiz.questions.prefetch_related("choices"))
            attempt = Attempt.objects.create(
                student=student, quiz=quiz, total=len(questions),
                started_at=completed - timedelta(minutes=6), completed_at=completed,
            )
            score = 0
            for q in questions:
                correct_choice = q.choices.filter(is_correct=True).first()
                if random.random() < accuracy:
                    chosen = correct_choice
                else:
                    wrong = list(q.choices.exclude(is_correct=True))
                    chosen = random.choice(wrong) if wrong else correct_choice
                ok = bool(chosen and chosen.is_correct)
                if ok:
                    score += 1
                Answer.objects.create(attempt=attempt, question=q, selected_choice=chosen, is_correct=ok)
            attempt.score = score
            attempt.save()
            made += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Topic.objects.count()} topics, {Quiz.objects.count()} quizzes, "
            f"{Question.objects.count()} questions, {Attempt.objects.count()} attempts ({made} new)."
        ))
        self.stdout.write("")
        self.stdout.write("Login credentials:")
        self.stdout.write("  Admin      -> admin / admin123")
        self.stdout.write("  Lecturer   -> lecturer / teach123")
        self.stdout.write("  Student    -> student / learn123   (also: alice, bob, carol)")
