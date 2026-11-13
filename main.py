"""A Drafter app for planning workouts and keeping a daily log."""

from dataclasses import dataclass
from math import isfinite
from sys import platform, stdout
import unittest

from drafter import (
    Button,
    Div,
    Header,
    Label,
    Link,
    Page,
    Paragraph,
    SelectBox,
    Table,
    TextBox,
    route,
    set_site_information,
    start_server,
)
from drafter.config.site_information import SiteInformation


SITE_TITLE = "Workout Goal Planner"
DESIGN_WORKSHEET = "Final_Project_Design_Phase.docx"
# Fixed conversion for the classroom estimate. The About page lists the source.
CALORIES_PER_POUND = 3500
MAX_WEEKS = 52
DAYS_PER_WEEK = 7

# CSS changes the layout and appearance. All pages and actions use Drafter.
SITE_CSS = """
body {
    margin: 0;
    background: #f1f5f3;
    color: #172c26;
    font-family: "Inter", system-ui, sans-serif;
}
.planner-shell {
    max-width: 760px;
    margin: 0 auto;
    padding: 28px 20px 40px;
}
.planner-brand {
    display: block;
    margin-bottom: 18px;
    color: #165947;
    font-size: 1rem;
    font-weight: 700;
    text-decoration: none;
}
.planner-panel {
    padding: clamp(20px, 5vw, 40px);
    background: #fff;
    border: 1px solid #d9e4de;
    border-radius: 16px;
}
.planner-panel h1 { margin: 0 0 12px; line-height: 1.15; }
.planner-panel p { line-height: 1.5; }
.planner-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 210px), 1fr));
    gap: 16px;
    margin: 20px 0;
}
.planner-field label { display: block; margin-bottom: 6px; font-weight: 600; }
.planner-field input, .planner-field select {
    box-sizing: border-box;
    width: 100%;
    min-height: 44px;
    padding: 8px 10px;
    border: 1px solid #839b8f;
    border-radius: 6px;
    background: #fff;
    color: inherit;
    font: inherit;
}
.planner-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px 16px;
    margin-top: 22px;
}
.planner-actions button, .planner-actions input[type="submit"] {
    min-height: 44px;
    padding: 9px 16px;
    border: 1px solid #165947;
    border-radius: 7px;
    background: #165947;
    color: #fff;
    font: inherit;
    font-weight: 600;
    cursor: pointer;
}
.planner-actions button:hover, .planner-actions input[type="submit"]:hover {
    background: #0c4334;
}
.planner-actions a { color: #165947; font-weight: 600; }
.planner-panel :focus-visible, .planner-brand:focus-visible {
    outline: 3px solid #177e66;
    outline-offset: 3px;
}
.planner-estimate {
    margin: 20px 0;
    padding: 16px 20px;
    border-radius: 9px;
    background: #e7f3ed;
}
.planner-estimate p { margin: 0; }
.planner-estimate h2 { margin: 2px 0 0; font-size: clamp(26px, 6vw, 44px); }
.planner-note { color: #425b51; font-size: .94rem; }
.planner-error { color: #8f2920; font-weight: 600; }
.planner-status { color: #165947; font-weight: 600; }
.planner-table { overflow-x: auto; }
.planner-table table { width: 100%; border-collapse: collapse; }
.planner-table th, .planner-table td {
    padding: 10px;
    border-bottom: 1px solid #d9e4de;
    text-align: left;
    vertical-align: top;
}
.planner-table th { background: #e7f3ed; color: #172c26; }
@media (max-width: 540px) {
    .planner-panel h1 { font-size: 2rem; }
    .planner-table table { table-layout: fixed; margin: 0; font-size: .875rem; }
    .planner-table th, .planner-table td { padding: 6px 4px; overflow-wrap: anywhere; }
    .planner-table th:nth-child(1) { width: 13%; }
    .planner-table th:nth-child(2) { width: 24%; }
    .planner-table th:nth-child(3) { width: 39%; }
    .planner-table th:nth-child(4) { width: 24%; }
}
"""


@dataclass
class DailyLog:
    """Store one day's food calories, workout calories, and weight."""

    day_number: int
    calories_eaten: int
    workout_calories: list[int]
    current_weight: float


