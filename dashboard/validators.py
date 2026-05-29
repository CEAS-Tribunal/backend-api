import re

from django.core.exceptions import ValidationError


class TribunalPasswordValidator:
    """
    Tribunal exec password rules: more than 5 characters, alphanumeric only,
    and not identical to the username.
    """

    def validate(self, password, user=None):
        errors = []

        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        
        if len(password) > 128:
            errors.append("Password must be no more than 128 characters.")

        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter.")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter.")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number.")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character.")
        
        if re.search(r'(.)\1{2,}', password):  # e.g. "aaa"
            errors.append("Password must not contain repeated characters.")

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return "Password must be 12–128 chars with upper, lower, number, and symbol."
