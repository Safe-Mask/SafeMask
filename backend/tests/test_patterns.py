import unittest

from scanner.patterns import (
    CID10_PATTERN,
    CNS_PATTERN,
    CRM_PATTERN,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    normalize_phone,
)


class EmailPatternTests(unittest.TestCase):
    def test_accepts_complete_email_addresses(self):
        valid_emails = [
            "ana.silva+alertas@empresa.com.br",
            "suporte@sub.dominio.org",
            "usuario_123@dominio.io",
        ]

        for email in valid_emails:
            with self.subTest(email=email):
                self.assertIsNotNone(EMAIL_PATTERN.fullmatch(email))

    def test_rejects_incomplete_or_malformed_email_addresses(self):
        invalid_emails = [
            "usuario@dominio",
            "usuario@dominio.c",
            "usuario @dominio.com",
            "usuario@dominio..com",
            "@dominio.com",
        ]

        for email in invalid_emails:
            with self.subTest(email=email):
                self.assertIsNone(EMAIL_PATTERN.fullmatch(email))


class PhonePatternTests(unittest.TestCase):
    def test_normalizes_brazilian_phone_numbers(self):
        phones = {
            "(11) 99876-5432": "11998765432",
            "+55 (21) 2345-6789": "2123456789",
            "1198765432": "1198765432",
        }

        for phone, expected in phones.items():
            with self.subTest(phone=phone):
                self.assertEqual(normalize_phone(phone), expected)
                self.assertIsNotNone(PHONE_PATTERN.fullmatch(phone))

    def test_rejects_incomplete_or_invalid_phone_numbers(self):
        invalid_phones = ["119876543", "(00) 99876-5432", "telefone"]

        for phone in invalid_phones:
            with self.subTest(phone=phone):
                self.assertIsNone(normalize_phone(phone))
                self.assertIsNone(PHONE_PATTERN.fullmatch(phone))


class MedicalPatternTests(unittest.TestCase):
    def test_accepts_medical_identifiers(self):
        identifiers = [
            (CNS_PATTERN, "123456789012345"),
            (CID10_PATTERN, "A00.0"),
            (CID10_PATTERN, "Z99"),
            (CRM_PATTERN, "CRM-SP 123456"),
            (CRM_PATTERN, "CRM 12345"),
        ]

        for pattern, identifier in identifiers:
            with self.subTest(identifier=identifier):
                self.assertIsNotNone(pattern.fullmatch(identifier))

    def test_rejects_incomplete_medical_identifiers(self):
        identifiers = [
            (CNS_PATTERN, "12345678901234"),
            (CID10_PATTERN, "AA0.0"),
            (CRM_PATTERN, "CRM-SP 123"),
        ]

        for pattern, identifier in identifiers:
            with self.subTest(identifier=identifier):
                self.assertIsNone(pattern.fullmatch(identifier))


if __name__ == "__main__":
    unittest.main()
