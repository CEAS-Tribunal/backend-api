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

            
            for i in range(interval_count):
               Timeslot.objects.create(
                    employer=employer,
                    timeslot=(start_dt + timedelta(minutes=(20 * i))).time()
               ) 

            return Response({'message': 'Employer and Timeslots created!', 'id': employer.id}, status=status.HTTP_201_CREATED)
        except Exception as e:
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
        
def _parse_time_string(s):
    """Parse '9:00 AM' or 'HH:MM' style string to time object."""
    from datetime import datetime
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def _time_matches(t, allowed):
    """Compare time t to list of allowed times by hour/minute (avoids microsecond mismatch from DB)."""
    list_of_matches = []
    for a in allowed:
        if t.hour == a.hour and t.minute == a.minute:
            list_of_matches.append(True)

    return any(list_of_matches)


def _parse_time_params(time_params):
    """Parse query time strings into a list of time objects. Returns empty list if none valid."""
    return [t for t in (_parse_time_string(p) for p in time_params) if t is not None]


def _format_slot(timeslot_obj):
    """Format a Timeslot instance as API dict with id and formatted timeslot string."""
    ts = timeslot_obj.timeslot
    if hasattr(ts, "hour"):
        h, m = ts.hour, ts.minute
        time_str = f"{h % 12 or 12}:{m:02d} {'AM' if h < 12 else 'PM'}"
    else:
        time_str = str(ts)
    return {"id": timeslot_obj.id, "timeslot": time_str}


def _slots_for_employer(employer_timeslots, times_filter):
    """Build list of slot dicts for an employer, optionally filtered by times_filter."""
    if times_filter:
        return [_format_slot(t) for t in employer_timeslots if _time_matches(t.timeslot, times_filter)]
    return [_format_slot(t) for t in employer_timeslots]


class TimeslotViewSet(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        major = request.query_params.get("major")
        time_params = request.query_params.getlist("time")
        times_filter = _parse_time_params(time_params)



        employers = Employer.objects.all()
        if major:
            employers = employers.filter(selected_majors__contains=major)
        
        results = []
        for employer in employers:
            employer_timeslots = Timeslot.objects.filter(employer=employer, student__isnull=True).all()
            slots = _slots_for_employer(employer_timeslots, times_filter) if employer_timeslots else []
            if slots:
                results.append({
                    "id": employer.id,
                    "full_name": employer.full_name,
                    "company_name": employer.company_name,
                    "timeslots": slots,
                })


        return Response(results, status=status.HTTP_200_OK)
