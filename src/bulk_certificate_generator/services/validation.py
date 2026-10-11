from pydantic import EmailStr, TypeAdapter, ValidationError

from bulk_certificate_generator.schemas.certificate import RecipientInput

email_adapter = TypeAdapter(EmailStr)


class RecipientValidator:
    def validate(self, recipient: RecipientInput) -> str | None:
        if not recipient.name or not recipient.name.strip():
            return "Recipient name is required."
        if not recipient.email or not recipient.email.strip():
            return "Recipient email is required."
        try:
            email_adapter.validate_python(recipient.email)
        except ValidationError:
            return "Recipient email is invalid."
        return None
