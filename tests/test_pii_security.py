"""
Comprehensive PII Scrubber Unit Tests and Security Boundary Tests.

Tests:
  1. Email variants (subdomains, plus-addressing, uppercase, international TLDs).
  2. Phone variants (dashes, dots, parentheses, country codes, compact).
  3. False-positive defense (dates, versions, IP addresses, decimals, math expressions).
  4. Name scrubbing (titles, full names, and negative false-positive protections).
  5. SSN and Address scrubbing.
"""

from __future__ import annotations

import pytest

from app.api.v1.endpoints.ai import _scrub_pii


class TestEmailScrubbing:
    @pytest.mark.parametrize(
        "email_text,expected_masked",
        [
            ("Contact me at user@example.com immediately.", "Contact me at [EMAIL] immediately."),
            ("Reach out to USER.NAME@DOMAIN.ORG for info.", "Reach out to [EMAIL] for info."),
            ("My email is user+tag@mail.domain.com please write.", "My email is [EMAIL] please write."),
            ("Confidential: ceo@sub.corp.company.co.uk is the address.", "Confidential: [EMAIL] is the address."),
            ("Send logs to support@tech-hub.io soon.", "Send logs to [EMAIL] soon."),
            ("Multiple: user1@a.com and user2@b.org sent notes.", "Multiple: [EMAIL] and [EMAIL] sent notes."),
        ],
    )
    def test_email_variations(self, email_text: str, expected_masked: str):
        scrubbed = _scrub_pii(email_text)
        assert scrubbed == expected_masked
        assert "@" not in scrubbed


class TestPhoneScrubbing:
    @pytest.mark.parametrize(
        "phone_text,expected_masked",
        [
            ("Call 415-555-2671 after lunch.", "Call [PHONE] after lunch."),
            ("Dial (415) 555-2671 now.", "Dial [PHONE] now."),
            ("Contact at 415.555.2671 for help.", "Contact at [PHONE] for help."),
            ("Reach +1-415-555-2671 directly.", "Reach [PHONE] directly."),
            ("Call +1 (415) 555-2671 today.", "Call [PHONE] today."),
            ("London office +44 20 7946 0958 is open.", "London office [PHONE] is open."),
            ("Compact number 4155552671 in note.", "Compact number [PHONE] in note."),
            ("Compact intl +14155552671 in note.", "Compact intl [PHONE] in note."),
        ],
    )
    def test_phone_variations(self, phone_text: str, expected_masked: str):
        scrubbed = _scrub_pii(phone_text)
        assert scrubbed == expected_masked
        assert "555-2671" not in scrubbed
        assert "5552671" not in scrubbed


class TestFalsePositiveGuardrails:
    """
    Ensures the scrubber does NOT corrupt legitimate non-PII text,
    such as dates, versions, IP addresses, mathematical equations, and decimals.
    """

    @pytest.mark.parametrize(
        "clean_text",
        [
            "Today's date is 2026-08-15 and the weather is pleasant.",
            "Meeting was scheduled for 15-08-2026 at 14:30.",
            "We deployed version 1.2.3 and patch 2.0.1 without issues.",
            "Server IP is 192.168.1.1 on local subnet 10.0.0.1.",
            "My body temperature was 98.6 degrees and pi is 3.14159.",
            "Calculation result: 100 - 50 = 50 and 200 - 100 = 100.",
            "I ran 10km in 45 minutes and rested for 15 minutes.",
            "The ratio is 1:2:3 and time is 10:30:00.",
        ],
    )
    def test_non_pii_content_preserved(self, clean_text: str):
        scrubbed = _scrub_pii(clean_text)
        assert "[PHONE]" not in scrubbed, f"False positive phone detection in: '{clean_text}' -> '{scrubbed}'"
        assert "[EMAIL]" not in scrubbed, f"False positive email detection in: '{clean_text}' -> '{scrubbed}'"
        assert scrubbed == clean_text


class TestNameScrubbing:
    def test_two_word_names(self):
        text = "I spoke with John Doe and Jane Smith during the morning standup."
        scrubbed = _scrub_pii(text)
        assert "John Doe" not in scrubbed
        assert "Jane Smith" not in scrubbed
        assert scrubbed.count("[NAME]") == 2

    def test_three_word_names(self):
        text = "Meeting with Robert Downey Junior was productive."
        scrubbed = _scrub_pii(text)
        assert "Robert Downey Junior" not in scrubbed
        assert "[NAME]" in scrubbed

    def test_titled_names(self):
        text = "Consultation with Dr. John Watson and Prof. Charles Xavier."
        scrubbed = _scrub_pii(text)
        assert "Dr. John Watson" not in scrubbed
        assert "Prof. Charles Xavier" not in scrubbed
        assert scrubbed.count("[NAME]") == 2

    def test_negative_name_cases(self):
        """Single words or lowercase words must not be scrubbed as names."""
        text = "I felt anxious today after lunch."
        scrubbed = _scrub_pii(text)
        assert "[NAME]" not in scrubbed
        assert scrubbed == text


class TestSSNAndAddressScrubbing:
    def test_ssn_scrubbing(self):
        text = "My SSN is 123-45-6789 for tax records."
        scrubbed = _scrub_pii(text)
        assert "123-45-6789" not in scrubbed
        assert "[SSN]" in scrubbed

    def test_address_scrubbing(self):
        text = "I moved to 742 Evergreen Terrace, CA 90210 last week."
        scrubbed = _scrub_pii(text)
        assert "742 Evergreen Terrace, CA 90210" not in scrubbed
        assert "[ADDRESS]" in scrubbed
        assert "last week." in scrubbed
