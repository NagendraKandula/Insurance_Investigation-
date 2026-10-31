
import re
import unicodedata


def normalize_email(email: str | None) -> str | None:
    """Normalize email addresses for comparison."""

    if not email:
        return None

    return email.strip().lower()


def normalize_phone(phone: str | None) -> str | None:
    """
    Keep digits only and remove the Indian country code
    when the number contains 12 digits beginning with 91.

    Example:
        +91 98765-43210 -> 9876543210
    """

    if not phone:
        return None

    digits = re.sub(r"\D", "", phone)

    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]

    return digits or None


def normalize_address(address: str | None) -> str | None:
    """
    Normalize address text for approximate matching.
    """

    if not address:
        return None

    address = unicodedata.normalize("NFKC", address)
    address = address.lower().strip()

    # Remove punctuation
    address = re.sub(r"[^\w\s]", " ", address)

    # Remove extra spaces
    address = re.sub(r"\s+", " ", address)

    return address or None


if __name__ == "__main__":

    print("Email:", normalize_email(" Nagendra@Gmail.COM "))

    print("Phone:", normalize_phone("+91 98765-43210"))

    print(
        "Address:",
        normalize_address("12/A, MG Road, Hyderabad!")
    )
