# Employee/forms.py


from django import forms

from .models import (
    Employee,
    Department,
    Position,
    Attendance,
    Leave,
    Contact,
)

# ==========================================
# EMPLOYEE FORM
# ==========================================

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee

        fields = [
            "user",
            "department",
            "position",
            "employee_code",
            "salary",
            "hourly_rate",
            "hire_date",
            "national_id",
            "emergency_contact",
            "is_active",
        ]


        widgets = {

            "hire_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control"
                }
            ),


            "employee_code": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),


            "salary": forms.NumberInput(
                attrs={
                    "class": "form-control"
                }
            ),


            "hourly_rate": forms.NumberInput(
                attrs={
                    "class": "form-control"
                }
            ),


            "national_id": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),


            "emergency_contact": forms.TextInput(
                attrs={
                    "class": "form-control"
                }
            ),

        }




# ==========================================
# DEPARTMENT FORM
# ==========================================

class DepartmentForm(forms.ModelForm):

    class Meta:

        model = Department

        fields = [
            "code",
            "name",
            "description",
            "manager",
        ]


        widgets = {

            "code": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),


            "name": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),


            "description": forms.Textarea(
                attrs={
                    "class":"form-control",
                    "rows":3
                }
            ),

        }




# ==========================================
# POSITION FORM
# ==========================================

class PositionForm(forms.ModelForm):

    class Meta:

        model = Position

        fields = [
            "title",
        ]


        widgets = {

            "title": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            )

        }




# ==========================================
# ATTENDANCE FORM
# ==========================================

class AttendanceForm(forms.ModelForm):

    class Meta:

        model = Attendance

        fields = [
            "employee",
            "date",
            "check_in",
            "check_out",
            "hours_worked",
            "status",
        ]


        widgets = {

            "date": forms.DateInput(
                attrs={
                    "type":"date",
                    "class":"form-control"
                }
            ),


            "check_in": forms.TimeInput(
                attrs={
                    "type":"time",
                    "class":"form-control"
                }
            ),


            "check_out": forms.TimeInput(
                attrs={
                    "type":"time",
                    "class":"form-control"
                }
            ),


            "hours_worked": forms.NumberInput(
                attrs={
                    "class":"form-control"
                }
            ),


            "status": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),

        }




# ==========================================
# LEAVE FORM
# ==========================================

class LeaveForm(forms.ModelForm):

    class Meta:

        model = Leave

        fields = [
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
        ]


        widgets = {

            "start_date": forms.DateInput(
                attrs={
                    "type":"date",
                    "class":"form-control"
                }
            ),


            "end_date": forms.DateInput(
                attrs={
                    "type":"date",
                    "class":"form-control"
                }
            ),


            "reason": forms.Textarea(
                attrs={
                    "class":"form-control",
                    "rows":4
                }
            ),

        }




# ==========================================
# CONTACT FORM
# ==========================================

class ContactForm(forms.ModelForm):

    class Meta:

        model = Contact

        fields = [
            "department",
            "name",
            "phone",
            "email",
            "role",
        ]


        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),


            "phone": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),


            "email": forms.EmailInput(
                attrs={
                    "class":"form-control"
                }
            ),


            "role": forms.TextInput(
                attrs={
                    "class":"form-control"
                }
            ),

        }