@dataclass
class State:
    """Keep the current workout plan and the log across pages."""

    start_weight: float
    goal_weight: float
    weeks: int
    workouts_per_week: int
    calories_per_workout: int
    daily_logs: list[DailyLog]


def initial_state() -> State:
    """Make a fresh state with no plan and an empty log."""
    return State(0.0, 0.0, 0, 0, 0, [])


def make_page(state: State, title: str, content: list) -> Page:
    """Put the page title and its Drafter components inside the site layout."""
    brand = Link(SITE_TITLE, "index", classes="planner-brand")
    panel = Div(Header(title), content, classes="planner-panel")
    return Page(state, [Div(brand, panel, classes="planner-shell")])


def form_field(label: str, control: TextBox | SelectBox) -> Div:
    """Associate a visible label with its text box or dropdown."""
    # Drafter uses the field name as a default ARIA label. Use the visible
    # wording and set a matching ID so assistive technology reads the label.
    control.extra_settings["id"] = control.name
    control.extra_settings["aria-label"] = label
    return Div(Label(label, control), control, classes="planner-field")


def show_goal_form(
    state: State,
    start_weight: str,
    goal_weight: str,
    weeks: str,
    workouts_per_week: str,
    error: str = "",
) -> Page:
    """Build the goal form with its current inputs and any validation error."""
    week_options = []
    for number in range(1, MAX_WEEKS + 1):
        week_options.append(str(number))
    workout_options = []
    for number in range(1, DAYS_PER_WEEK + 1):
        workout_options.append(str(number))

    if weeks not in week_options:
        weeks = "8"
    if workouts_per_week not in workout_options:
        workouts_per_week = "3"

    content = [Paragraph("Enter your starting and goal weights and choose your workout schedule.")]
    if error:
        content.append(Paragraph(error, classes="planner-error", role="alert"))
    content.append(Div(
        form_field("Starting weight (lb)", TextBox("start_weight", start_weight)),
        form_field("Goal weight (lb)", TextBox("goal_weight", goal_weight)),
        form_field("Weeks", SelectBox("weeks", week_options, weeks)),
        form_field(
            "Workouts per week",
            SelectBox("workouts_per_week", workout_options, workouts_per_week),
        ),
        classes="planner-grid",
    ))
    content.append(Div(
        Button("Calculate Plan", "calculate_plan"), Link("Home", "index"),
        classes="planner-actions",
    ))
    return make_page(state, "Set a Goal", content)


def show_log_form(
    state: State,
    day_number: str,
    calories_eaten: str = "",
    workout_calories: str = "",
    current_weight: str = "",
    error: str = "",
) -> Page:
    """Build the daily log form with its current inputs and any validation error."""
    content = [Paragraph("Use the same day number to update a saved entry.")]
    if error:
        content.append(Paragraph(error, classes="planner-error", role="alert"))
    content.append(Div(
        form_field("Day number", TextBox("day_number", day_number)),
        form_field("Calories eaten", TextBox("calories_eaten", calories_eaten)),
        form_field("Calories burned in each workout", TextBox("workout_calories", workout_calories)),
        form_field("Current weight (lb)", TextBox("current_weight", current_weight)),
        classes="planner-grid",
    ))
    content.append(Paragraph(
        "Separate multiple workouts with commas, such as 240, 160. Leave the box blank on a rest day.",
        classes="planner-note",
    ))
    content.append(Div(
        Button("Save Day", "save_day"), Link("Back to Plan", "plan"),
        classes="planner-actions",
    ))
    return make_page(state, "Log a Day", content)


def read_goal_inputs(
    start_weight: str, goal_weight: str, weeks: str, workouts_per_week: str,
) -> tuple[float, float, int, int]:
    """Convert the form inputs to numbers or raise ValueError with an error message."""
    # Converting invalid text raises ValueError. The submit route catches the
    # exception and shows the message without changing the saved plan.
    try:
        starting = float(start_weight)
        goal = float(goal_weight)
        duration = int(weeks)
        frequency = int(workouts_per_week)
    except ValueError:
        raise ValueError("Enter numeric weights and choose a workout schedule.") from None

    if not isfinite(starting) or not isfinite(goal) or starting <= 0 or goal <= 0:
        raise ValueError("Both weights must be positive numbers.")
    if goal >= starting:
        raise ValueError("Enter a goal weight below your starting weight.")
    if not 1 <= duration <= MAX_WEEKS:
        raise ValueError(f"Choose a plan from 1 to {MAX_WEEKS} weeks.")
    if not 1 <= frequency <= DAYS_PER_WEEK:
        raise ValueError(f"Choose from 1 to {DAYS_PER_WEEK} workouts per week.")
    return starting, goal, duration, frequency


