from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from dashboard.models import ExecMember, ExecRole
from .serializers import ExecMemberSerializer

import pandas as pd

class ExecMemberView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ExecMemberSerializer
    queryset = ExecMember.objects.all()
    
    def get(self, request):
        roleId = request.query_params.get('roleId')
        role = ExecRole.objects.get(id=roleId)
        members = pd.DataFrame(role.ExecMember.values())

        members =  members.to_dict(orient='records')
        
        return Response(members, status=status.HTTP_200_OK)
    def post(self, request):
        serializer = ExecMemberSerializer(data=request.data)
        if serializer.is_valid():
            member = serializer.save()
            return Response({
                'message': 'Member created successfully',
                'member': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'error': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request):
        member_id = request.data.get('id')
        if not member_id:
            return Response({
                'error': 'Member ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        print(member_id)
        try:
            member = ExecMember.objects.get(id=member_id)
            serializer = ExecMemberSerializer(member, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Member updated successfully',
                    'member': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response({
                'error': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except ExecMember.DoesNotExist:
            return Response({
                'error': 'Member not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    def delete(self, request):
        member_id = request.data.get('id')
        if not member_id:
            return Response({
                'error': 'Member ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            member = ExecMember.objects.get(id=member_id)
            member.delete()
            return Response({
                'message': 'Member deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except ExecMember.DoesNotExist:
            return Response({
                'error': 'Member not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)