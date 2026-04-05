import re

from django.core.exceptions import ValidationError


class TribunalPasswordValidator:
    """
    Tribunal exec password rules: more than 5 characters, alphanumeric only,
    and not identical to the username.
    """

    def validate(self, password, user=None):
        if user and password == user.username:
            raise ValidationError(
                "Password cannot be the same as your username.",
                code="password_same_as_username",
            )
        if len(password) <= 5:
            raise ValidationError(
                "Password must be more than 5 characters.",
                code="password_too_short",
            )
        if not re.fullmatch(r"[a-zA-Z0-9]+", password):
            raise ValidationError(
                "Password must contain only letters and numbers.",
                code="password_not_alphanumeric",
            )

    def get_help_text(self):
        return (
            "Your password must be more than 5 characters, use only letters and numbers, "
            "and cannot match your username."
        )