def read_workout_calories(workout_calories: str) -> list[int]:
    """Read positive calorie counts separated by commas, or an empty rest-day list."""
    if workout_calories.strip() == "":
        return []

    counts = []
    for part in workout_calories.split(","):
        try:
            calories = int(part)
        except ValueError:
            raise ValueError("Use whole numbers separated by commas for workout calories.") from None
        if calories <= 0:
            raise ValueError("Each workout calorie count must be a positive whole number.")
        counts.append(calories)
    return counts


def read_log_inputs(
    day_number: str, calories_eaten: str, workout_calories: str, current_weight: str,
) -> DailyLog:
    """Validate the daily form and return a record ready to save."""
    try:
        day = int(day_number)
        food = int(calories_eaten)
        weight = float(current_weight)
    except ValueError:
        raise ValueError("Enter a whole day number, whole food calories, and a numeric weight.") from None

    if day <= 0:
        raise ValueError("The day number must be at least 1.")
    if food < 0:
        raise ValueError("Calories eaten must be zero or more.")
    if not isfinite(weight) or weight <= 0:
        raise ValueError("Current weight must be a positive number.")
    return DailyLog(day, food, read_workout_calories(workout_calories), weight)


def store_day(daily_logs: list[DailyLog], entry: DailyLog) -> None:
    """Save the entry in day order, replacing a record with the same day number."""
    for position, existing in enumerate(daily_logs):
        if existing.day_number == entry.day_number:
            daily_logs[position] = entry
            return
        if existing.day_number > entry.day_number:
            daily_logs.insert(position, entry)
            return
    daily_logs.append(entry)


def describe_workouts(calories: list[int]) -> str:
    """Show workout calorie counts and their daily total, or mark a rest day."""
    if not calories:
        return "Rest day"
    if len(calories) == 1:
        return f"{calories[0]:,}"

    counts = []
    for count in calories:
        counts.append(f"{count:,}")
    return f"{sum(calories):,} total ({', '.join(counts)})"


@route
def index(state: State) -> Page:
    """Introduce the app and give the user a way to start or reopen a plan."""
    actions = [Button("Set a Goal", "goal_form")]
    if state.weeks > 0:
        actions.append(Link("View Plan", "plan"))
    return make_page(state, "Plan your workouts", [
        Paragraph("Estimate calories per workout from your weight goal and schedule."),
        Paragraph("Log food calories, workouts, and weigh-ins as you go."),
        Div(actions, classes="planner-actions"),
    ])


@route
def goal_form(state: State) -> Page:
    """Show the goal form, filling in any values saved in the current plan."""
    if state.weeks == 0:
        return show_goal_form(state, "", "", "8", "3")
    return show_goal_form(
        state, str(state.start_weight), str(state.goal_weight),
        str(state.weeks), str(state.workouts_per_week),
    )


@route
def calculate_plan(
    state: State, start_weight: str, goal_weight: str, weeks: str, workouts_per_week: str,
) -> Page:
    """Save a valid workout plan or redisplay the goal form with an error."""
    try:
        starting, goal, duration, frequency = read_goal_inputs(
            start_weight, goal_weight, weeks, workouts_per_week,
        )
        workout_count = duration * frequency
        estimated_calories = (starting - goal) / workout_count * CALORIES_PER_POUND
        if not isfinite(estimated_calories):
            raise ValueError("Enter a smaller difference between your weights.")
    except ValueError as error:
        return show_goal_form(state, start_weight, goal_weight, weeks, workouts_per_week, str(error))

    state.start_weight = starting
    state.goal_weight = goal
    state.weeks = duration
    state.workouts_per_week = frequency
    state.calories_per_workout = round(estimated_calories)
    return plan(state)


@route
def plan(state: State) -> Page:
    """Show the saved plan and navigation to the daily log and progress pages."""
    if state.weeks == 0:
        return goal_form(state)

    workout_count = state.weeks * state.workouts_per_week
    return make_page(state, "Your Workout Plan", [
        Paragraph(f"Starting weight {state.start_weight:g} lb. Goal weight {state.goal_weight:g} lb."),
        Paragraph(f"{state.weeks} weeks at {state.workouts_per_week} workouts per week."),
        Paragraph(f"{workout_count} planned workouts."),
        Div(
            Paragraph("Estimated calories per workout"),
            Header(f"{state.calories_per_workout:,}", level=2),
            classes="planner-estimate",
        ),
        Paragraph(
            "This rough estimate spreads the full estimated calorie deficit across your planned workouts.",
            classes="planner-note",
        ),
        Div(
            Button("Log a Day", "log_day"), Button("View Progress", "progress"),
            Link("Edit Goal", "goal_form"),
            classes="planner-actions",
        ),
    ])


@route
def log_day(state: State) -> Page:
    """Open a new log form with the next day number filled in."""
    if state.weeks == 0:
        return goal_form(state)
    next_day = 1
    if state.daily_logs:
        next_day = state.daily_logs[-1].day_number + 1
    return show_log_form(state, str(next_day))


@route
def save_day(
    state: State, day_number: str, calories_eaten: str, workout_calories: str, current_weight: str,
) -> Page:
    """Save a valid day and show progress, or return the form with an error."""
    if state.weeks == 0:
        return goal_form(state)
    try:
        entry = read_log_inputs(day_number, calories_eaten, workout_calories, current_weight)
    except ValueError as error:
        return show_log_form(state, day_number, calories_eaten, workout_calories, current_weight, str(error))

    store_day(state.daily_logs, entry)
    return progress(state, f"Day {entry.day_number} saved.")


@route
def progress(state: State, message: str = "") -> Page:
    """Show the latest weigh-in and a table built from the saved daily records."""
    if state.weeks == 0:
        return goal_form(state)

    content = []
    if message:
        content.append(Paragraph(message, classes="planner-status", role="status"))
    content.append(Paragraph(f"Goal weight {state.goal_weight:g} lb."))
    if not state.daily_logs:
        content.append(Paragraph("No days logged yet. Log a day to get started."))
    else:
        latest = state.daily_logs[-1]
        content.append(Paragraph(f"Latest weigh-in {latest.current_weight:g} lb on day {latest.day_number}."))

        rows = []
        for entry in state.daily_logs:
            rows.append([
                entry.day_number,
                f"{entry.calories_eaten:,}",
                describe_workouts(entry.workout_calories),
                f"{entry.current_weight:g} lb",
            ])
        table = Table(rows, ["Day", "Food calories", "Workout calories", "Weight"])
        content.append(Div(table, classes="planner-table"))

    content.append(Div(
        Button("Log a Day", "log_day"), Link("Back to Plan", "plan"),
        classes="planner-actions",
    ))
    content.append(Paragraph("Your plan and log reset when you reload this tab.", classes="planner-note"))
    return make_page(state, "Progress", content)


def run_site() -> None:
    """Set the About page information and start the Drafter app."""
    information = SiteInformation(
        author="Jacob",
        description="A class project for planning workouts and recording daily food, workouts, and weight.",
        sources=[
            "Drafter documentation",
            "Kevin Hall, What Is the Required Energy Deficit per Unit Weight Loss?",
            "ChatGPT assisted with the design, implementation, and testing.",
        ],
        planning=[DESIGN_WORKSHEET],
        links=[
            "https://drafter-edu.github.io/drafter/",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC2376744/",
        ],
    )
    # Drafter 2.2.1 reports an error when the browser replays the individual
    # metadata updates from set_site_information. Pyodide identifies itself as
    # emscripten, so pass the same information at startup in that environment.
    if platform != "emscripten":
        set_site_information(
            author=information.author,
            description=information.description,
            sources=information.sources,
            planning=information.planning,
            links=information.links,
        )
    start_server(
        initial_state(),
        information=information,
        site_title=SITE_TITLE,
        in_debug_mode=False,
        framed=False,
        additional_style_content=[SITE_CSS],
        additional_files=[DESIGN_WORKSHEET],
    )


# Unit tests for the seven Drafter routes.
def page_elements(content: list) -> list[object]:
    """Collect the components inside the layout so tests can inspect them."""
    # Recursion visits a Div or list inside another Div until it finds
    # individual headings, buttons, or other components.
    elements = []
    for element in content:
        if isinstance(element, Div):
            elements.extend(page_elements(element.content))
        elif isinstance(element, list):
            elements.extend(page_elements(element))
        else:
            elements.append(element)
    return elements


def title_of(page: Page) -> str:
    """Get the first heading from a rendered page's component list."""
    for element in page_elements(page.content):
        if isinstance(element, Header):
            return str(element.body)
    raise AssertionError("The page has no heading.")


def sample_plan() -> State:
    """Make a plan fixture with a known estimate of 700 calories per workout."""
    return State(180.0, 172.0, 10, 4, 700, [])


class RouteTests(unittest.TestCase):
    """Check each route's result and the state changes caused by submissions."""

    def test_index(self) -> None:
        """Home offers a route to the goal form."""
        state = initial_state()
        page = index(state)
        self.assertEqual(title_of(page), "Plan your workouts")
        self.assertIn(Button("Set a Goal", "goal_form"), page_elements(page.content))
        self.assertIs(page.state, state)

    def test_goal_form(self) -> None:
        """The goal form shows both weights and both scheduling controls."""
        elements = page_elements(goal_form(initial_state()).content)
        weight_fields = [item.name for item in elements if isinstance(item, TextBox)]
        schedule_fields = [item.name for item in elements if isinstance(item, SelectBox)]
        self.assertEqual(weight_fields, ["start_weight", "goal_weight"])
        self.assertEqual(schedule_fields, ["weeks", "workouts_per_week"])
        self.assertIn(Button("Calculate Plan", "calculate_plan"), elements)

    def test_goal_form_prefills_saved_plan(self) -> None:
        """Editing a saved plan uses its current weights and schedule."""
        elements = page_elements(goal_form(sample_plan()).content)
        weights = [item.default_value for item in elements if isinstance(item, TextBox)]
        self.assertEqual(weights, ["180.0", "172.0"])
        selected = [item.default_value for item in elements if isinstance(item, SelectBox)]
        self.assertEqual(selected, ["10", "4"])

    def test_calculate_plan(self) -> None:
        """A valid goal changes all five plan fields and opens Plan."""
        state = initial_state()
        page = calculate_plan(state, "180", "172", "10", "4")
        self.assertEqual(page.state, sample_plan())
        self.assertEqual(title_of(page), "Your Workout Plan")
        self.assertIn(Header("700", level=2), page_elements(page.content))

    def test_calculate_plan_rejects_invalid_inputs(self) -> None:
        """Invalid goals return the form without changing a saved plan."""
        invalid_inputs = [
            ("abc", "172", "10", "4"),
            ("nan", "172", "10", "4"),
            ("180", "180", "10", "4"),
            ("180", "182", "10", "4"),
            ("180", "172", "0", "4"),
            ("180", "172", "53", "4"),
            ("180", "172", "10", "8"),
        ]
        for starting, goal, weeks, frequency in invalid_inputs:
            # subTest reports the specific input that failed while checking the rest.
            with self.subTest(starting=starting, goal=goal, weeks=weeks, frequency=frequency):
                state = sample_plan()
                page = calculate_plan(state, starting, goal, weeks, frequency)
                self.assertEqual(title_of(page), "Set a Goal")
                self.assertEqual(page.state, sample_plan())

    def test_editing_plan_preserves_daily_logs(self) -> None:
        """Calculating a new plan keeps the daily log intact."""
        state = sample_plan()
        entry = DailyLog(1, 1900, [240], 179.5)
        state.daily_logs.append(entry)
        page = calculate_plan(state, "179.5", "175", "6", "3")
        self.assertEqual(page.state.daily_logs, [entry])
        self.assertEqual(page.state.calories_per_workout, 875)

    def test_plan(self) -> None:
        """Plan displays the total workout count and links to both tracking pages."""
        page = plan(sample_plan())
        elements = page_elements(page.content)
        self.assertEqual(title_of(page), "Your Workout Plan")
        self.assertIn(Paragraph("40 planned workouts."), elements)
        self.assertIn(Button("Log a Day", "log_day"), elements)
        self.assertIn(Button("View Progress", "progress"), elements)

    def test_plan_without_goal(self) -> None:
        """Opening Plan before creating a goal shows the setup form."""
        self.assertEqual(title_of(plan(initial_state())), "Set a Goal")

    def test_log_day(self) -> None:
        """Log Day proposes the next day number and offers a save button."""
        state = sample_plan()
        state.daily_logs.append(DailyLog(4, 1800, [], 177.0))
        page = log_day(state)
        self.assertEqual(title_of(page), "Log a Day")
        elements = page_elements(page.content)
        values = {item.name: item.default_value for item in elements if isinstance(item, TextBox)}
        self.assertEqual(values["day_number"], "5")
        self.assertIn(Button("Save Day", "save_day"), elements)

    def test_save_day(self) -> None:
        """Saving a workout day records both workouts and opens Progress."""
        state = sample_plan()
        page = save_day(state, "1", "1900", "240, 160", "179.5")
        self.assertEqual(page.state.daily_logs, [DailyLog(1, 1900, [240, 160], 179.5)])
        self.assertEqual(title_of(page), "Progress")

    def test_save_day_replaces_and_orders_records(self) -> None:
        """An earlier day is inserted in order and a repeated day is replaced."""
        state = sample_plan()
        save_day(state, "3", "2000", "300", "179")
        save_day(state, "1", "0", "", "180")
        self.assertEqual(state.daily_logs, [
            DailyLog(1, 0, [], 180.0),
            DailyLog(3, 2000, [300], 179.0),
        ])
        save_day(state, "3", "1950", " ", "178.5")
        self.assertEqual(state.daily_logs, [
            DailyLog(1, 0, [], 180.0),
            DailyLog(3, 1950, [], 178.5),
        ])

    def test_save_day_rejects_invalid_inputs(self) -> None:
        """Bad log input reopens the form without altering existing records."""
        invalid_inputs = [
            ("0", "1900", "240", "179"),
            ("1", "-1", "240", "179"),
            ("1", "1900", "240,", "179"),
            ("1", "1900", "240, -1", "179"),
            ("1", "1900", "0", "179"),
            ("1", "1900", "240", "inf"),
        ]
        for day, food, workouts, weight in invalid_inputs:
            with self.subTest(day=day, food=food, workouts=workouts, weight=weight):
                state = sample_plan()
                entry = DailyLog(1, 1800, [200], 180.0)
                state.daily_logs.append(entry)
                page = save_day(state, day, food, workouts, weight)
                self.assertEqual(title_of(page), "Log a Day")
                self.assertEqual(page.state.daily_logs, [entry])

    def test_progress_empty(self) -> None:
        """Progress prompts the user to log a day when there are no records."""
        page = progress(sample_plan())
        elements = page_elements(page.content)
        self.assertIn(Paragraph("No days logged yet. Log a day to get started."), elements)
        self.assertFalse(any(isinstance(item, Table) for item in elements))

    def test_progress_lists_days_and_latest_weight(self) -> None:
        """Progress renders one row per day, including the workout total and rest days."""
        state = sample_plan()
        state.daily_logs.extend([
            DailyLog(1, 1950, [240, 160], 179.5),
            DailyLog(3, 2000, [], 178.5),
        ])
        elements = page_elements(progress(state).content)
        self.assertIn(Paragraph("Latest weigh-in 178.5 lb on day 3."), elements)
        tables = [item for item in elements if isinstance(item, Table)]
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0].rows, [
            [1, "1,950", "400 total (240, 160)", "179.5 lb"],
            [3, "2,000", "Rest day", "178.5 lb"],
        ])



def run_tests() -> bool:
    """Run the route tests and report whether the app is ready to launch."""
    # Running a TestSuite directly gives us the result without exiting Python.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RouteTests)
    result = unittest.TextTestRunner(stream=stdout, verbosity=2).run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    # The browser uses the compiled app. Thonny and the build run tests first.
    if platform != "emscripten" and not run_tests():
        raise SystemExit(1)
    run_site()
