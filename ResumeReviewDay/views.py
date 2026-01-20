from rest_framework.views import APIView 
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny

from .models import Employer, Student, Timeslot

from datetime import datetime, timedelta
import pandas as pd

class EmployerViewSet(APIView):
    permission_classes = [AllowAny]
    '''
        Adds an employer to the list of employers
    '''
    def post(self, request):
        try:
            full_name = request.data.get("full_name")
            company_name = request.data.get("company_name")
            email = request.data.get("email")
            phone_number = request.data.get("phone_number")
            diet_restriction = request.data.get("diet_restriction", "")
            start_time = request.data.get("start_time")  # Expecting 'HH:MM' string
            end_time = request.data.get("end_time")
            max_resumes = int(request.data.get("max_resumes"))
            uc_alumni = bool(request.data.get("uc_alumni"))
            selected_majors = request.data.get("selected_majors", [])

            print(selected_majors)


            # Parse times (optional: add error checking)
            start_time = datetime.strptime(start_time, "%H:%M").time()
            end_time = datetime.strptime(end_time, "%H:%M").time()
            
            today = datetime.today().date()
            start_dt = datetime.combine(today, start_time)
            end_dt = datetime.combine(today, end_time)

            # Get the interval in minutes
            total_minutes = int((end_dt - start_dt).total_seconds() / 60)
            interval_count = total_minutes // 20

            employer = Employer.objects.create(
                full_name=full_name,
                company_name=company_name,
                email=email,
                phone_number=phone_number,
                diet_restriction=diet_restriction,
                start_time=start_time,
                end_time=end_time,
                max_resumes=max_resumes,
                uc_alumni=uc_alumni,
                selected_majors=selected_majors,
            )

            print(employer)
            
            for i in range(interval_count):
               Timeslot.objects.create(
                    employer=employer,
                    timeslot=(start_dt + timedelta(minutes=(20 * i))).time()
               ) 

            return Response({'message': 'Employer and Timeslots created!', 'id': employer.id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(e)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class StudentViewSet(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            full_name = request.data.get("full_name")
            email = request.data.get("email")
            grad_year = int(request.data.get("grad_year"))
            major = request.data.get("major")
            resume = request.FILES.get("resume")
            timeslot_ids = request.data.get("timeslots", "")
            timeslot_ids = [t.strip() for t in timeslot_ids.split(",") if t.strip()]

            student = Student.objects.create(
                full_name=full_name,
                email=email,
                grad_year=grad_year,
                major=major,
                resume=resume,
            )

            updated_slots = []
            for slot_id in timeslot_ids:
                try:
                    timeslot = Timeslot.objects.get(id=slot_id, student__isnull=True)  # only update if unassigned
                    timeslot.student = student
                    timeslot.save()
                    updated_slots.append({'id': timeslot.id, 'timeslot': str(timeslot.timeslot)})
                except Timeslot.DoesNotExist:
                    continue 

            result = {
                "message": "Student registered and timeslots assigned.",
                "student_id": student.id,
                "full_name": student.full_name,
                "assigned_timeslots": updated_slots,
            }
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class TimeslotViewSet(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        major = request.data.get("major")
        time = request.data.get("time")  # should be 'HH:MM' string if being passed
        
        employers = Employer.objects.all()
        if major:
            employers = employers.filter(selected_majors__contains=major)

        # Prepare results
        results = []
        for employer in employers:
            # Filter timeslots for this employer, unassigned, and by time if provided
            timeslot_filter = {'employer': employer, 'student__isnull': True}
            if time:
                timeslot_filter['timeslot'] = time

            available_timeslots = Timeslot.objects.filter(**timeslot_filter)
            data = {
                'id': employer.id,
                'full_name': employer.full_name,
                'company_name': employer.company_name,
                'timeslots': [
                    {'id': t.id, 'timeslot': t.timeslot} for t in available_timeslots 
                ]
            }
            results.append(data)
        return Response(results)