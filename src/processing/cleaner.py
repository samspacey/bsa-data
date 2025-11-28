"""Data cleaning and PII removal for reviews."""

import re
from datetime import datetime
from typing import Optional

from langdetect import detect, LangDetectException

from src.data.schemas import Channel, CleanedReview, Product, RawReview


class ReviewCleaner:
    """Clean and normalize review data."""

    # PII patterns
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    PHONE_PATTERN = re.compile(
        r"\b(?:(?:\+44\s?|0)(?:\d\s?){9,10}|\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b"
    )
    POSTCODE_PATTERN = re.compile(
        r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", re.IGNORECASE
    )
    ACCOUNT_NUMBER_PATTERN = re.compile(r"\b\d{6,8}\b")
    SORT_CODE_PATTERN = re.compile(r"\b\d{2}[-\s]?\d{2}[-\s]?\d{2}\b")

    # Name patterns (common UK names that might appear)
    # We'll use a more conservative approach - only redact if it looks like a name reference
    NAME_REFERENCE_PATTERN = re.compile(
        r"\b(?:Mr|Mrs|Ms|Miss|Dr)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b"
    )

    # Channel detection keywords
    CHANNEL_KEYWORDS = {
        Channel.BRANCH: [
            "branch", "in-branch", "in branch", "staff", "teller", "counter",
            "visited", "walk in", "walked in", "face to face"
        ],
        Channel.MOBILE_APP: [
            "app", "mobile", "phone app", "android", "iphone", "ios",
            "application", "mobile banking"
        ],
        Channel.ONLINE: [
            "online", "website", "internet banking", "web", "browser",
            "online banking", "digital"
        ],
        Channel.CALL_CENTRE: [
            "call", "phone", "telephone", "rang", "called", "spoke to",
            "on the phone", "customer service", "helpline", "contact centre"
        ],
    }

    # Product detection keywords
    PRODUCT_KEYWORDS = {
        Product.MORTGAGE: [
            "mortgage", "home loan", "house", "property", "remortgage",
            "lending", "conveyancing"
        ],
        Product.SAVINGS: [
            "savings", "save", "interest rate", "isa", "fixed rate",
            "easy access", "notice account", "saver"
        ],
        Product.CURRENT_ACCOUNT: [
            "current account", "bank account", "debit card", "overdraft",
            "direct debit", "standing order", "wages"
        ],
        Product.ISA: [
            "isa", "cash isa", "stocks and shares isa", "lisa",
            "lifetime isa"
        ],
    }

    def __init__(self, min_review_length: int = 10):
        """Initialize the cleaner.

        Args:
            min_review_length: Minimum length for valid reviews
        """
        self.min_review_length = min_review_length

    def remove_pii(self, text: str) -> str:
        """Remove personally identifiable information from text.

        Args:
            text: Raw text to clean

        Returns:
            Text with PII redacted
        """
        # Remove email addresses
        text = self.EMAIL_PATTERN.sub("[EMAIL]", text)

        # Remove phone numbers
        text = self.PHONE_PATTERN.sub("[PHONE]", text)

        # Remove postcodes
        text = self.POSTCODE_PATTERN.sub("[POSTCODE]", text)

        # Remove potential account numbers (be conservative)
        text = self.ACCOUNT_NUMBER_PATTERN.sub("[ACCOUNT]", text)

        # Remove sort codes
        text = self.SORT_CODE_PATTERN.sub("[SORTCODE]", text)

        # Remove name references with titles
        text = self.NAME_REFERENCE_PATTERN.sub("[NAME]", text)

        return text

    def normalize_text(self, text: str) -> str:
        """Normalize text formatting.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Convert to single spaces
        text = re.sub(r"\s+", " ", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        # Fix common issues
        text = text.replace("\u00a0", " ")  # Non-breaking space
        text = text.replace("\u2019", "'")  # Smart quote
        text = text.replace("\u2018", "'")  # Smart quote
        text = text.replace("\u201c", '"')  # Smart quote
        text = text.replace("\u201d", '"')  # Smart quote
        text = text.replace("\u2013", "-")  # En dash
        text = text.replace("\u2014", "-")  # Em dash

        return text

    def detect_language(self, text: str) -> Optional[str]:
        """Detect the language of text.

        Args:
            text: Text to analyze

        Returns:
            ISO language code or None
        """
        if len(text) < 20:
            return None

        try:
            return detect(text)
        except LangDetectException:
            return None

    def infer_channel(self, text: str) -> Optional[Channel]:
        """Infer the channel from review text.

        Args:
            text: Review text

        Returns:
            Inferred channel or None
        """
        text_lower = text.lower()

        # Count keyword matches for each channel
        channel_scores = {}
        for channel, keywords in self.CHANNEL_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                channel_scores[channel] = score

        if channel_scores:
            return max(channel_scores, key=channel_scores.get)

        return None

    def infer_product(self, text: str) -> Optional[Product]:
        """Infer the product type from review text.

        Args:
            text: Review text

        Returns:
            Inferred product or None
        """
        text_lower = text.lower()

        # Count keyword matches for each product
        product_scores = {}
        for product, keywords in self.PRODUCT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                product_scores[product] = score

        if product_scores:
            return max(product_scores, key=product_scores.get)

        return None

    def should_exclude(self, review: RawReview, clean_text: str) -> tuple[bool, Optional[str]]:
        """Determine if a review should be excluded.

        Args:
            review: Raw review
            clean_text: Cleaned text

        Returns:
            Tuple of (should_exclude, reason)
        """
        # Too short
        if len(clean_text) < self.min_review_length:
            return True, "Text too short"

        # Spam indicators
        spam_patterns = [
            r"click here",
            r"visit my",
            r"check out my",
            r"www\.\w+\.\w+",
            r"http[s]?://",
        ]
        for pattern in spam_patterns:
            if re.search(pattern, clean_text, re.IGNORECASE):
                return True, "Potential spam"

        # Offensive content indicators (basic)
        # Note: More sophisticated filtering should use LLM
        offensive_patterns = [
            r"\b(?:racist|sexist|homophobic)\b",
        ]
        for pattern in offensive_patterns:
            if re.search(pattern, clean_text, re.IGNORECASE):
                return True, "Potentially offensive content"

        return False, None

    def clean_review(self, raw_review: RawReview) -> CleanedReview:
        """Clean a raw review.

        Args:
            raw_review: Raw review data

        Returns:
            Cleaned review
        """
        # Combine title and body for analysis
        full_text = raw_review.body
        if raw_review.title:
            full_text = f"{raw_review.title}. {full_text}"

        # Normalize text first
        normalized_text = self.normalize_text(full_text)

        # Remove PII
        clean_text = self.remove_pii(normalized_text)

        # Detect language
        language = self.detect_language(clean_text)

        # Infer channel and product
        channel = self.infer_channel(clean_text)
        product = self.infer_product(clean_text)

        # Check for exclusion
        should_exclude, exclusion_reason = self.should_exclude(raw_review, clean_text)

        # Normalize rating to 0-1 scale
        rating_normalised = (raw_review.rating - 1) / 4  # Maps 1-5 to 0-1

        # Clean title separately
        clean_title = None
        if raw_review.title:
            clean_title = self.remove_pii(self.normalize_text(raw_review.title))

        return CleanedReview(
            source_id=raw_review.source_id,
            source_review_id=raw_review.source_review_id,
            building_society_id=raw_review.building_society_id,
            review_date=raw_review.review_date,
            rating_raw=raw_review.rating,
            rating_normalised=rating_normalised,
            title_text=clean_title,
            body_text_raw=raw_review.body,
            body_text_clean=clean_text,
            reviewer_language=language,
            channel=channel,
            product=product,
            location_text=raw_review.location,
            app_version=raw_review.app_version,
            is_flagged_for_exclusion=should_exclude,
            exclusion_reason=exclusion_reason,
        )

    def clean_reviews(self, raw_reviews: list[RawReview]) -> list[CleanedReview]:
        """Clean a batch of reviews.

        Args:
            raw_reviews: List of raw reviews

        Returns:
            List of cleaned reviews
        """
        return [self.clean_review(r) for r in raw_reviews]
