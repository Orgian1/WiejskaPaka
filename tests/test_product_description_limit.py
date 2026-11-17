"""Regression: product descriptions must stay within the approved 200-character limit."""
import pytest
from pydantic import ValidationError
from backend.app import ProductIn


def product(description):
    return ProductIn(name='Marchew', price_grosze=500, delivery_grosze=0, stock=3, description=description)


def test_description_accepts_exactly_200_characters():
    assert len(product('ż' * 200).description) == 200


def test_description_rejects_201_characters():
    with pytest.raises(ValidationError):
        product('ż' * 201)


def test_description_rejects_embedded_null():
    with pytest.raises(ValidationError):
        product('Marchew' + chr(0) + 'test')
