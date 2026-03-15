from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Expense
from .serializers import ExpenseSerializer

class ExpenseListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    # GET — aaj ke saare expenses lao
    def get(self, request):
        date = request.query_params.get('date', timezone.localdate())
        expenses = Expense.objects.filter(user=request.user, date=date)
        serializer = ExpenseSerializer(expenses, many=True)
        return Response(serializer.data)

    # POST — naya expense add karo
    def post(self, request):
        serializer = ExpenseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExpenseDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    # DELETE — expense delete karo
    def delete(self, request, pk):
        try:
            expense = Expense.objects.get(pk=pk, user=request.user)
        except Expense.DoesNotExist:
            return Response({'error': 'Expense not found'}, status=status.HTTP_404_NOT_FOUND)

        expense.delete()
        return Response({'message': 'Expense deleted'}, status=status.HTTP_204_NO_CONTENT)