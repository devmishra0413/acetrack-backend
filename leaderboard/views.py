from django.utils import timezone
from django.db.models import Sum, Count, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from tasks.models import Task
from focus.models import FocusSession


def get_week_bounds():
    """Return (week_start, week_end) for the current Monday–today window."""
    today = timezone.localdate()
    week_start = today - timezone.timedelta(days=today.weekday())  # Monday
    week_end = today
    return week_start, week_end


def compute_achievements(user, week_start, week_end):
    """
    Compute achievement count for a user using the same logic as the users app.
    Achievements: streak_7, tasks_50, focus_10h, night_owl, early_bird.
    All achievements are evaluated all-time (not scoped to the week).
    """
    count = 0

    # --- streak_7: completed tasks on 7 consecutive days ---
    completed_dates = (
        Task.objects.filter(user=user, is_completed=True)
        .dates("date", "day")
    )
    completed_date_set = set(completed_dates)
    max_streak = 0
    streak = 0
    if completed_date_set:
        sorted_dates = sorted(completed_date_set)
        streak = 1
        max_streak = 1
        for i in range(1, len(sorted_dates)):
            delta = (sorted_dates[i] - sorted_dates[i - 1]).days
            if delta == 1:
                streak += 1
                max_streak = max(max_streak, streak)
            elif delta > 1:
                streak = 1
    if max_streak >= 7:
        count += 1

    # --- tasks_50: completed at least 50 tasks all-time ---
    total_completed = Task.objects.filter(user=user, is_completed=True).count()
    if total_completed >= 50:
        count += 1

    # --- focus_10h: at least 10 hours of focus time all-time ---
    total_focus = (
        FocusSession.objects.filter(user=user)
        .aggregate(total=Sum("duration_minutes"))["total"]
        or 0
    )
    if total_focus >= 600:  # 10 hours = 600 minutes
        count += 1

    # --- night_owl: any focus session that started at or after 22:00 ---
    night_owl = FocusSession.objects.filter(
        user=user,
        started_at__hour__gte=22,
    ).exists()
    if night_owl:
        count += 1

    # --- early_bird: any focus session that started before 07:00 ---
    early_bird = FocusSession.objects.filter(
        user=user,
        started_at__hour__lt=7,
    ).exists()
    if early_bird:
        count += 1

    return count


class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        week_start, week_end = get_week_bounds()

        # ------------------------------------------------------------------ #
        # 1. Aggregate per-user weekly stats in bulk                          #
        # ------------------------------------------------------------------ #

        # Focus time this week (in minutes)
        focus_qs = (
            FocusSession.objects.filter(
                started_at__date__gte=week_start,
                started_at__date__lte=week_end,
            )
            .values("user")
            .annotate(total_focus=Sum("duration_minutes"))
        )
        focus_map = {row["user"]: row["total_focus"] or 0 for row in focus_qs}

        # Tasks this week
        task_qs = (
            Task.objects.filter(
                date__gte=week_start,
                date__lte=week_end,
            )
            .values("user")
            .annotate(
                completed=Count("id", filter=Q(is_completed=True)),
                total=Count("id"),
            )
        )
        task_map = {
            row["user"]: {"completed": row["completed"], "total": row["total"]}
            for row in task_qs
        }

        # ------------------------------------------------------------------ #
        # 2. Build raw stats for every active user                            #
        # ------------------------------------------------------------------ #
        users = User.objects.filter(is_active=True)

        raw = []
        for user in users:
            focus_minutes = focus_map.get(user.pk, 0)
            task_data = task_map.get(user.pk, {"completed": 0, "total": 0})
            completed = task_data["completed"]
            total = task_data["total"]
            productivity = (completed / total * 100) if total > 0 else 0.0

            raw.append(
                {
                    "user": user,
                    "focus_minutes": focus_minutes,
                    "tasks_completed": completed,
                    "productivity_score": productivity,
                }
            )

        # ------------------------------------------------------------------ #
        # 3. Normalise each dimension to [0, 100]                             #
        # ------------------------------------------------------------------ #
        max_focus = max((r["focus_minutes"] for r in raw), default=1) or 1
        max_tasks = max((r["tasks_completed"] for r in raw), default=1) or 1
        # productivity_score is already 0–100

        scored = []
        for r in raw:
            focus_score = (r["focus_minutes"] / max_focus) * 100
            task_score = (r["tasks_completed"] / max_tasks) * 100
            prod_score = r["productivity_score"]

            score = round(
                (focus_score * 0.5) + (task_score * 0.3) + (prod_score * 0.2), 2
            )

            achievements = compute_achievements(r["user"], week_start, week_end)

            scored.append(
                {
                    "user": r["user"],
                    "score": score,
                    "focus_time_seconds": r["focus_minutes"] * 60,
                    "focus_minutes": r["focus_minutes"],  # used for tie-breaking
                    "tasks_completed": r["tasks_completed"],
                    "productivity_score": round(r["productivity_score"], 2),
                    "achievements_count": achievements,
                }
            )

        # ------------------------------------------------------------------ #
        # 4. Sort: score DESC → focus_minutes DESC → achievements_count DESC  #
        # ------------------------------------------------------------------ #
        scored.sort(
            key=lambda x: (
                -x["score"],
                -x["focus_minutes"],
                -x["achievements_count"],
            )
        )

        # ------------------------------------------------------------------ #
        # 5. Assign ranks (shared rank on equal sort key)                     #
        # ------------------------------------------------------------------ #
        result = []
        rank = 0
        prev_key = None
        for i, entry in enumerate(scored):
            sort_key = (
                entry["score"],
                entry["focus_minutes"],
                entry["achievements_count"],
            )
            if sort_key != prev_key:
                rank = i + 1
                prev_key = sort_key

            result.append(
                {
                    "rank": rank,
                    "username": entry["user"].username,
                    "score": entry["score"],
                    "focus_time_seconds": entry["focus_time_seconds"],
                    "tasks_completed": entry["tasks_completed"],
                    "productivity_score": entry["productivity_score"],
                    "achievements_count": entry["achievements_count"],
                }
            )

        return Response(result)