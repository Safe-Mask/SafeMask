import unittest

from scanner.patterns import EMAIL_PATTERN


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


if __name__ == "__main__":
    unittest.main()
