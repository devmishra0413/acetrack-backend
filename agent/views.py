import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework import serializers, status

from .advisor import get_advice
from .summarizer import extract_text_from_pdf, extract_text_from_txt, summarize_content
from .roadmap import extract_syllabus_from_pdf, generate_roadmap
from .schedule import generate_schedule

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_WORDS_FOR_SUMMARY = 10_000
ALLOWED_EXTENSIONS = (".pdf", ".txt")


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class AdvisorSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=1, max_length=5_000)
    conversation_history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        max_length=50,
    )


class SummarizerSerializer(serializers.Serializer):
    text = serializers.CharField(required=False, allow_blank=True, max_length=50_000)

    def validate(self, attrs):
        # File validation is handled in the view; here we just ensure text isn't missing
        # when no file is provided (cross-field validation happens in the view).
        return attrs


class RoadmapSerializer(serializers.Serializer):
    exam_name = serializers.CharField(min_length=1, max_length=200)
    exam_date = serializers.DateField(input_formats=["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"])
    daily_hours = serializers.IntegerField(min_value=1, max_value=16, default=4)
    syllabus_text = serializers.CharField(required=False, allow_blank=True, max_length=50_000)

    def validate(self, attrs):
        from datetime import date
        if attrs["exam_date"] <= date.today():
            raise serializers.ValidationError({"exam_date": "Exam date must be in the future."})
        return attrs


class ScheduleSerializer(serializers.Serializer):
    activities = serializers.CharField(min_length=1, max_length=5_000)
    goal = serializers.CharField(min_length=1, max_length=1_000)
    wake_time = serializers.CharField(max_length=20, default="6:00 AM")
    sleep_time = serializers.CharField(max_length=20, default="11:00 PM")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_uploaded_file(file):
    """
    Returns (text, error_response) — one of them will be None.
    """
    if file.size > MAX_FILE_SIZE_BYTES:
        return None, Response(
            {"error": "File size must be under 5 MB."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    filename = file.name.lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return None, Response(
            {"error": f"Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if filename.endswith(".pdf"):
        text = extract_text_from_pdf(file)
    else:
        text = extract_text_from_txt(file)

    if not text or not text.strip():
        return None, Response(
            {"error": "No readable text found in the uploaded file."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return text, None


def _truncate_to_words(text: str, max_words: int) -> str:
    words = text.split()
    return " ".join(words[:max_words]) if len(words) > max_words else text


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class AdvisorView(APIView):
    """
    POST /api/advisor/
    Body: { message: str, history?: list[dict] }
    Returns: { reply: str }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AdvisorSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            reply = get_advice(
                user=request.user,
                user_message=data["message"],
                conversation_history=data["conversation_history"],
            )
            return Response({"reply": reply})
        except Exception:
            logger.exception("AdvisorView failed for user=%s", request.user.id)
            return Response(
                {"error": "Something went wrong. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SummarizerView(APIView):
    """
    POST /api/summarizer/
    Body (multipart): file (PDF/TXT) OR text (plain string)
    Returns: { summary: str, word_count: int, truncated: bool }
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        file = request.FILES.get("file")
        serializer = SummarizerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        text_input = serializer.validated_data.get("text", "").strip()

        if not file and not text_input:
            return Response(
                {"error": "Provide either a file (PDF/TXT) or a text field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if file:
                text, err = _validate_uploaded_file(file)
                if err:
                    return err
            else:
                text = text_input

            original_word_count = len(text.split())
            truncated = original_word_count > MAX_WORDS_FOR_SUMMARY
            text = _truncate_to_words(text, MAX_WORDS_FOR_SUMMARY)

            summary = summarize_content(text)
            return Response({
                "summary": summary,
                "word_count": original_word_count,
                "truncated": truncated,
            })
        except Exception:
            logger.exception("SummarizerView failed for user=%s", request.user.id)
            return Response(
                {"error": "Something went wrong. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RoadmapView(APIView):
    """
    POST /api/roadmap/
    Body (multipart): exam_name, exam_date, daily_hours, file (PDF) OR syllabus_text
    Returns: { roadmap: str, exam_name, exam_date, daily_hours }
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = RoadmapSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        file = request.FILES.get("file")

        if not file and not data.get("syllabus_text"):
            return Response(
                {"error": "Provide either a syllabus PDF or syllabus_text."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if file:
                syllabus, err = _validate_uploaded_file(file)
                if err:
                    return err
            else:
                syllabus = data["syllabus_text"]

            roadmap = generate_roadmap(
                syllabus_text=syllabus,
                exam_name=data["exam_name"],
                exam_date=str(data["exam_date"]),
                daily_hours=data["daily_hours"],
            )
            return Response({
                "roadmap": roadmap,
                "exam_name": data["exam_name"],
                "exam_date": str(data["exam_date"]),
                "daily_hours": data["daily_hours"],
            })
        except Exception:
            logger.exception("RoadmapView failed for user=%s", request.user.id)
            return Response(
                {"error": "Something went wrong. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ScheduleView(APIView):
    """
    POST /api/schedule/
    Body: { activities, goal, wake_time?, sleep_time? }
    Returns: { schedule: str }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ScheduleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            schedule = generate_schedule(
                activities=data["activities"],
                goal=data["goal"],
                wake_time=data["wake_time"],
                sleep_time=data["sleep_time"],
            )
            return Response({"schedule": schedule})
        except Exception:
            logger.exception("ScheduleView failed for user=%s", request.user.id)
            return Response(
                {"error": "Something went wrong. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )