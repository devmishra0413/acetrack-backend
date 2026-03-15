from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .advisor import get_advice
from .summarizer import extract_text_from_pdf, extract_text_from_txt, summarize_content
from .roadmap import extract_syllabus_from_pdf, generate_roadmap
from .schedule import generate_schedule
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

@method_decorator(ratelimit(key='user', rate='5/d', method='POST', block=True), name='dispatch')
class AdvisorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get('message', '').strip()
        conversation_history = request.data.get('history', [])
        if not user_message:
            return Response(
                {'error': 'Message cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            reply = get_advice(
                user=request.user,
                user_message=user_message,
                conversation_history=conversation_history
            )
            return Response({'reply': reply})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(ratelimit(key='user', rate='6/d', method='POST', block=True), name='dispatch')
class SummarizerView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        file = request.FILES.get('file')
        text_input = request.data.get('text', '').strip()
        if not file and not text_input:
            return Response(
                {'error': 'File ya text dono mein se kuch toh do!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            if file:
                filename = file.name.lower()
                if filename.endswith('.pdf'):
                    text = extract_text_from_pdf(file)
                elif filename.endswith('.txt'):
                    text = extract_text_from_txt(file)
                else:
                    return Response(
                        {'error': 'Sirf PDF ya TXT file allowed hai!'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                text = text_input
            if not text:
                return Response(
                    {'error': 'File mein koi text nahi mila!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            summary = summarize_content(text)
            return Response({
                'summary': summary,
                'word_count': len(text.split()),
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(ratelimit(key='user', rate='3/d', method='POST', block=True), name='dispatch')
class RoadmapView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    def post(self, request):
        file = request.FILES.get('file')
        syllabus_text = request.data.get('syllabus_text', '').strip()
        exam_name = request.data.get('exam_name', '').strip()
        exam_date = request.data.get('exam_date', '').strip()
        daily_hours = request.data.get('daily_hours', '4').strip()
        if not exam_name:
            return Response(
                {'error': 'Exam ka naam toh batao!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not exam_date:
            return Response(
                {'error': 'Exam date batao!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not file and not syllabus_text:
            return Response(
                {'error': 'Syllabus PDF ya text dono mein se kuch do!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            if file:
                syllabus = extract_syllabus_from_pdf(file)
            else:
                syllabus = syllabus_text
            if not syllabus:
                return Response(
                    {'error': 'Syllabus mein koi content nahi mila!'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            roadmap = generate_roadmap(
                syllabus_text=syllabus,
                exam_name=exam_name,
                exam_date=exam_date,
                daily_hours=daily_hours,
            )
            return Response({
                'roadmap': roadmap,
                'exam_name': exam_name,
                'exam_date': exam_date,
                'daily_hours': daily_hours,
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(ratelimit(key='user', rate='3/d', method='POST', block=True), name='dispatch')
class ScheduleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        activities = request.data.get('activities', '').strip()
        goal = request.data.get('goal', '').strip()
        wake_time = request.data.get('wake_time', '6:00 AM').strip()
        sleep_time = request.data.get('sleep_time', '11:00 PM').strip()

        if not activities:
            return Response(
                {'error': 'Apni daily activities toh batao!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not goal:
            return Response(
                {'error': 'Apna goal batao!'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            schedule = generate_schedule(
                activities=activities,
                goal=goal,
                wake_time=wake_time,
                sleep_time=sleep_time,
            )
            return Response({'schedule': schedule})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )