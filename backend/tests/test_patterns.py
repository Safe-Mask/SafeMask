import unittest

from scanner.patterns import (
    CID10_PATTERN,
    CNS_PATTERN,
    CRM_PATTERN,
    CPF_PATTERN,
    EMAIL_PATTERN,
    PHONE_PATTERN,
    increment_cpf_count,
    mask_cpf,
    mask_phone,
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

    def test_masks_phone_without_losing_its_structure(self):
        masks = {
            "(11) 99876-5432": "(11) *****-5432",
            "+55 (21) 2345-6789": "+55 (21) ****-6789",
            "1198765432": "11****5432",
        }

        for phone, expected in masks.items():
            with self.subTest(phone=phone):
                self.assertEqual(mask_phone(phone), expected)

    def test_does_not_mask_invalid_phone_format(self):
        self.assertIsNone(mask_phone("119876543"))


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


class CpfMaskTests(unittest.TestCase):
    def test_replaces_valid_cpf_with_structured_mask(self):
        cpf = "123.456.789-00"

        self.assertIsNotNone(CPF_PATTERN.fullmatch(cpf))
        self.assertEqual(mask_cpf(cpf), "***.***.***-**")

    def test_does_not_mask_invalid_cpf_format(self):
        self.assertIsNone(mask_cpf("12345678900"))

    def test_increments_only_cpf_redactions(self):
        count = increment_cpf_count(0, "CPF", 2)
        count = increment_cpf_count(count, "EMAIL", 3)
        count = increment_cpf_count(count, "CPF", 1)

        self.assertEqual(count, 3)


if __name__ == "__main__":
    unittest.main()
