import unittest

from scanner.patterns import EMAIL_PATTERN, PHONE_PATTERN, normalize_phone


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


if __name__ == "__main__":
    unittest.main()
