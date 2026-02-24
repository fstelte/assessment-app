import pytest
from datetime import date
from scaffold.apps.bia.forms import ContextScopeForm, ComponentForm

def test_context_scope_user_amount_validation(app):
    """Test that user_amount cannot be negative."""
    with app.test_request_context():
        # Valid case
        form = ContextScopeForm(data={"name": "Test Context", "user_amount": 10})
        assert form.validate() is True

        # Invalid case: negative amount
        form = ContextScopeForm(data={"name": "Test Context", "user_amount": -5})
        assert form.validate() is False
        assert "user_amount" in form.errors

def test_context_scope_date_validation(app):
    """Test that end_date cannot be before start_date."""
    with app.test_request_context():
        # Valid case
        form = ContextScopeForm(data={
            "name": "Test Context",
            "start_date": date(2023, 1, 1),
            "end_date": date(2023, 1, 2)
        })
        assert form.validate() is True

        # Invalid case: end_date before start_date
        form = ContextScopeForm(data={
            "name": "Test Context",
            "start_date": date(2023, 1, 2),
            "end_date": date(2023, 1, 1)
        })
        assert form.validate() is False
        assert "end_date" in form.errors
        # The error message key used in the form was bia.context_form.errors.end_date_before_start

def test_context_scope_required_fields(app):
    """Test that required fields are enforced."""
    with app.test_request_context():
        form = ContextScopeForm(data={})
        assert form.validate() is False
        assert "name" in form.errors

def test_component_form_required_fields(app):
    """Test that required fields are enforced."""
    with app.test_request_context():
        form = ComponentForm(data={})
        assert form.validate() is False
        assert "name" in form.errors

def test_field_length_limits(app):
    """Test boundary conditions for string lengths."""
    with app.test_request_context():
        # ContextScopeForm name max length 255
        long_name = "a" * 256
        form = ContextScopeForm(data={"name": long_name})
        assert form.validate() is False
        assert "name" in form.errors

        # ComponentForm name max length 255
        form = ComponentForm(data={"name": long_name})
        assert form.validate() is False
        assert "name" in form.errors

        # TextAreaField max length 5000 (e.g. service_description)
        long_desc = "a" * 5001
        form = ContextScopeForm(data={"name": "Valid Name", "service_description": long_desc})
        assert form.validate() is False
        assert "service_description" in form.errors

        # Component description max length 5000
        form = ComponentForm(data={"name": "Valid Name", "description": long_desc})
        assert form.validate() is False
        assert "description" in form.errors
